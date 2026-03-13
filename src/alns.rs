use anyhow::{bail, Result};
use rand::prelude::SliceRandom;
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use serde::Serialize;

use crate::construction::{build_initial_solution, repair_nodes};
use crate::distance::DistanceMatrix;
use crate::evaluate::evaluate_solution;
use crate::instance::Instance;
use crate::solution::SolutionState;

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
    pub initial_objective: i64,
    pub best_solution: SolutionState,
    pub operator_weights: Vec<OperatorWeight>,
}

#[derive(Debug, Copy, Clone)]
enum DestroyOperator {
    Random,
    Worst,
    Shaw,
}

impl DestroyOperator {
    fn all() -> [Self; 3] {
        [Self::Random, Self::Worst, Self::Shaw]
    }

    fn name(self) -> &'static str {
        match self {
            Self::Random => "random_removal",
            Self::Worst => "worst_removal",
            Self::Shaw => "shaw_removal",
        }
    }
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
    let mut current_objective = initial_metrics.objective;
    let mut best_solution = initial_solution;
    let mut best_objective = current_objective;
    let mut weights = vec![1.0_f64; DestroyOperator::all().len()];
    let mut temperature = (current_objective.max(1) as f64) * 0.05;
    let mut rng = StdRng::seed_from_u64(params.seed);

    for _ in 0..params.iterations {
        let operator_index = select_operator(&weights, &mut rng);
        let operator = DestroyOperator::all()[operator_index];
        let mut candidate_solution = current_solution.clone();
        let remove_count = removal_count(candidate_solution.all_nodes().len(), &mut rng);
        let removed_nodes = apply_destroy(
            instance,
            matrix,
            &mut candidate_solution,
            operator,
            remove_count,
            &mut rng,
        );

        if removed_nodes.is_empty() {
            continue;
        }

        if !repair_nodes(instance, matrix, &mut candidate_solution, &removed_nodes) {
            update_weight(&mut weights[operator_index], 0.25);
            continue;
        }

        let candidate_metrics = evaluate_solution(instance, matrix, &candidate_solution);
        if !candidate_metrics.feasible {
            update_weight(&mut weights[operator_index], 0.25);
            continue;
        }

        let candidate_objective = candidate_metrics.objective;
        let delta = candidate_objective - current_objective;
        let accepted = if delta <= 0 {
            true
        } else {
            let acceptance_probability = (-(delta as f64) / temperature.max(1.0)).exp();
            rng.gen::<f64>() < acceptance_probability
        };

        let reward = if candidate_objective < best_objective {
            8.0
        } else if candidate_objective < current_objective {
            4.0
        } else if accepted {
            1.5
        } else {
            0.5
        };

        update_weight(&mut weights[operator_index], reward);

        if accepted {
            current_objective = candidate_objective;
            current_solution = candidate_solution.clone();
        }

        if candidate_objective < best_objective {
            best_objective = candidate_objective;
            best_solution = candidate_solution;
        }

        temperature = (temperature * 0.997).max(0.5);
    }

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

fn removal_count(node_count: usize, rng: &mut StdRng) -> usize {
    let upper = usize::min(12, node_count.max(1));
    let lower = usize::min(4, upper);
    rng.gen_range(lower..=upper)
}

fn apply_destroy(
    instance: &Instance,
    matrix: &DistanceMatrix,
    solution: &mut SolutionState,
    operator: DestroyOperator,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    let removed_nodes = match operator {
        DestroyOperator::Random => random_removal(solution, remove_count, rng),
        DestroyOperator::Worst => worst_removal(solution, matrix, remove_count),
        DestroyOperator::Shaw => shaw_removal(solution, instance, matrix, remove_count, rng),
    };
    solution.remove_nodes(&removed_nodes);
    removed_nodes
}

fn random_removal(solution: &SolutionState, remove_count: usize, rng: &mut StdRng) -> Vec<usize> {
    let mut nodes = solution.all_nodes();
    nodes.shuffle(rng);
    nodes.truncate(remove_count);
    nodes
}

fn worst_removal(
    solution: &SolutionState,
    matrix: &DistanceMatrix,
    remove_count: usize,
) -> Vec<usize> {
    let mut candidates = Vec::new();

    for route in &solution.routes {
        let depot_location = matrix.depot_location(route.depot_idx);

        for (position, &node_idx) in route.stops.iter().enumerate() {
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

    candidates.sort_by(|left, right| right.1.cmp(&left.1));
    candidates
        .into_iter()
        .take(remove_count)
        .map(|(node_idx, _)| node_idx)
        .collect()
}

fn shaw_removal(
    solution: &SolutionState,
    instance: &Instance,
    matrix: &DistanceMatrix,
    remove_count: usize,
    rng: &mut StdRng,
) -> Vec<usize> {
    let all_nodes = solution.all_nodes();
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
            let time_window_gap =
                (seed_node.tw.start - node.tw.start).abs() + (seed_node.tw.end - node.tw.end).abs();
            let demand_gap = (seed_node.demand - node.demand).abs() as i64 * 10;
            (node_idx, geography + time_window_gap + demand_gap)
        })
        .collect::<Vec<_>>();

    ranked.sort_by_key(|(_, score)| *score);
    ranked
        .into_iter()
        .take(remove_count)
        .map(|(node_idx, _)| node_idx)
        .collect()
}
