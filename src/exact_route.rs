use std::collections::HashMap;

use rand::prelude::SliceRandom;
use rand::rngs::StdRng;

use crate::distance::DistanceMatrix;
use crate::evaluate::evaluate_route;
use crate::instance::{Instance, NodeKind};
use crate::solution::{Route, SolutionState};

const MAX_SMALL_ROUTE_STOPS: usize = 20;
const MIN_SMALL_ROUTE_STOPS: usize = 3;
const SMALL_ROUTE_SHORTLIST: usize = 3;
const FLOAT_TOLERANCE: f64 = 1e-9;

#[derive(Debug, Clone)]
struct Label {
    last: usize,
    distance: f64,
    departure_time: f64,
    predecessor: Option<usize>,
}

struct SmallRouteOptimizer<'a> {
    instance: &'a Instance,
    matrix: &'a DistanceMatrix,
    route: &'a Route,
    load_feasible: Vec<bool>,
    dependency_masks: Vec<u32>,
}

impl<'a> SmallRouteOptimizer<'a> {
    fn new(instance: &'a Instance, matrix: &'a DistanceMatrix, route: &'a Route) -> Option<Self> {
        let stop_count = route.stops.len();
        if !(MIN_SMALL_ROUTE_STOPS..=MAX_SMALL_ROUTE_STOPS).contains(&stop_count) {
            return None;
        }

        let start_load = if instance.uses_balanced_start_load() {
            route
                .stops
                .iter()
                .map(|&node_idx| (-instance.nodes[node_idx].demand).max(0))
                .sum::<i32>()
        } else {
            0
        };

        if !(0..=instance.capacity).contains(&start_load) {
            return None;
        }

        let state_count = 1_usize << stop_count;
        let mut subset_demands = vec![0_i32; state_count];
        let mut load_feasible = vec![false; state_count];
        load_feasible[0] = true;

        for mask in 1..state_count {
            let least_bit = mask & (!mask + 1);
            let local_idx = least_bit.trailing_zeros() as usize;
            let previous_mask = mask ^ least_bit;
            let node_idx = route.stops[local_idx];
            subset_demands[mask] = subset_demands[previous_mask] + instance.nodes[node_idx].demand;
            let load_after = start_load + subset_demands[mask];
            load_feasible[mask] = (0..=instance.capacity).contains(&load_after);
        }

        let mut dependency_masks = vec![0_u32; stop_count];
        if instance.enforces_precedence() {
            let mut pickup_positions = HashMap::new();
            for (local_idx, &node_idx) in route.stops.iter().enumerate() {
                let node = &instance.nodes[node_idx];
                if node.kind == NodeKind::Pickup {
                    pickup_positions.insert(node.request_id.clone(), local_idx);
                }
            }

            for (local_idx, &node_idx) in route.stops.iter().enumerate() {
                let node = &instance.nodes[node_idx];
                if node.kind == NodeKind::Delivery {
                    let pickup_idx = pickup_positions.get(&node.request_id)?;
                    dependency_masks[local_idx] = 1_u32 << pickup_idx;
                }
            }
        }

        Some(Self {
            instance,
            matrix,
            route,
            load_feasible,
            dependency_masks,
        })
    }

    fn solve(&self) -> Option<Route> {
        let stop_count = self.route.stops.len();
        let full_mask = (1_u32 << stop_count) - 1;
        let mut labels = Vec::<Label>::new();
        let mut current_states = HashMap::<u64, Vec<usize>>::new();

        for local_idx in 0..stop_count {
            let bit = 1_u32 << local_idx;
            if !self.can_visit(0, local_idx) || !self.is_load_feasible(bit) {
                continue;
            }

            let Some((distance, departure_time)) = self.travel_from_depot(local_idx) else {
                continue;
            };

            insert_label(
                &mut current_states,
                &mut labels,
                bit,
                Label {
                    last: local_idx,
                    distance,
                    departure_time,
                    predecessor: None,
                },
            );
        }

        if current_states.is_empty() {
            return None;
        }

        for _ in 1..stop_count {
            let mut next_states = HashMap::<u64, Vec<usize>>::new();

            for (state_key, frontier) in current_states {
                let (mask, _) = decode_state_key(state_key);

                for label_idx in frontier {
                    let label = labels[label_idx].clone();

                    for next_idx in 0..stop_count {
                        let bit = 1_u32 << next_idx;
                        if mask & bit != 0 || !self.can_visit(mask, next_idx) {
                            continue;
                        }

                        let next_mask = mask | bit;
                        if !self.is_load_feasible(next_mask) {
                            continue;
                        }

                        let Some((distance, departure_time)) = self.extend_label(&label, next_idx)
                        else {
                            continue;
                        };

                        insert_label(
                            &mut next_states,
                            &mut labels,
                            next_mask,
                            Label {
                                last: next_idx,
                                distance,
                                departure_time,
                                predecessor: Some(label_idx),
                            },
                        );
                    }
                }
            }

            if next_states.is_empty() {
                return None;
            }
            current_states = next_states;
        }

        let mut best_label_idx = None;
        let mut best_total_distance = f64::INFINITY;

        for (state_key, frontier) in current_states {
            let (mask, _) = decode_state_key(state_key);
            if mask != full_mask {
                continue;
            }

            for label_idx in frontier {
                let label = &labels[label_idx];
                let return_distance = self.matrix.distance(
                    self.matrix.node_location(self.route.stops[label.last]),
                    self.matrix.depot_location(self.route.depot_idx),
                );
                let end_time = label.departure_time + return_distance;

                if end_time > self.instance.depots[self.route.depot_idx].tw.end as f64 {
                    continue;
                }

                let total_distance = label.distance + return_distance;
                if total_distance + FLOAT_TOLERANCE < best_total_distance {
                    best_total_distance = total_distance;
                    best_label_idx = Some(label_idx);
                }
            }
        }

        let best_label_idx = best_label_idx?;
        let ordered_local_indices = reconstruct_path(&labels, best_label_idx);
        Some(Route {
            depot_idx: self.route.depot_idx,
            vehicle_idx: self.route.vehicle_idx,
            stops: ordered_local_indices
                .into_iter()
                .map(|local_idx| self.route.stops[local_idx])
                .collect(),
        })
    }

    fn can_visit(&self, mask: u32, local_idx: usize) -> bool {
        let bit = 1_u32 << local_idx;
        if mask & bit != 0 {
            return false;
        }

        let dependency_mask = self.dependency_masks[local_idx];
        dependency_mask == 0 || (mask & dependency_mask) == dependency_mask
    }

    fn is_load_feasible(&self, mask: u32) -> bool {
        self.load_feasible[mask as usize]
    }

    fn travel_from_depot(&self, next_idx: usize) -> Option<(f64, f64)> {
        let depot = &self.instance.depots[self.route.depot_idx];
        let node_idx = self.route.stops[next_idx];
        let node = &self.instance.nodes[node_idx];
        let travel = self.matrix.distance(
            self.matrix.depot_location(self.route.depot_idx),
            self.matrix.node_location(node_idx),
        );
        let arrival = depot.tw.start as f64 + travel;
        let start_service = arrival.max(node.tw.start as f64);

        if start_service > node.tw.end as f64 {
            return None;
        }

        Some((travel, start_service + node.service_duration as f64))
    }

    fn extend_label(&self, label: &Label, next_idx: usize) -> Option<(f64, f64)> {
        let from_node_idx = self.route.stops[label.last];
        let next_node_idx = self.route.stops[next_idx];
        let next_node = &self.instance.nodes[next_node_idx];
        let travel = self.matrix.distance(
            self.matrix.node_location(from_node_idx),
            self.matrix.node_location(next_node_idx),
        );
        let arrival = label.departure_time + travel;
        let start_service = arrival.max(next_node.tw.start as f64);

        if start_service > next_node.tw.end as f64 {
            return None;
        }

        Some((
            label.distance + travel,
            start_service + next_node.service_duration as f64,
        ))
    }
}

pub fn intensify_small_route_order(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    rng: &mut StdRng,
) -> bool {
    let mut ranked_routes = solution
        .routes
        .iter()
        .enumerate()
        .filter(|(_, route)| {
            (MIN_SMALL_ROUTE_STOPS..=MAX_SMALL_ROUTE_STOPS).contains(&route.stops.len())
                && route
                    .stops
                    .iter()
                    .all(|node_idx| !instance.node_is_fixed(*node_idx))
        })
        .map(|(route_index, route)| {
            let metrics = evaluate_route(instance, matrix, route);
            (route_index, route.stops.len(), metrics.distance)
        })
        .collect::<Vec<_>>();

    ranked_routes.sort_by(|left, right| {
        right
            .1
            .cmp(&left.1)
            .then_with(|| right.2.total_cmp(&left.2))
    });

    let mut shortlist = ranked_routes
        .into_iter()
        .take(SMALL_ROUTE_SHORTLIST)
        .collect::<Vec<_>>();
    shortlist.shuffle(rng);

    for (route_index, _, _) in shortlist {
        if let Some(optimized_route) =
            optimize_route_if_better(instance, matrix, &solution.routes[route_index])
        {
            solution.routes[route_index] = optimized_route;
            return true;
        }
    }

    false
}

pub fn optimize_all_small_routes(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
) -> bool {
    let mut route_order = solution
        .routes
        .iter()
        .enumerate()
        .filter(|(_, route)| {
            (MIN_SMALL_ROUTE_STOPS..=MAX_SMALL_ROUTE_STOPS).contains(&route.stops.len())
                && route
                    .stops
                    .iter()
                    .all(|node_idx| !instance.node_is_fixed(*node_idx))
        })
        .map(|(route_index, route)| {
            let metrics = evaluate_route(instance, matrix, route);
            (route_index, route.stops.len(), metrics.distance)
        })
        .collect::<Vec<_>>();

    route_order.sort_by(|left, right| {
        right
            .1
            .cmp(&left.1)
            .then_with(|| right.2.total_cmp(&left.2))
    });

    let mut improved = false;
    for (route_index, _, _) in route_order {
        if let Some(optimized_route) =
            optimize_route_if_better(instance, matrix, &solution.routes[route_index])
        {
            solution.routes[route_index] = optimized_route;
            improved = true;
        }
    }

    improved
}

fn optimize_route_if_better(
    instance: &Instance,
    matrix: &DistanceMatrix,
    route: &Route,
) -> Option<Route> {
    let original_metrics = evaluate_route(instance, matrix, route);
    if !original_metrics.feasible {
        return None;
    }

    let optimizer = SmallRouteOptimizer::new(instance, matrix, route)?;
    let optimized_route = optimizer.solve()?;
    let optimized_metrics = evaluate_route(instance, matrix, &optimized_route);

    (optimized_metrics.feasible
        && optimized_metrics.distance + FLOAT_TOLERANCE < original_metrics.distance)
        .then_some(optimized_route)
}

fn insert_label(
    states: &mut HashMap<u64, Vec<usize>>,
    labels: &mut Vec<Label>,
    mask: u32,
    candidate: Label,
) {
    let state_key = encode_state_key(mask, candidate.last);
    let frontier = states.entry(state_key).or_default();

    if frontier
        .iter()
        .any(|&label_idx| dominates(&labels[label_idx], &candidate))
    {
        return;
    }

    frontier.retain(|&label_idx| !dominates(&candidate, &labels[label_idx]));
    let label_idx = labels.len();
    labels.push(candidate);
    frontier.push(label_idx);
}

fn dominates(left: &Label, right: &Label) -> bool {
    left.distance <= right.distance + FLOAT_TOLERANCE
        && left.departure_time <= right.departure_time + FLOAT_TOLERANCE
}

fn reconstruct_path(labels: &[Label], mut label_idx: usize) -> Vec<usize> {
    let mut path = Vec::new();

    loop {
        let label = &labels[label_idx];
        path.push(label.last);
        match label.predecessor {
            Some(previous_idx) => label_idx = previous_idx,
            None => break,
        }
    }

    path.reverse();
    path
}

fn encode_state_key(mask: u32, last: usize) -> u64 {
    ((mask as u64) << 5) | last as u64
}

fn decode_state_key(state_key: u64) -> (u32, usize) {
    ((state_key >> 5) as u32, (state_key & 0b1_1111) as usize)
}

#[cfg(test)]
mod tests {
    use super::{optimize_all_small_routes, SmallRouteOptimizer};
    use crate::distance::DistanceMatrix;
    use crate::evaluate::evaluate_route;
    use crate::instance::Instance;
    use crate::solution::{Route, SolutionState};

    fn precedence_instance() -> Instance {
        serde_json::from_str::<Instance>(
            r#"
            {
              "name": "small-route",
              "seed": 1,
              "planning_horizon": { "start": 0, "end": 200 },
              "capacity": 4,
              "vehicles_per_depot": { "D0": 1 },
              "depots": [
                { "id": "D0", "x": 0, "y": 0, "tw": { "start": 0, "end": 200 } }
              ],
              "nodes": [
                {
                  "id": "P1",
                  "request_id": "R1",
                  "kind": "pickup",
                  "x": 1,
                  "y": 0,
                  "demand": 1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L1",
                  "time_window_label": "none"
                },
                {
                  "id": "D1",
                  "request_id": "R1",
                  "kind": "delivery",
                  "x": 2,
                  "y": 0,
                  "demand": -1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L2",
                  "time_window_label": "none"
                },
                {
                  "id": "P2",
                  "request_id": "R2",
                  "kind": "pickup",
                  "x": 10,
                  "y": 10,
                  "demand": 1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L3",
                  "time_window_label": "none"
                },
                {
                  "id": "D2",
                  "request_id": "R2",
                  "kind": "delivery",
                  "x": 11,
                  "y": 10,
                  "demand": -1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L4",
                  "time_window_label": "none"
                }
              ],
              "metadata": {
                "request_count": 2,
                "node_count": 4,
                "location_count": 4,
                "vehicle_count": 1,
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
        .normalized()
        .unwrap()
    }

    #[test]
    fn small_route_optimizer_finds_better_feasible_order() {
        let instance = precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let route = Route {
            depot_idx: 0,
            vehicle_idx: 0,
            stops: vec![2, 3, 0, 1],
        };

        let optimizer = SmallRouteOptimizer::new(&instance, &matrix, &route).unwrap();
        let optimized = optimizer.solve().unwrap();

        assert_eq!(optimized.stops, vec![0, 1, 2, 3]);
        assert!(evaluate_route(&instance, &matrix, &optimized).feasible);
        assert!(
            evaluate_route(&instance, &matrix, &optimized).distance
                < evaluate_route(&instance, &matrix, &route).distance
        );
    }

    #[test]
    fn optimize_all_small_routes_updates_solution_in_place() {
        let instance = precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let mut solution = SolutionState {
            routes: vec![Route {
                depot_idx: 0,
                vehicle_idx: 0,
                stops: vec![2, 3, 0, 1],
            }],
            ..SolutionState::default()
        };

        assert!(optimize_all_small_routes(&instance, &matrix, &mut solution));
        assert_eq!(solution.routes[0].stops, vec![0, 1, 2, 3]);
    }
}
