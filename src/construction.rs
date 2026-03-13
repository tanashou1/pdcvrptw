use anyhow::{bail, Result};

use crate::distance::DistanceMatrix;
use crate::evaluate::evaluate_route;
use crate::instance::Instance;
use crate::solution::{Route, SolutionState};

#[derive(Debug, Clone)]
pub struct InsertionChoice {
    pub route_index: Option<usize>,
    pub depot_idx: usize,
    pub position: usize,
    pub delta: i64,
}

pub fn build_initial_solution(
    instance: &Instance,
    matrix: &DistanceMatrix,
) -> Result<SolutionState> {
    let mut solution = SolutionState::default();
    let pending = (0..instance.nodes.len()).collect::<Vec<_>>();

    if !repair_nodes(instance, matrix, &mut solution, &pending) {
        bail!("failed to construct a feasible initial solution");
    }

    Ok(solution)
}

pub fn repair_nodes(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    nodes: &[usize],
) -> bool {
    let mut pending = nodes.to_vec();

    while !pending.is_empty() {
        let Some((node_idx, choice)) =
            select_regret_insertion(instance, matrix, solution, &pending)
        else {
            return false;
        };

        apply_insertion(solution, node_idx, &choice);
        pending.retain(|candidate| *candidate != node_idx);
    }

    true
}

fn select_regret_insertion(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    pending: &[usize],
) -> Option<(usize, InsertionChoice)> {
    let mut selected: Option<(usize, InsertionChoice, i64, i64)> = None;

    for &node_idx in pending {
        let mut choices = feasible_insertions(instance, matrix, solution, node_idx);
        if choices.is_empty() {
            continue;
        }

        choices.sort_by_key(|choice| choice.delta);
        let best = choices[0].clone();
        let second_delta = choices
            .get(1)
            .map(|choice| choice.delta)
            .unwrap_or(best.delta + 50);
        let regret = second_delta - best.delta;

        let should_replace = match &selected {
            None => true,
            Some((_, _, best_regret, best_delta)) => {
                regret > *best_regret || (regret == *best_regret && best.delta < *best_delta)
            }
        };

        if should_replace {
            selected = Some((node_idx, best, regret, choices[0].delta));
        }
    }

    selected.map(|(node_idx, choice, _, _)| (node_idx, choice))
}

fn feasible_insertions(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    node_idx: usize,
) -> Vec<InsertionChoice> {
    let mut choices = Vec::new();

    for (route_index, route) in solution.routes.iter().enumerate() {
        for position in 0..=route.stops.len() {
            let delta = insertion_delta(matrix, route, position, node_idx);
            let mut candidate = route.clone();
            candidate.stops.insert(position, node_idx);

            if evaluate_route(instance, matrix, &candidate).feasible {
                choices.push(InsertionChoice {
                    route_index: Some(route_index),
                    depot_idx: route.depot_idx,
                    position,
                    delta,
                });
            }
        }
    }

    for depot_idx in 0..instance.depots.len() {
        if solution.used_vehicle_count(depot_idx) >= instance.vehicle_limit(depot_idx) {
            continue;
        }

        let candidate = Route {
            depot_idx,
            stops: vec![node_idx],
        };
        let metrics = evaluate_route(instance, matrix, &candidate);

        if metrics.feasible {
            choices.push(InsertionChoice {
                route_index: None,
                depot_idx,
                position: 0,
                delta: metrics.distance,
            });
        }
    }

    choices
}

fn insertion_delta(
    matrix: &DistanceMatrix,
    route: &Route,
    position: usize,
    node_idx: usize,
) -> i64 {
    let depot_location = matrix.depot_location(route.depot_idx);
    let previous_location = if position == 0 {
        depot_location
    } else {
        matrix.node_location(route.stops[position - 1])
    };
    let next_location = if position == route.stops.len() {
        depot_location
    } else {
        matrix.node_location(route.stops[position])
    };
    let node_location = matrix.node_location(node_idx);

    matrix.distance(previous_location, node_location)
        + matrix.distance(node_location, next_location)
        - matrix.distance(previous_location, next_location)
}

fn apply_insertion(solution: &mut SolutionState, node_idx: usize, choice: &InsertionChoice) {
    if let Some(route_index) = choice.route_index {
        solution.routes[route_index]
            .stops
            .insert(choice.position, node_idx);
        return;
    }

    let mut route = Route::new(choice.depot_idx);
    route.stops.push(node_idx);
    solution.routes.push(route);
}
