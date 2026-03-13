use std::collections::{BTreeMap, BTreeSet};

use serde::Serialize;

use crate::distance::DistanceMatrix;
use crate::instance::Instance;
use crate::solution::{Route, SolutionState};

#[derive(Debug, Clone, Serialize)]
pub struct StopVisit {
    pub node_id: String,
    pub arrival: i64,
    pub start_service: i64,
    pub departure: i64,
    pub wait_duration: i64,
    pub load_after_service: i32,
}

#[derive(Debug, Clone, Serialize)]
pub struct RouteMetrics {
    pub depot_id: String,
    pub node_ids: Vec<String>,
    pub distance: i64,
    pub start_load: i32,
    pub max_load: i32,
    pub end_time: i64,
    pub feasible: bool,
    pub violations: Vec<String>,
    pub stops: Vec<StopVisit>,
}

#[derive(Debug, Clone, Serialize)]
pub struct SolutionMetrics {
    pub objective: i64,
    pub total_distance: i64,
    pub route_count: usize,
    pub visited_nodes: usize,
    pub unique_served_nodes: usize,
    pub feasible: bool,
    pub duplicate_nodes: Vec<String>,
    pub missing_nodes: Vec<String>,
    pub vehicle_usage: BTreeMap<String, usize>,
    pub vehicle_violations: Vec<String>,
    pub routes: Vec<RouteMetrics>,
}

pub fn evaluate_route(instance: &Instance, matrix: &DistanceMatrix, route: &Route) -> RouteMetrics {
    let depot = &instance.depots[route.depot_idx];
    let depot_location = matrix.depot_location(route.depot_idx);
    let mut violations = BTreeSet::new();
    let mut feasible = true;

    let start_load = route
        .stops
        .iter()
        .map(|&node_idx| (-instance.nodes[node_idx].demand).max(0))
        .sum::<i32>();

    if start_load > instance.capacity {
        feasible = false;
        violations.insert(format!("{}:initial_capacity", depot.id));
    }

    let mut current_load = start_load;
    let mut max_load = start_load;
    let mut current_time = depot.tw.start;
    let mut current_location = depot_location;
    let mut total_distance = 0_i64;
    let mut visits = Vec::with_capacity(route.stops.len());

    for &node_idx in &route.stops {
        let node = &instance.nodes[node_idx];
        let node_location = matrix.node_location(node_idx);
        let travel = matrix.distance(current_location, node_location);
        let arrival = current_time + travel;
        let start_service = arrival.max(node.tw.start);
        let wait_duration = start_service - arrival;

        if start_service > node.tw.end {
            feasible = false;
            violations.insert(format!("{}:time_window", node.id));
        }

        current_load += node.demand;
        max_load = max_load.max(current_load);

        if current_load < 0 || current_load > instance.capacity {
            feasible = false;
            violations.insert(format!("{}:capacity", node.id));
        }

        let departure = start_service + node.service_duration;
        total_distance += travel;
        visits.push(StopVisit {
            node_id: node.id.clone(),
            arrival,
            start_service,
            departure,
            wait_duration,
            load_after_service: current_load,
        });

        current_time = departure;
        current_location = node_location;
    }

    let return_distance = matrix.distance(current_location, depot_location);
    total_distance += return_distance;
    let end_time = current_time + return_distance;

    if end_time > depot.tw.end {
        feasible = false;
        violations.insert(format!("{}:depot_close", depot.id));
    }

    RouteMetrics {
        depot_id: depot.id.clone(),
        node_ids: route
            .stops
            .iter()
            .map(|&node_idx| instance.nodes[node_idx].id.clone())
            .collect(),
        distance: total_distance,
        start_load,
        max_load,
        end_time,
        feasible,
        violations: violations.into_iter().collect(),
        stops: visits,
    }
}

pub fn evaluate_solution(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
) -> SolutionMetrics {
    let mut objective = 0_i64;
    let mut feasible = true;
    let mut route_metrics = Vec::with_capacity(solution.routes.len());
    let mut visit_counts = instance
        .nodes
        .iter()
        .map(|node| (node.id.clone(), 0_usize))
        .collect::<BTreeMap<_, _>>();
    let mut vehicle_usage = instance
        .depots
        .iter()
        .map(|depot| (depot.id.clone(), 0_usize))
        .collect::<BTreeMap<_, _>>();

    for route in &solution.routes {
        let metrics = evaluate_route(instance, matrix, route);
        objective += metrics.distance;
        feasible &= metrics.feasible;

        if let Some(used) = vehicle_usage.get_mut(&instance.depots[route.depot_idx].id) {
            *used += 1;
        }

        for node_id in &metrics.node_ids {
            if let Some(count) = visit_counts.get_mut(node_id) {
                *count += 1;
            } else {
                feasible = false;
            }
        }

        route_metrics.push(metrics);
    }

    let duplicate_nodes = visit_counts
        .iter()
        .filter_map(|(node_id, &count)| (count > 1).then(|| node_id.clone()))
        .collect::<Vec<_>>();
    let missing_nodes = visit_counts
        .iter()
        .filter_map(|(node_id, &count)| (count == 0).then(|| node_id.clone()))
        .collect::<Vec<_>>();

    let mut vehicle_violations = Vec::new();
    for (depot_idx, depot) in instance.depots.iter().enumerate() {
        let used = vehicle_usage.get(&depot.id).copied().unwrap_or_default();
        let limit = instance.vehicle_limit(depot_idx);

        if used > limit {
            vehicle_violations.push(format!("{}:{}>{}", depot.id, used, limit));
        }
    }

    feasible &= duplicate_nodes.is_empty();
    feasible &= missing_nodes.is_empty();
    feasible &= vehicle_violations.is_empty();

    let visited_nodes = solution
        .routes
        .iter()
        .map(|route| route.stops.len())
        .sum::<usize>();
    let unique_served_nodes = visit_counts.values().filter(|&&count| count > 0).count();

    SolutionMetrics {
        objective,
        total_distance: objective,
        route_count: solution.routes.len(),
        visited_nodes,
        unique_served_nodes,
        feasible,
        duplicate_nodes,
        missing_nodes,
        vehicle_usage,
        vehicle_violations,
        routes: route_metrics,
    }
}

#[cfg(test)]
mod tests {
    use super::{evaluate_route, evaluate_solution};
    use crate::distance::DistanceMatrix;
    use crate::instance::Instance;
    use crate::solution::{Route, SolutionState};

    fn sample_instance() -> Instance {
        serde_json::from_str(
            r#"
            {
              "name": "sample",
              "seed": 1,
              "planning_horizon": { "start": 480, "end": 1080 },
              "capacity": 6,
              "vehicles_per_depot": { "D0": 2 },
              "depots": [
                { "id": "D0", "x": 0, "y": 0, "tw": { "start": 480, "end": 1080 } }
              ],
              "location_catalog": [
                { "id": "L00", "x": 3, "y": 4, "home_depot_id": "D0" },
                { "id": "L01", "x": 6, "y": 8, "home_depot_id": "D0" }
              ],
              "nodes": [
                {
                  "id": "P000",
                  "request_id": "R000",
                  "kind": "pickup",
                  "x": 3,
                  "y": 4,
                  "demand": 1,
                  "service_duration": 5,
                  "tw": { "start": 480, "end": 1080 },
                  "location_id": "L00",
                  "time_window_label": "none"
                },
                {
                  "id": "D000",
                  "request_id": "R000",
                  "kind": "delivery",
                  "x": 6,
                  "y": 8,
                  "demand": -1,
                  "service_duration": 5,
                  "tw": { "start": 480, "end": 1080 },
                  "location_id": "L01",
                  "time_window_label": "none"
                }
              ],
              "metadata": {
                "request_count": 1,
                "node_count": 2,
                "location_count": 2,
                "vehicle_count": 2,
                "variant": "test",
                "distance_metric": "euclidean_int_half_up",
                "time_window_distribution": { "none": 2 }
              }
            }
            "#,
        )
        .expect("sample instance should deserialize")
    }

    #[test]
    fn route_evaluation_is_feasible() {
        let instance = sample_instance();
        let matrix = DistanceMatrix::build(&instance);
        let route = Route {
            depot_idx: 0,
            stops: vec![1, 0],
        };

        let metrics = evaluate_route(&instance, &matrix, &route);
        assert!(metrics.feasible);
        assert_eq!(metrics.distance, 20);
        assert_eq!(metrics.start_load, 1);
    }

    #[test]
    fn duplicate_visits_are_detected() {
        let instance = sample_instance();
        let matrix = DistanceMatrix::build(&instance);
        let solution = SolutionState {
            routes: vec![Route {
                depot_idx: 0,
                stops: vec![0, 0],
            }],
        };

        let metrics = evaluate_solution(&instance, &matrix, &solution);
        assert!(!metrics.feasible);
        assert_eq!(metrics.duplicate_nodes, vec!["P000".to_string()]);
    }
}
