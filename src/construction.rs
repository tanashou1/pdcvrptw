use std::cmp::Ordering;

use anyhow::{bail, Result};

use crate::distance::DistanceMatrix;
use crate::evaluate::evaluate_route;
use crate::instance::{Instance, RequestPair};
use crate::solution::{Route, SolutionState};

#[derive(Debug, Clone, Copy)]
pub struct RepairOptions {
    pub allow_new_routes: bool,
}

impl Default for RepairOptions {
    fn default() -> Self {
        Self {
            allow_new_routes: true,
        }
    }
}

#[derive(Debug, Clone)]
pub struct InsertionChoice {
    pub route_index: Option<usize>,
    pub depot_idx: usize,
    pub position: usize,
    pub delta: f64,
    pub distance_delta: f64,
    pub remaining_time: f64,
    pub remaining_capacity: i32,
}

#[derive(Debug, Clone)]
pub struct PairInsertionChoice {
    pub route_index: Option<usize>,
    pub depot_idx: usize,
    pub pickup_position: usize,
    pub delivery_position: usize,
    pub delta: f64,
    pub distance_delta: f64,
    pub remaining_time: f64,
    pub remaining_capacity: i32,
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

    compact_routes(instance, matrix, &mut solution);
    Ok(solution)
}

pub fn repair_nodes(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    nodes: &[usize],
) -> bool {
    repair_nodes_with_options(instance, matrix, solution, nodes, RepairOptions::default())
}

pub fn repair_nodes_with_options(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    nodes: &[usize],
    options: RepairOptions,
) -> bool {
    if instance.enforces_precedence() {
        return repair_request_pairs(instance, matrix, solution, nodes, options);
    }

    repair_single_nodes(instance, matrix, solution, nodes, options)
}

pub fn compact_routes(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
) -> bool {
    if solution.routes.len() <= 1 {
        return false;
    }

    let mut improved = false;

    loop {
        let route_order = route_compaction_order(instance, matrix, solution);
        let mut reduced_once = false;

        for route_index in route_order {
            let removed_nodes = solution.routes[route_index].stops.clone();
            if removed_nodes.is_empty() {
                continue;
            }

            let mut candidate = solution.clone();
            candidate.routes.remove(route_index);

            if repair_nodes_with_options(
                instance,
                matrix,
                &mut candidate,
                &removed_nodes,
                RepairOptions {
                    allow_new_routes: false,
                },
            ) {
                *solution = candidate;
                improved = true;
                reduced_once = true;
                break;
            }
        }

        if !reduced_once || solution.routes.len() <= 1 {
            break;
        }
    }

    improved
}

fn repair_single_nodes(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    nodes: &[usize],
    options: RepairOptions,
) -> bool {
    let mut pending = nodes.to_vec();

    while !pending.is_empty() {
        let Some((node_idx, choice)) =
            select_regret_insertion(instance, matrix, solution, &pending, options)
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
    options: RepairOptions,
) -> bool {
    let mut pending_pairs = instance.request_pairs_from_nodes(nodes);

    while !pending_pairs.is_empty() {
        let Some((pair_index, choice)) =
            select_pair_regret_insertion(instance, matrix, solution, &pending_pairs, options)
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
    options: RepairOptions,
) -> Option<(usize, InsertionChoice)> {
    let mut selected: Option<(usize, InsertionChoice, f64, f64)> = None;

    for &node_idx in pending {
        let mut choices = feasible_insertions(instance, matrix, solution, node_idx, options);
        if choices.is_empty() {
            continue;
        }

        choices.sort_by(compare_insertion_choices);
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
    options: RepairOptions,
) -> Option<(usize, PairInsertionChoice)> {
    let mut selected: Option<(usize, PairInsertionChoice, f64, f64)> = None;

    for (pair_index, pair) in pending_pairs.iter().enumerate() {
        let mut choices = feasible_pair_insertions(instance, matrix, solution, pair, options);
        if choices.is_empty() {
            continue;
        }

        choices.sort_by(compare_pair_insertion_choices);
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
    options: RepairOptions,
) -> Vec<InsertionChoice> {
    let mut choices = Vec::new();
    let current_route_count = solution.routes.len();

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
                    delta: insertion_delta(
                        instance,
                        current_route_count,
                        0,
                        metrics.distance - original_distance,
                    ),
                    distance_delta: metrics.distance - original_distance,
                    remaining_time: remaining_route_time(
                        instance,
                        route.depot_idx,
                        metrics.end_time,
                    ),
                    remaining_capacity: remaining_route_capacity(instance, metrics.max_load),
                });
            }
        }
    }

    if options.allow_new_routes {
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
                    delta: insertion_delta(instance, current_route_count, 1, metrics.distance),
                    distance_delta: metrics.distance,
                    remaining_time: remaining_route_time(instance, depot_idx, metrics.end_time),
                    remaining_capacity: remaining_route_capacity(instance, metrics.max_load),
                });
            }
        }
    }

    choices
}

fn feasible_pair_insertions(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    pair: &RequestPair,
    options: RepairOptions,
) -> Vec<PairInsertionChoice> {
    let mut choices = Vec::new();
    let current_route_count = solution.routes.len();

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
                        delta: insertion_delta(
                            instance,
                            current_route_count,
                            0,
                            metrics.distance - original_distance,
                        ),
                        distance_delta: metrics.distance - original_distance,
                        remaining_time: remaining_route_time(
                            instance,
                            route.depot_idx,
                            metrics.end_time,
                        ),
                        remaining_capacity: remaining_route_capacity(instance, metrics.max_load),
                    });
                }
            }
        }
    }

    if options.allow_new_routes {
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
                    delta: insertion_delta(instance, current_route_count, 1, metrics.distance),
                    distance_delta: metrics.distance,
                    remaining_time: remaining_route_time(instance, depot_idx, metrics.end_time),
                    remaining_capacity: remaining_route_capacity(instance, metrics.max_load),
                });
            }
        }
    }

    choices
}

fn insertion_delta(
    instance: &Instance,
    current_route_count: usize,
    extra_routes: usize,
    distance_delta: f64,
) -> f64 {
    instance.search_score(current_route_count + extra_routes, distance_delta)
        - instance.search_score(current_route_count, 0.0)
}

fn remaining_route_time(instance: &Instance, depot_idx: usize, end_time: f64) -> f64 {
    (instance.depots[depot_idx].tw.end as f64 - end_time).max(0.0)
}

fn remaining_route_capacity(instance: &Instance, max_load: i32) -> i32 {
    (instance.capacity - max_load).max(0)
}

fn compare_insertion_choices(left: &InsertionChoice, right: &InsertionChoice) -> Ordering {
    left.delta
        .total_cmp(&right.delta)
        .then_with(|| right.remaining_time.total_cmp(&left.remaining_time))
        .then_with(|| right.remaining_capacity.cmp(&left.remaining_capacity))
        .then_with(|| left.distance_delta.total_cmp(&right.distance_delta))
}

fn compare_pair_insertion_choices(
    left: &PairInsertionChoice,
    right: &PairInsertionChoice,
) -> Ordering {
    left.delta
        .total_cmp(&right.delta)
        .then_with(|| right.remaining_time.total_cmp(&left.remaining_time))
        .then_with(|| right.remaining_capacity.cmp(&left.remaining_capacity))
        .then_with(|| left.distance_delta.total_cmp(&right.distance_delta))
}

fn route_compaction_order(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
) -> Vec<usize> {
    let mut ranked = solution
        .routes
        .iter()
        .enumerate()
        .map(|(route_index, route)| {
            let unit_count = if instance.enforces_precedence() {
                instance.request_pairs_from_nodes(&route.stops).len()
            } else {
                route.stops.len()
            };
            let metrics = evaluate_route(instance, matrix, route);
            (route_index, unit_count, route.stops.len(), metrics.distance)
        })
        .collect::<Vec<_>>();

    ranked.sort_by(|left, right| {
        left.1
            .cmp(&right.1)
            .then_with(|| left.2.cmp(&right.2))
            .then_with(|| left.3.total_cmp(&right.3))
    });

    ranked
        .into_iter()
        .map(|(route_index, _, _, _)| route_index)
        .collect()
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

#[cfg(test)]
mod tests {
    use super::compact_routes;
    use crate::distance::DistanceMatrix;
    use crate::evaluate::evaluate_solution;
    use crate::instance::Instance;
    use crate::solution::{Route, SolutionState};

    fn sample_precedence_instance() -> Instance {
        serde_json::from_str(
            r#"
            {
              "name": "compact",
              "seed": 1,
              "planning_horizon": { "start": 0, "end": 500 },
              "capacity": 4,
              "vehicles_per_depot": { "D0": 2 },
              "depots": [
                { "id": "D0", "x": 0, "y": 0, "tw": { "start": 0, "end": 500 } }
              ],
              "nodes": [
                {
                  "id": "P001",
                  "request_id": "R001",
                  "kind": "pickup",
                  "x": 1,
                  "y": 0,
                  "demand": 1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 500 },
                  "location_id": "L001P",
                  "time_window_label": "none"
                },
                {
                  "id": "D001",
                  "request_id": "R001",
                  "kind": "delivery",
                  "x": 2,
                  "y": 0,
                  "demand": -1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 500 },
                  "location_id": "L001D",
                  "time_window_label": "none"
                },
                {
                  "id": "P002",
                  "request_id": "R002",
                  "kind": "pickup",
                  "x": 3,
                  "y": 0,
                  "demand": 1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 500 },
                  "location_id": "L002P",
                  "time_window_label": "none"
                },
                {
                  "id": "D002",
                  "request_id": "R002",
                  "kind": "delivery",
                  "x": 4,
                  "y": 0,
                  "demand": -1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 500 },
                  "location_id": "L002D",
                  "time_window_label": "none"
                }
              ],
              "metadata": {
                "request_count": 2,
                "node_count": 4,
                "location_count": 4,
                "vehicle_count": 2,
                "variant": "test",
                "benchmark_group": "test",
                "distance_metric": "euclidean_double",
                "load_profile": "balanced_start",
                "objective_mode": "vehicles_then_distance",
                "enforce_precedence": true
              }
            }
            "#,
        )
        .unwrap()
    }

    #[test]
    fn compact_routes_merges_routes_when_existing_routes_can_absorb_requests() {
        let instance = sample_precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let mut solution = SolutionState {
            routes: vec![
                Route {
                    depot_idx: 0,
                    stops: vec![0, 1],
                },
                Route {
                    depot_idx: 0,
                    stops: vec![2, 3],
                },
            ],
        };

        assert!(compact_routes(&instance, &matrix, &mut solution));
        assert_eq!(solution.routes.len(), 1);
        assert!(evaluate_solution(&instance, &matrix, &solution).feasible);
    }
}
