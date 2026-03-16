use std::fs;
use std::path::Path;

use anyhow::Result;
use serde::Serialize;

use crate::alns::OperatorWeight;
use crate::evaluate::SolutionMetrics;
use crate::instance::Instance;
use crate::solution::SolutionState;

#[derive(Debug, Serialize)]
pub struct RouteOutput {
    pub route_index: usize,
    pub depot_id: String,
    pub vehicle_id: String,
    pub node_ids: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct SolverMetadata {
    pub iterations: usize,
    pub seed: u64,
    pub initial_objective: f64,
    pub operator_weights: Vec<OperatorWeight>,
}

#[derive(Debug, Serialize)]
pub struct SerializedSolution {
    pub instance: String,
    pub solver: String,
    pub objective: f64,
    pub route_count: usize,
    pub feasible: bool,
    pub routes: Vec<RouteOutput>,
    pub evaluation: SolutionMetrics,
    pub metadata: SolverMetadata,
}

pub fn solution_to_json(
    instance: &Instance,
    solution: &SolutionState,
    evaluation: SolutionMetrics,
    iterations: usize,
    seed: u64,
    initial_objective: f64,
    operator_weights: Vec<OperatorWeight>,
) -> SerializedSolution {
    let routes = solution
        .routes
        .iter()
        .enumerate()
        .map(|(route_index, route)| RouteOutput {
            route_index,
            depot_id: instance.depots[route.depot_idx].id.clone(),
            vehicle_id: instance.vehicle(route.vehicle_idx).id.clone(),
            node_ids: route
                .stops
                .iter()
                .map(|&node_idx| instance.nodes[node_idx].id.clone())
                .collect(),
        })
        .collect::<Vec<_>>();

    SerializedSolution {
        instance: instance.name.clone(),
        solver: "rust-alns".to_string(),
        objective: evaluation.objective,
        route_count: evaluation.route_count,
        feasible: evaluation.feasible,
        routes,
        evaluation,
        metadata: SolverMetadata {
            iterations,
            seed,
            initial_objective,
            operator_weights,
        },
    }
}

pub fn write_solution(path: &Path, solution: &SerializedSolution) -> Result<()> {
    fs::write(path, serde_json::to_string_pretty(solution)? + "\n")?;
    Ok(())
}
