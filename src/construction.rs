use anyhow::{bail, Result};

use crate::distance::DistanceMatrix;
use crate::evaluate::evaluate_route;
use crate::instance::{Instance, RequestPair};
use crate::solution::{Route, SolutionState};

#[derive(Debug, Clone)]
pub struct InsertionChoice {
    pub route_index: Option<usize>,
    pub depot_idx: usize,
    pub position: usize,
    pub delta: f64,
}

#[derive(Debug, Clone)]
pub struct PairInsertionChoice {
    pub route_index: Option<usize>,
    pub depot_idx: usize,
    pub pickup_position: usize,
    pub delivery_position: usize,
    pub delta: f64,
}

pub fn build_initial_solution(
    instance: &Instance,
    matrix: &DistanceMatrix,
) -> Result<SolutionState> {
    let mut solution = SolutionState::default();

    let repaired = if instance.enforces_precedence() {
        let pending = instance
            .request_pairs()
            .into_iter()
            .flat_map(|pair| [pair.pickup_idx, pair.delivery_idx])
            .collect::<Vec<_>>();
        repair_nodes(instance, matrix, &mut solution, &pending)
    } else {
        let pending = (0..instance.nodes.len()).collect::<Vec<_>>();
        repair_nodes(instance, matrix, &mut solution, &pending)
    };

    if !repaired {
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
    if instance.enforces_precedence() {
        return repair_request_pairs(instance, matrix, solution, nodes);
    }

    repair_single_nodes(instance, matrix, solution, nodes)
}

fn repair_single_nodes(
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

fn repair_request_pairs(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    nodes: &[usize],
) -> bool {
    let mut pending_pairs = instance.request_pairs_from_nodes(nodes);

    while !pending_pairs.is_empty() {
        let Some((pair_index, choice)) =
            select_pair_regret_insertion(instance, matrix, solution, &pending_pairs)
        else {
            return false;
        };

        let pair = pending_pairs.remove(pair_index);
        apply_pair_insertion(solution, &pair, &choice);
    }

    true
}

fn select_regret_insertion(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    pending: &[usize],
) -> Option<(usize, InsertionChoice)> {
    let mut selected: Option<(usize, InsertionChoice, f64, f64)> = None;

    for &node_idx in pending {
        let mut choices = feasible_insertions(instance, matrix, solution, node_idx);
        if choices.is_empty() {
            continue;
        }

        choices.sort_by(|left, right| left.delta.total_cmp(&right.delta));
        let best = choices[0].clone();
        let second_delta = choices
            .get(1)
            .map(|choice| choice.delta)
            .unwrap_or(best.delta + 50.0);
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

fn select_pair_regret_insertion(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    pending_pairs: &[RequestPair],
) -> Option<(usize, PairInsertionChoice)> {
    let mut selected: Option<(usize, PairInsertionChoice, f64, f64)> = None;

    for (pair_index, pair) in pending_pairs.iter().enumerate() {
        let mut choices = feasible_pair_insertions(instance, matrix, solution, pair);
        if choices.is_empty() {
            continue;
        }

        choices.sort_by(|left, right| left.delta.total_cmp(&right.delta));
        let best = choices[0].clone();
        let second_delta = choices
            .get(1)
            .map(|choice| choice.delta)
            .unwrap_or(best.delta + 50.0);
        let regret = second_delta - best.delta;

        let should_replace = match &selected {
            None => true,
            Some((_, _, best_regret, best_delta)) => {
                regret > *best_regret || (regret == *best_regret && best.delta < *best_delta)
            }
        };

        if should_replace {
            selected = Some((pair_index, best, regret, choices[0].delta));
        }
    }

    selected.map(|(pair_index, choice, _, _)| (pair_index, choice))
}

fn feasible_insertions(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    node_idx: usize,
) -> Vec<InsertionChoice> {
    let mut choices = Vec::new();

    for (route_index, route) in solution.routes.iter().enumerate() {
        let original_distance = evaluate_route(instance, matrix, route).distance;

        for position in 0..=route.stops.len() {
            let mut candidate = route.clone();
            candidate.stops.insert(position, node_idx);

            let metrics = evaluate_route(instance, matrix, &candidate);
            if metrics.feasible {
                choices.push(InsertionChoice {
                    route_index: Some(route_index),
                    depot_idx: route.depot_idx,
                    position,
                    delta: metrics.distance - original_distance,
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

fn feasible_pair_insertions(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    pair: &RequestPair,
) -> Vec<PairInsertionChoice> {
    let mut choices = Vec::new();

    for (route_index, route) in solution.routes.iter().enumerate() {
        let original_distance = evaluate_route(instance, matrix, route).distance;

        for pickup_position in 0..=route.stops.len() {
            for delivery_position in (pickup_position + 1)..=(route.stops.len() + 1) {
                let mut candidate = route.clone();
                candidate.stops.insert(pickup_position, pair.pickup_idx);
                candidate.stops.insert(delivery_position, pair.delivery_idx);

                let metrics = evaluate_route(instance, matrix, &candidate);
                if metrics.feasible {
                    choices.push(PairInsertionChoice {
                        route_index: Some(route_index),
                        depot_idx: route.depot_idx,
                        pickup_position,
                        delivery_position,
                        delta: metrics.distance - original_distance,
                    });
                }
            }
        }
    }

    for depot_idx in 0..instance.depots.len() {
        if solution.used_vehicle_count(depot_idx) >= instance.vehicle_limit(depot_idx) {
            continue;
        }

        let candidate = Route {
            depot_idx,
            stops: vec![pair.pickup_idx, pair.delivery_idx],
        };
        let metrics = evaluate_route(instance, matrix, &candidate);

        if metrics.feasible {
            choices.push(PairInsertionChoice {
                route_index: None,
                depot_idx,
                pickup_position: 0,
                delivery_position: 1,
                delta: metrics.distance,
            });
        }
    }

    choices
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

fn apply_pair_insertion(
    solution: &mut SolutionState,
    pair: &RequestPair,
    choice: &PairInsertionChoice,
) {
    if let Some(route_index) = choice.route_index {
        solution.routes[route_index]
            .stops
            .insert(choice.pickup_position, pair.pickup_idx);
        solution.routes[route_index]
            .stops
            .insert(choice.delivery_position, pair.delivery_idx);
        return;
    }

    let mut route = Route::new(choice.depot_idx);
    route.stops.push(pair.pickup_idx);
    route.stops.push(pair.delivery_idx);
    solution.routes.push(route);
}
