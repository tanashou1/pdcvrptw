use crate::distance::DistanceMatrix;
use crate::instance::{Instance, RequestPair};
use crate::solution::Route;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RouteSummary {
    pub distance: f64,
    pub end_time: f64,
    pub max_load: i32,
    pub feasible: bool,
}

#[derive(Debug, Clone)]
pub struct RouteEvaluationCache {
    start_load: i32,
    prefix_departures: Vec<f64>,
    prefix_distances: Vec<f64>,
    prefix_demands: Vec<i32>,
    prefix_max_demands: Vec<i32>,
    prefix_min_demands: Vec<i32>,
    summary: RouteSummary,
}

impl RouteEvaluationCache {
    pub fn new(instance: &Instance, matrix: &DistanceMatrix, route: &Route) -> Self {
        let depot = &instance.depots[route.depot_idx];
        let depot_location = matrix.depot_location(route.depot_idx);
        let start_load = initial_route_load(instance, route);
        let mut feasible = start_load <= instance.capacity;
        let mut current_time = depot.tw.start as f64;
        let mut current_location = depot_location;
        let mut current_load = start_load;
        let mut max_load = start_load;
        let mut total_distance = 0.0_f64;
        let mut prefix_departures = Vec::with_capacity(route.stops.len() + 1);
        let mut prefix_distances = Vec::with_capacity(route.stops.len() + 1);
        let mut prefix_demands = Vec::with_capacity(route.stops.len() + 1);
        let mut prefix_max_demands = Vec::with_capacity(route.stops.len() + 1);
        let mut prefix_min_demands = Vec::with_capacity(route.stops.len() + 1);
        let mut cumulative_demand = 0_i32;
        let mut max_cumulative_demand = 0_i32;
        let mut min_cumulative_demand = 0_i32;

        prefix_departures.push(current_time);
        prefix_distances.push(total_distance);
        prefix_demands.push(cumulative_demand);
        prefix_max_demands.push(max_cumulative_demand);
        prefix_min_demands.push(min_cumulative_demand);

        for &node_idx in &route.stops {
            let node = &instance.nodes[node_idx];
            let node_location = matrix.node_location(node_idx);
            let travel = matrix.distance(current_location, node_location);
            let arrival = current_time + travel;
            let start_service = arrival.max(node.tw.start as f64);

            if start_service > node.tw.end as f64 {
                feasible = false;
            }

            current_load += node.demand;
            if current_load < 0 || current_load > instance.capacity {
                feasible = false;
            }
            max_load = max_load.max(current_load);

            current_time = start_service + node.service_duration as f64;
            current_location = node_location;
            total_distance += travel;
            cumulative_demand += node.demand;
            max_cumulative_demand = max_cumulative_demand.max(cumulative_demand);
            min_cumulative_demand = min_cumulative_demand.min(cumulative_demand);

            prefix_departures.push(current_time);
            prefix_distances.push(total_distance);
            prefix_demands.push(cumulative_demand);
            prefix_max_demands.push(max_cumulative_demand);
            prefix_min_demands.push(min_cumulative_demand);
        }

        let return_distance = matrix.distance(current_location, depot_location);
        total_distance += return_distance;
        let end_time = current_time + return_distance;
        if end_time > depot.tw.end as f64 {
            feasible = false;
        }

        Self {
            start_load,
            prefix_departures,
            prefix_distances,
            prefix_demands,
            prefix_max_demands,
            prefix_min_demands,
            summary: RouteSummary {
                distance: instance.serialise_distance(total_distance),
                end_time: serialise_time(instance, end_time),
                max_load,
                feasible,
            },
        }
    }

    pub fn summary(&self) -> RouteSummary {
        self.summary
    }
}

pub fn summarize_route(
    instance: &Instance,
    matrix: &DistanceMatrix,
    route: &Route,
) -> RouteSummary {
    RouteEvaluationCache::new(instance, matrix, route).summary()
}

pub fn evaluate_insertion(
    instance: &Instance,
    matrix: &DistanceMatrix,
    route: &Route,
    cache: &RouteEvaluationCache,
    node_idx: usize,
    position: usize,
) -> RouteSummary {
    evaluate_suffix(
        instance,
        matrix,
        route,
        cache,
        position,
        start_load_contribution(instance, node_idx),
        std::iter::once(node_idx).chain(route.stops[position..].iter().copied()),
    )
}

pub fn evaluate_pair_insertion(
    instance: &Instance,
    matrix: &DistanceMatrix,
    route: &Route,
    cache: &RouteEvaluationCache,
    pair: &RequestPair,
    pickup_position: usize,
    delivery_position: usize,
) -> RouteSummary {
    evaluate_suffix(
        instance,
        matrix,
        route,
        cache,
        pickup_position,
        start_load_contribution(instance, pair.delivery_idx),
        std::iter::once(pair.pickup_idx)
            .chain(
                route.stops[pickup_position..(delivery_position - 1)]
                    .iter()
                    .copied(),
            )
            .chain(std::iter::once(pair.delivery_idx))
            .chain(route.stops[(delivery_position - 1)..].iter().copied()),
    )
}

pub fn evaluate_request_removal(
    instance: &Instance,
    matrix: &DistanceMatrix,
    route: &Route,
    cache: &RouteEvaluationCache,
    request: &RequestPair,
) -> Option<RouteSummary> {
    let pickup_position = route
        .stops
        .iter()
        .position(|&node_idx| node_idx == request.pickup_idx)?;
    route
        .stops
        .iter()
        .position(|&node_idx| node_idx == request.delivery_idx)?;

    Some(evaluate_suffix(
        instance,
        matrix,
        route,
        cache,
        pickup_position,
        -start_load_contribution(instance, request.delivery_idx),
        route.stops[pickup_position..]
            .iter()
            .copied()
            .filter(|&node_idx| node_idx != request.pickup_idx && node_idx != request.delivery_idx),
    ))
}

fn evaluate_suffix<I>(
    instance: &Instance,
    matrix: &DistanceMatrix,
    route: &Route,
    cache: &RouteEvaluationCache,
    prefix_len: usize,
    start_load_delta: i32,
    suffix_nodes: I,
) -> RouteSummary
where
    I: IntoIterator<Item = usize>,
{
    let depot = &instance.depots[route.depot_idx];
    let depot_location = matrix.depot_location(route.depot_idx);
    let start_load = cache.start_load + start_load_delta;
    let prefix_max_load = start_load + cache.prefix_max_demands[prefix_len];
    let prefix_min_load = start_load + cache.prefix_min_demands[prefix_len];
    let mut feasible = start_load >= 0
        && start_load <= instance.capacity
        && prefix_min_load >= 0
        && prefix_max_load <= instance.capacity;
    let mut current_time = cache.prefix_departures[prefix_len];
    let mut current_location = if prefix_len == 0 {
        depot_location
    } else {
        matrix.node_location(route.stops[prefix_len - 1])
    };
    let mut current_load = start_load + cache.prefix_demands[prefix_len];
    let mut max_load = prefix_max_load.max(start_load);
    let mut total_distance = cache.prefix_distances[prefix_len];

    for node_idx in suffix_nodes {
        let node = &instance.nodes[node_idx];
        let node_location = matrix.node_location(node_idx);
        let travel = matrix.distance(current_location, node_location);
        let arrival = current_time + travel;
        let start_service = arrival.max(node.tw.start as f64);

        if start_service > node.tw.end as f64 {
            feasible = false;
        }

        current_load += node.demand;
        if current_load < 0 || current_load > instance.capacity {
            feasible = false;
        }
        max_load = max_load.max(current_load);

        current_time = start_service + node.service_duration as f64;
        current_location = node_location;
        total_distance += travel;
    }

    let return_distance = matrix.distance(current_location, depot_location);
    total_distance += return_distance;
    let end_time = current_time + return_distance;
    if end_time > depot.tw.end as f64 {
        feasible = false;
    }

    RouteSummary {
        distance: instance.serialise_distance(total_distance),
        end_time: serialise_time(instance, end_time),
        max_load,
        feasible,
    }
}

fn initial_route_load(instance: &Instance, route: &Route) -> i32 {
    if instance.uses_balanced_start_load() {
        route
            .stops
            .iter()
            .map(|&node_idx| start_load_contribution(instance, node_idx))
            .sum()
    } else {
        0
    }
}

fn start_load_contribution(instance: &Instance, node_idx: usize) -> i32 {
    if instance.uses_balanced_start_load() {
        (-instance.nodes[node_idx].demand).max(0)
    } else {
        0
    }
}

fn serialise_time(instance: &Instance, value: f64) -> f64 {
    if instance.uses_double_distance() {
        (value * 1_000_000.0).round() / 1_000_000.0
    } else {
        value.round()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        evaluate_insertion, evaluate_pair_insertion, evaluate_request_removal, summarize_route,
        RouteEvaluationCache, RouteSummary,
    };
    use crate::distance::DistanceMatrix;
    use crate::evaluate::evaluate_route;
    use crate::instance::{Instance, RequestPair};
    use crate::solution::Route;

    fn non_precedence_instance() -> Instance {
        serde_json::from_str(
            r#"
            {
              "name": "route_eval_non_precedence",
              "seed": 1,
              "planning_horizon": { "start": 0, "end": 200 },
              "capacity": 6,
              "vehicles_per_depot": { "D0": 2 },
              "depots": [
                { "id": "D0", "x": 0, "y": 0, "tw": { "start": 0, "end": 200 } }
              ],
              "nodes": [
                {
                  "id": "N0",
                  "request_id": "R0",
                  "kind": "pickup",
                  "x": 1,
                  "y": 0,
                  "demand": 2,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L0",
                  "time_window_label": "none"
                },
                {
                  "id": "N1",
                  "request_id": "R1",
                  "kind": "delivery",
                  "x": 2,
                  "y": 0,
                  "demand": -2,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L1",
                  "time_window_label": "none"
                },
                {
                  "id": "N2",
                  "request_id": "R2",
                  "kind": "pickup",
                  "x": 3,
                  "y": 0,
                  "demand": 1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L2",
                  "time_window_label": "none"
                },
                {
                  "id": "N3",
                  "request_id": "R3",
                  "kind": "delivery",
                  "x": 4,
                  "y": 0,
                  "demand": -1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "L3",
                  "time_window_label": "none"
                }
              ],
              "metadata": {
                "request_count": 4,
                "node_count": 4,
                "location_count": 4,
                "vehicle_count": 2,
                "variant": "test",
                "benchmark_group": "test",
                "distance_metric": "euclidean_int_half_up",
                "load_profile": "balanced_start",
                "objective_mode": "distance_only",
                "enforce_precedence": false
              }
            }
            "#,
        )
        .unwrap()
    }

    fn precedence_instance() -> Instance {
        serde_json::from_str(
            r#"
            {
              "name": "route_eval_precedence",
              "seed": 1,
              "planning_horizon": { "start": 0, "end": 200 },
              "capacity": 6,
              "vehicles_per_depot": { "D0": 2 },
              "depots": [
                { "id": "D0", "x": 0, "y": 0, "tw": { "start": 0, "end": 200 } }
              ],
              "nodes": [
                {
                  "id": "P0",
                  "request_id": "R0",
                  "kind": "pickup",
                  "x": 1,
                  "y": 0,
                  "demand": 2,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "LP0",
                  "time_window_label": "none"
                },
                {
                  "id": "D0",
                  "request_id": "R0",
                  "kind": "delivery",
                  "x": 2,
                  "y": 0,
                  "demand": -2,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "LD0",
                  "time_window_label": "none"
                },
                {
                  "id": "P1",
                  "request_id": "R1",
                  "kind": "pickup",
                  "x": 3,
                  "y": 0,
                  "demand": 1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "LP1",
                  "time_window_label": "none"
                },
                {
                  "id": "D1",
                  "request_id": "R1",
                  "kind": "delivery",
                  "x": 4,
                  "y": 0,
                  "demand": -1,
                  "service_duration": 0,
                  "tw": { "start": 0, "end": 200 },
                  "location_id": "LD1",
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
                "distance_metric": "euclidean_int_half_up",
                "load_profile": "balanced_start",
                "objective_mode": "vehicles_then_distance",
                "enforce_precedence": true
              }
            }
            "#,
        )
        .unwrap()
    }

    fn request_pair(request_id: &str, pickup_idx: usize, delivery_idx: usize) -> RequestPair {
        RequestPair {
            request_id: request_id.to_string(),
            pickup_idx,
            delivery_idx,
        }
    }

    fn assert_matches(summary: RouteSummary, route_metrics: &crate::evaluate::RouteMetrics) {
        assert_eq!(summary.distance, route_metrics.distance);
        assert_eq!(summary.end_time, route_metrics.end_time);
        assert_eq!(summary.max_load, route_metrics.max_load);
        assert_eq!(summary.feasible, route_metrics.feasible);
    }

    #[test]
    fn summarize_route_matches_full_route_evaluation() {
        let instance = non_precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let route = Route {
            depot_idx: 0,
            stops: vec![0, 1, 2],
        };

        let summary = summarize_route(&instance, &matrix, &route);
        let route_metrics = evaluate_route(&instance, &matrix, &route);
        assert_matches(summary, &route_metrics);
    }

    #[test]
    fn incremental_single_insertion_matches_full_route_evaluation() {
        let instance = non_precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let route = Route {
            depot_idx: 0,
            stops: vec![0, 1, 2],
        };
        let cache = RouteEvaluationCache::new(&instance, &matrix, &route);

        for position in 0..=route.stops.len() {
            let mut candidate = route.clone();
            candidate.stops.insert(position, 3);
            let summary = evaluate_insertion(&instance, &matrix, &route, &cache, 3, position);
            let route_metrics = evaluate_route(&instance, &matrix, &candidate);
            assert_matches(summary, &route_metrics);
        }
    }

    #[test]
    fn incremental_pair_insertion_matches_full_route_evaluation() {
        let instance = precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let route = Route {
            depot_idx: 0,
            stops: vec![0, 1],
        };
        let cache = RouteEvaluationCache::new(&instance, &matrix, &route);
        let pair = request_pair("R1", 2, 3);

        for pickup_position in 0..=route.stops.len() {
            for delivery_position in (pickup_position + 1)..=(route.stops.len() + 1) {
                let mut candidate = route.clone();
                candidate.stops.insert(pickup_position, pair.pickup_idx);
                candidate.stops.insert(delivery_position, pair.delivery_idx);
                let summary = evaluate_pair_insertion(
                    &instance,
                    &matrix,
                    &route,
                    &cache,
                    &pair,
                    pickup_position,
                    delivery_position,
                );
                let route_metrics = evaluate_route(&instance, &matrix, &candidate);
                assert_matches(summary, &route_metrics);
            }
        }
    }

    #[test]
    fn incremental_request_removal_matches_full_route_evaluation() {
        let instance = precedence_instance();
        let matrix = DistanceMatrix::build(&instance);
        let route = Route {
            depot_idx: 0,
            stops: vec![0, 2, 1, 3],
        };
        let cache = RouteEvaluationCache::new(&instance, &matrix, &route);

        for request in [request_pair("R0", 0, 1), request_pair("R1", 2, 3)] {
            let mut candidate = route.clone();
            candidate.stops.retain(|&node_idx| {
                node_idx != request.pickup_idx && node_idx != request.delivery_idx
            });
            let summary =
                evaluate_request_removal(&instance, &matrix, &route, &cache, &request).unwrap();
            let route_metrics = evaluate_route(&instance, &matrix, &candidate);
            assert_matches(summary, &route_metrics);
        }
    }
}
