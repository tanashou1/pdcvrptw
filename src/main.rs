use std::fs;
use std::path::{Path, PathBuf};
use std::{env, str::FromStr};

use anyhow::{bail, Result};
use serde::Serialize;

use pdcvrptw::alns::{solve, RouteCapture, SolveOutcome, SolveParams};
use pdcvrptw::distance::DistanceMatrix;
use pdcvrptw::evaluate::evaluate_solution;
use pdcvrptw::instance::{instance_paths, Instance};
use pdcvrptw::output::{solution_to_json, write_solution};

#[derive(Debug)]
struct SolveCommand {
    instances_dir: PathBuf,
    output_dir: PathBuf,
    iterations: usize,
    seed: u64,
}

#[derive(Debug, Serialize)]
struct SummaryRecord {
    instance: String,
    initial_objective: f64,
    best_objective: f64,
    route_count: usize,
    feasible: bool,
    missing_required_count: usize,
    missing_optional_count: usize,
}

#[derive(Debug, Serialize)]
struct Summary {
    solutions: Vec<SummaryRecord>,
}

#[derive(Debug)]
struct AnimateCommand {
    instance_path: PathBuf,
    output_path: PathBuf,
    iterations: usize,
    seed: u64,
}

#[derive(Debug, Serialize)]
struct RouteHistoryEntry {
    depot_id: String,
    node_ids: Vec<String>,
}

#[derive(Debug, Serialize)]
struct SnapshotOutput {
    iteration: usize,
    temperature: f64,
    candidate_score: f64,
    best_score: f64,
    accepted: bool,
    best_updated: bool,
    candidate_routes: Vec<RouteHistoryEntry>,
    best_routes: Vec<RouteHistoryEntry>,
}

#[derive(Debug, Serialize)]
struct HistoryOutput {
    instance_name: String,
    initial_score: f64,
    total_iterations: usize,
    snapshots: Vec<SnapshotOutput>,
}

fn main() -> Result<()> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    match args.first().map(String::as_str) {
        Some("solve") => {
            let command = parse_solve_cli(&args[1..])?;
            solve_all(
                &command.instances_dir,
                &command.output_dir,
                command.iterations,
                command.seed,
            )
        }
        Some("animate") => {
            let command = parse_animate_cli(&args[1..])?;
            run_animate(&command)
        }
        _ => bail!("{}", usage()),
    }
}

fn solve_all(instances_dir: &Path, output_dir: &Path, iterations: usize, seed: u64) -> Result<()> {
    fs::create_dir_all(output_dir)?;

    let mut summary = Vec::new();
    for (offset, instance_path) in instance_paths(instances_dir)?.into_iter().enumerate() {
        let instance = Instance::from_path(&instance_path)?;
        let matrix = DistanceMatrix::build(&instance);
        let solve_params = SolveParams {
            iterations,
            seed: seed + offset as u64 + instance.seed,
            record_history: false,
        };
        let outcome = solve(&instance, &matrix, &solve_params)?;
        let evaluation = evaluate_solution(&instance, &matrix, &outcome.best_solution);
        let serialized = solution_to_json(
            &instance,
            &outcome.best_solution,
            evaluation.clone(),
            iterations,
            solve_params.seed,
            outcome.initial_objective,
            outcome.operator_weights,
        );

        write_solution(
            &output_dir.join(format!("{}.solution.json", instance.name)),
            &serialized,
        )?;

        println!(
            "[rust] {}: objective={:.2} routes={} feasible={} missing_optional={}",
            serialized.instance,
            serialized.objective,
            serialized.route_count,
            serialized.feasible,
            serialized.evaluation.missing_optional_nodes.len()
        );

        summary.push(SummaryRecord {
            instance: serialized.instance,
            initial_objective: serialized.metadata.initial_objective,
            best_objective: serialized.objective,
            route_count: serialized.route_count,
            feasible: serialized.feasible,
            missing_required_count: serialized.evaluation.missing_required_nodes.len(),
            missing_optional_count: serialized.evaluation.missing_optional_nodes.len(),
        });
    }

    fs::write(
        output_dir.join("summary.json"),
        serde_json::to_string_pretty(&Summary { solutions: summary })? + "\n",
    )?;

    Ok(())
}

fn parse_solve_cli(args: &[String]) -> Result<SolveCommand> {
    let mut instances_dir = PathBuf::from("instances/li_lim_100");
    let mut output_dir = PathBuf::from("results/li_lim_100/rust");
    let mut iterations = 100_usize;
    let mut seed = 42_u64;
    let mut cursor = 0_usize;

    while cursor < args.len() {
        match args[cursor].as_str() {
            "--instances-dir" => {
                instances_dir = parse_value::<PathBuf>(args, &mut cursor, "--instances-dir")?;
            }
            "--output-dir" => {
                output_dir = parse_value::<PathBuf>(args, &mut cursor, "--output-dir")?;
            }
            "--iterations" => {
                iterations = parse_value::<usize>(args, &mut cursor, "--iterations")?;
            }
            "--seed" => {
                seed = parse_value::<u64>(args, &mut cursor, "--seed")?;
            }
            "--help" | "-h" => bail!("{}", usage()),
            flag => bail!("unknown flag: {flag}\n\n{}", usage()),
        }
        cursor += 1;
    }

    Ok(SolveCommand {
        instances_dir,
        output_dir,
        iterations,
        seed,
    })
}

fn parse_animate_cli(args: &[String]) -> Result<AnimateCommand> {
    let mut instance_path: Option<PathBuf> = None;
    let mut output_path = PathBuf::from("animation_history.json");
    let mut iterations = 2000_usize;
    let mut seed = 42_u64;
    let mut cursor = 0_usize;

    while cursor < args.len() {
        match args[cursor].as_str() {
            "--instance" => {
                instance_path = Some(parse_value::<PathBuf>(args, &mut cursor, "--instance")?);
            }
            "--output" => {
                output_path = parse_value::<PathBuf>(args, &mut cursor, "--output")?;
            }
            "--iterations" => {
                iterations = parse_value::<usize>(args, &mut cursor, "--iterations")?;
            }
            "--seed" => {
                seed = parse_value::<u64>(args, &mut cursor, "--seed")?;
            }
            "--help" | "-h" => bail!("{}", usage()),
            flag => bail!("unknown flag: {flag}\n\n{}", usage()),
        }
        cursor += 1;
    }

    let instance_path =
        instance_path.ok_or_else(|| anyhow::anyhow!("--instance is required\n\n{}", usage()))?;

    Ok(AnimateCommand {
        instance_path,
        output_path,
        iterations,
        seed,
    })
}

fn run_animate(command: &AnimateCommand) -> Result<()> {
    let instance = Instance::from_path(&command.instance_path)?;
    let matrix = DistanceMatrix::build(&instance);
    let solve_params = SolveParams {
        iterations: command.iterations,
        seed: command.seed,
        record_history: true,
    };

    eprintln!(
        "[animate] Solving {} with {} iterations...",
        instance.name, command.iterations
    );
    let outcome = solve(&instance, &matrix, &solve_params)?;
    eprintln!(
        "[animate] Done. Recorded {} snapshots.",
        outcome.history.len()
    );

    let history_output = build_history_output(&instance, &outcome, command.iterations);
    fs::write(
        &command.output_path,
        serde_json::to_string_pretty(&history_output)? + "\n",
    )?;
    eprintln!(
        "[animate] History written to {}",
        command.output_path.display()
    );

    Ok(())
}

fn build_history_output(
    instance: &Instance,
    outcome: &SolveOutcome,
    total_iterations: usize,
) -> HistoryOutput {
    let snapshots = outcome
        .history
        .iter()
        .map(|snap| SnapshotOutput {
            iteration: snap.iteration,
            temperature: snap.temperature,
            candidate_score: snap.candidate_score,
            best_score: snap.best_score,
            accepted: snap.accepted,
            best_updated: snap.best_updated,
            candidate_routes: routes_to_entries(instance, &snap.candidate_routes),
            best_routes: routes_to_entries(instance, &snap.best_routes),
        })
        .collect();

    HistoryOutput {
        instance_name: instance.name.clone(),
        initial_score: outcome.initial_objective,
        total_iterations,
        snapshots,
    }
}

fn routes_to_entries(instance: &Instance, routes: &[RouteCapture]) -> Vec<RouteHistoryEntry> {
    routes
        .iter()
        .map(|route| RouteHistoryEntry {
            depot_id: instance.depots[route.depot_idx].id.clone(),
            node_ids: route
                .stops
                .iter()
                .map(|&node_idx| instance.nodes[node_idx].id.clone())
                .collect(),
        })
        .collect()
}

fn parse_value<T>(args: &[String], cursor: &mut usize, flag: &str) -> Result<T>
where
    T: FromStr,
    <T as FromStr>::Err: std::fmt::Display,
{
    *cursor += 1;
    let Some(value) = args.get(*cursor) else {
        bail!("missing value for {flag}");
    };

    value
        .parse::<T>()
        .map_err(|error| anyhow::anyhow!("invalid value for {flag}: {error}"))
}

fn usage() -> &'static str {
    "Usage:
  cargo run --release -- solve [--instances-dir <path>] [--output-dir <path>] [--iterations <n>] [--seed <n>]
  cargo run --release -- animate --instance <path> [--output <path>] [--iterations <n>] [--seed <n>]"
}
