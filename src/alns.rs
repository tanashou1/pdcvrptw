use anyhow::{bail, Result};
use rand::prelude::SliceRandom;
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use serde::Serialize;

use crate::construction::{
    build_initial_solution, compact_routes, repair_nodes_with_options, RepairOptions,
};
use crate::distance::DistanceMatrix;
use crate::evaluate::evaluate_solution;
use crate::exact_route::{intensify_small_route_order, optimize_all_small_routes};
use crate::instance::{Instance, RequestPair};
use crate::route_eval::{evaluate_request_removal, summarize_route, RouteEvaluationCache};
use crate::solution::SolutionState;

const SMALL_ROUTE_DP_INTERVAL: usize = 100;

#[derive(Debug, Clone)]
pub struct SolveParams {
    pub iterations: usize,
    pub seed: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct OperatorWeight {
    pub name: String,
    pub weight: f64,
}

#[derive(Debug, Clone)]
pub struct SolveOutcome {
    pub initial_objective: f64,
    pub best_solution: SolutionState,
    pub operator_weights: Vec<OperatorWeight>,
}

#[derive(Debug, Copy, Clone)]
enum DestroyOperator {
    Random,
    Worst,
    Shaw,
    RouteReduction,
}

impl DestroyOperator {
    fn all() -> [Self; 4] {
        [Self::Random, Self::Worst, Self::Shaw, Self::RouteReduction]
    }

    fn name(self) -> &'static str {
        match self {
            Self::Random => "random_removal",
            Self::Worst => "worst_removal",
            Self::Shaw => "shaw_removal",
            Self::RouteReduction => "route_reduction",
        }
    }
}

#[derive(Debug, Clone)]
struct DestroyOutcome {
    removed_nodes: Vec<usize>,
    allow_new_routes: bool,
}

pub fn solve(
    instance: &Instance,
    matrix: &DistanceMatrix,
    params: &SolveParams,
) -> Result<SolveOutcome> {
    let initial_solution = build_initial_solution(instance, matrix)?;
    let initial_metrics = evaluate_solution(instance, matrix, &initial_solution);

    if !initial_metrics.feasible {
        bail!("initial solution is infeasible for {}", instance.name);
    }

    let mut current_solution = initial_solution.clone();
    let mut current_score = initial_metrics.search_objective;
    let mut best_solution = initial_solution;
    let mut best_score = current_score;
    let mut weights = vec![1.0_f64; DestroyOperator::all().len()];
    let mut temperature = current_score.max(1.0) * 0.05;
    let mut rng = StdRng::seed_from_u64(params.seed);

    for iteration in 0..params.iterations {
        let operator_index = select_operator(&weights, &mut rng);
        let operator = DestroyOperator::all()[operator_index];
        let mut candidate_solution = current_solution.clone();
        let unit_count = removal_unit_count(instance, &candidate_solution);
        let remove_count = removal_count(unit_count, &mut rng);
        let destroy_outcome = apply_destroy(
            instance,
            matrix,
            &mut candidate_solution,
            operator,
            remove_count,
            &mut rng,
        );

        let mut pending_nodes = destroy_outcome.removed_nodes;
        pending_nodes.extend(candidate_solution.take_unassigned_nodes());
        pending_nodes.sort_unstable();
        pending_nodes.dedup();

        if pending_nodes.is_empty() {
            continue;
        }

        if !repair_nodes_with_options(
            instance,
            matrix,
            &mut candidate_solution,
            &pending_nodes,
            RepairOptions {
                allow_new_routes: destroy_outcome.allow_new_routes,
            },
        ) {
            update_weight(&mut weights[operator_index], 0.25);
            continue;
        }

        if !destroy_outcome.allow_new_routes {
            compact_routes(instance, matrix, &mut candidate_solution);
        }

        let candidate_metrics = evaluate_solution(instance, matrix, &candidate_solution);
        if !candidate_metrics.feasible {
            update_weight(&mut weights[operator_index], 0.25);
            continue;
        }

        let candidate_score = candidate_metrics.search_objective;
        let delta = candidate_score - current_score;
        let accepted = if delta <= 0.0 {
            true
        } else {
            let acceptance_probability = (-(delta) / temperature.max(1.0)).exp();
            rng.gen::<f64>() < acceptance_probability
        };

        let reward = if candidate_score < best_score {
            8.0
        } else if candidate_score < current_score {
            4.0
        } else if accepted {
            1.5
        } else {
            0.5
        };

        update_weight(&mut weights[operator_index], reward);

        if accepted {
            current_score = candidate_score;
            current_solution = candidate_solution.clone();
        }

        if candidate_score < best_score {
            best_score = candidate_score;
            best_solution = candidate_solution;
        }

        if should_run_small_route_dp(iteration) {
            let mut intensified_best = best_solution.clone();
            if intensify_small_route_order(instance, matrix, &mut intensified_best, &mut rng) {
                let intensified_metrics = evaluate_solution(instance, matrix, &intensified_best);
                if intensified_metrics.feasible && intensified_metrics.search_objective < best_score
                {
                    best_score = intensified_metrics.search_objective;
                    best_solution = intensified_best.clone();
                    if best_score < current_score {
                        current_score = best_score;
                        current_solution = intensified_best;
                    }
                }
            }
        }

        temperature = (temperature * 0.9985).max(0.5);
    }

    optimize_all_small_routes(instance, matrix, &mut best_solution);

    Ok(SolveOutcome {
        initial_objective: initial_metrics.objective,
        best_solution,
        operator_weights: DestroyOperator::all()
            .iter()
            .zip(weights.iter())
            .map(|(operator, weight)| OperatorWeight {
                name: operator.name().to_string(),
                weight: *weight,
            })
            .collect(),
    })
}

fn select_operator(weights: &[f64], rng: &mut StdRng) -> usize {
    let total_weight = weights.iter().sum::<f64>();
    let mut draw = rng.gen::<f64>() * total_weight;

    for (index, weight) in weights.iter().enumerate() {
        draw -= *weight;
        if draw <= 0.0 {
            return index;
        }
    }

    weights.len().saturating_sub(1)
}

fn update_weight(weight: &mut f64, reward: f64) {
    *weight = (0.85 * *weight) + (0.15 * reward);
}

fn should_run_small_route_dp(iteration: usize) -> bool {
    (iteration + 1) % SMALL_ROUTE_DP_INTERVAL == 0
}

fn removal_count(unit_count: usize, rng: &mut StdRng) -> usize {
    let upper = usize::min(12, unit_count.max(1));
    let lower = usize::min(4, upper);
    rng.gen_range(lower..=upper)
}

fn removal_unit_count(instance: &Instance, solution: &SolutionState) -> usize {
    if instance.enforces_precedence() {
        request_pairs_in_solution(instance, solution)
            .into_iter()
            .filter(|request| request_is_removable(instance, request))
            .count()
    } else {
        solution
            .all_nodes()
            .into_iter()
            .filter(|node_idx| node_is_removable(instance, *node_idx))
            .count()
    }
}

fn apply_destroy(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    operator: DestroyOperator,
    remove_count: usize,
    rng: &mut StdRng,
) -> DestroyOutcome {
    let (removed_nodes, allow_new_routes) = if instance.enforces_precedence() {
        match operator {
            DestroyOperator::Random => (
                random_request_removal(instance, solution, remove_count, rng),
                true,
            ),
            DestroyOperator::Worst => (
                worst_request_removal(instance, matrix, solution, remove_count),
                true,
            ),
            DestroyOperator::Shaw => (
                shaw_request_removal(instance, matrix, solution, remove_count, rng),
                true,
            ),
            DestroyOperator::RouteReduction => (
                route_reduction_removal(instance, matrix, solution, remove_count, rng),
                false,
            ),
        }
    } else {
        match operator {
            DestroyOperator::Random => {
                (random_removal(instance, solution, remove_count, rng), true)
            }
            DestroyOperator::Worst => (
                worst_removal(instance, solution, matrix, remove_count),
                true,
            ),
            DestroyOperator::Shaw => (
                shaw_removal(solution, instance, matrix, remove_count, rng),
                true,
            ),
            DestroyOperator::RouteReduction => (
                route_reduction_removal(instance, matrix, solution, remove_count, rng),
                false,
            ),
        }
    };

    solution.remove_nodes(&removed_nodes);
    DestroyOutcome {
        removed_nodes,
        allow_new_routes,
    }
}

fn random_removal(
    instance: &Instance,
    solution: &SolutionState,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    let mut nodes = solution
        .all_nodes()
        .into_iter()
        .filter(|node_idx| node_is_removable(instance, *node_idx))
        .collect::<Vec<_>>();
    nodes.shuffle(rng);
    nodes.into_iter().take(remove_count).collect()
}

fn random_request_removal(
    instance: &Instance,
    solution: &SolutionState,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    let mut requests = request_pairs_in_solution(instance, solution)
        .into_iter()
        .filter(|request| request_is_removable(instance, request))
        .collect::<Vec<_>>();
    requests.shuffle(rng);
    requests.truncate(remove_count);
    flatten_requests(&requests)
}

fn worst_removal(
    instance: &Instance,
    solution: &SolutionState,
    matrix: &DistanceMatrix,
    remove_count: usize,
) -> Vec<usize> {
    let mut candidates = Vec::new();

    for route in &solution.routes {
        let depot_location = matrix.depot_location(route.depot_idx);

        for (position, &node_idx) in route.stops.iter().enumerate() {
            if !node_is_removable(instance, node_idx) {
                continue;
            }
            let previous_location = if position == 0 {
                depot_location
            } else {
                matrix.node_location(route.stops[position - 1])
            };
            let next_location = if position + 1 == route.stops.len() {
                depot_location
            } else {
                matrix.node_location(route.stops[position + 1])
            };
            let current_location = matrix.node_location(node_idx);
            let saving = matrix.distance(previous_location, current_location)
                + matrix.distance(current_location, next_location)
                - matrix.distance(previous_location, next_location);

            candidates.push((node_idx, saving));
        }
    }

    candidates.sort_by(|left, right| right.1.total_cmp(&left.1));
    candidates
        .into_iter()
        .take(remove_count)
        .map(|(node_idx, _)| node_idx)
        .collect()
}

fn worst_request_removal(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    remove_count: usize,
) -> Vec<usize> {
    let mut candidates = Vec::new();

    for route in &solution.routes {
        let cache = RouteEvaluationCache::new(instance, matrix, route);
        let route_distance = cache.summary().distance;

        for request in requests_in_route(instance, route) {
            if !request_is_removable(instance, &request) {
                continue;
            }
            if let Some(summary) =
                evaluate_request_removal(instance, matrix, route, &cache, &request)
            {
                candidates.push((request, route_distance - summary.distance));
            }
        }
    }

    candidates.sort_by(|left, right| right.1.total_cmp(&left.1));
    flatten_requests(
        &candidates
            .into_iter()
            .take(remove_count)
            .map(|(request, _)| request)
            .collect::<Vec<_>>(),
    )
}

fn shaw_removal(
    solution: &SolutionState,
    instance: &Instance,
    matrix: &DistanceMatrix,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    let all_nodes = solution
        .all_nodes()
        .into_iter()
        .filter(|node_idx| node_is_removable(instance, *node_idx))
        .collect::<Vec<_>>();
    let Some(&seed_node_idx) = all_nodes.choose(rng) else {
        return Vec::new();
    };

    let seed_node = &instance.nodes[seed_node_idx];
    let mut ranked = all_nodes
        .into_iter()
        .map(|node_idx| {
            let node = &instance.nodes[node_idx];
            let geography = matrix.distance(
                matrix.node_location(seed_node_idx),
                matrix.node_location(node_idx),
            );
            let time_window_gap = (seed_node.tw.start - node.tw.start).abs() as f64
                + (seed_node.tw.end - node.tw.end).abs() as f64;
            let demand_gap = (seed_node.demand - node.demand).abs() as f64 * 10.0;
            (node_idx, geography + time_window_gap + demand_gap)
        })
        .collect::<Vec<_>>();

    ranked.sort_by(|left, right| left.1.total_cmp(&right.1));
    ranked
        .into_iter()
        .take(remove_count)
        .map(|(node_idx, _)| node_idx)
        .collect()
}

fn shaw_request_removal(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &SolutionState,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    let requests = request_pairs_in_solution(instance, solution)
        .into_iter()
        .filter(|request| request_is_removable(instance, request))
        .collect::<Vec<_>>();
    let Some(seed_request) = requests.choose(rng).cloned() else {
        return Vec::new();
    };

    let seed_pickup = &instance.nodes[seed_request.pickup_idx];
    let seed_delivery = &instance.nodes[seed_request.delivery_idx];
    let mut ranked = requests
        .into_iter()
        .map(|request| {
            let pickup = &instance.nodes[request.pickup_idx];
            let delivery = &instance.nodes[request.delivery_idx];
            let pickup_distance = matrix.distance(
                matrix.node_location(seed_request.pickup_idx),
                matrix.node_location(request.pickup_idx),
            );
            let delivery_distance = matrix.distance(
                matrix.node_location(seed_request.delivery_idx),
                matrix.node_location(request.delivery_idx),
            );
            let time_gap = (seed_pickup.tw.start - pickup.tw.start).abs() as f64
                + (seed_pickup.tw.end - pickup.tw.end).abs() as f64
                + (seed_delivery.tw.start - delivery.tw.start).abs() as f64
                + (seed_delivery.tw.end - delivery.tw.end).abs() as f64;
            let demand_gap = (seed_pickup.demand - pickup.demand).abs() as f64
                + (seed_delivery.demand - delivery.demand).abs() as f64;

            (
                request,
                pickup_distance + delivery_distance + time_gap + demand_gap * 10.0,
            )
        })
        .collect::<Vec<_>>();

    ranked.sort_by(|left, right| left.1.total_cmp(&right.1));
    flatten_requests(
        &ranked
            .into_iter()
            .take(remove_count)
            .map(|(request, _)| request)
            .collect::<Vec<_>>(),
    )
}

fn route_reduction_removal(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    if solution.routes.len() <= 1 {
        return Vec::new();
    }

    let mut ranked = solution
        .routes
        .iter()
        .enumerate()
        .filter(|(_, route)| {
            route
                .stops
                .iter()
                .all(|node_idx| node_is_removable(instance, *node_idx))
        })
        .map(|(route_index, route)| {
            let unit_count = if instance.enforces_precedence() {
                requests_in_route(instance, route).len()
            } else {
                route.stops.len()
            };
            let metrics = summarize_route(instance, matrix, route);
            (route_index, unit_count, route.stops.len(), metrics.distance)
        })
        .collect::<Vec<_>>();

    ranked.sort_by(|left, right| {
        left.1
            .cmp(&right.1)
            .then_with(|| left.2.cmp(&right.2))
            .then_with(|| left.3.total_cmp(&right.3))
    });

    let shortlist = ranked
        .into_iter()
        .take(usize::min(3, solution.routes.len()))
        .collect::<Vec<_>>();
    let Some((route_index, _, _, _)) = shortlist.choose(rng).copied() else {
        return Vec::new();
    };

    let removed_nodes = solution.routes[route_index].stops.clone();
    solution.routes.remove(route_index);
    let support_remove_count = usize::min(3, usize::max(1, remove_count / 4));
    let mut additional_nodes = if instance.enforces_precedence() {
        worst_request_removal(instance, matrix, solution, support_remove_count)
    } else {
        worst_removal(instance, solution, matrix, support_remove_count)
    };

    let mut combined = removed_nodes;
    combined.append(&mut additional_nodes);
    combined.sort_unstable();
    combined.dedup();
    combined
}

fn request_pairs_in_solution(instance: &Instance, solution: &SolutionState) -> Vec<RequestPair> {
    let all_nodes = solution.all_nodes();
    instance.request_pairs_from_nodes(&all_nodes)
}

fn requests_in_route(instance: &Instance, route: &crate::solution::Route) -> Vec<RequestPair> {
    instance.request_pairs_from_nodes(&route.stops)
}

fn node_is_removable(instance: &Instance, node_idx: usize) -> bool {
    !instance.node_is_fixed(node_idx)
}

fn request_is_removable(instance: &Instance, request: &RequestPair) -> bool {
    node_is_removable(instance, request.pickup_idx)
        && node_is_removable(instance, request.delivery_idx)
}

fn flatten_requests(requests: &[RequestPair]) -> Vec<usize> {
    requests
        .iter()
        .flat_map(|request| [request.pickup_idx, request.delivery_idx])
        .collect()
}
