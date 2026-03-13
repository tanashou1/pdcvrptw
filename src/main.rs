use std::fs;
use std::path::{Path, PathBuf};
use std::{env, str::FromStr};

use anyhow::{bail, Result};
use serde::Serialize;

use pdcvrptw::alns::{solve, SolveParams};
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
    initial_objective: i64,
    best_objective: i64,
    route_count: usize,
    feasible: bool,
}

#[derive(Debug, Serialize)]
struct Summary {
    solutions: Vec<SummaryRecord>,
}

fn main() -> Result<()> {
    let command = parse_cli()?;
    solve_all(
        &command.instances_dir,
        &command.output_dir,
        command.iterations,
        command.seed,
    )
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
            "[rust] {}: objective={} routes={} feasible={}",
            serialized.instance, serialized.objective, serialized.route_count, serialized.feasible
        );

        summary.push(SummaryRecord {
            instance: serialized.instance,
            initial_objective: serialized.metadata.initial_objective,
            best_objective: serialized.objective,
            route_count: serialized.route_count,
            feasible: serialized.feasible,
        });
    }

    fs::write(
        output_dir.join("summary.json"),
        serde_json::to_string_pretty(&Summary { solutions: summary })? + "\n",
    )?;

    Ok(())
}

fn parse_cli() -> Result<SolveCommand> {
    let args = env::args().skip(1).collect::<Vec<_>>();

    if args.first().map(String::as_str) != Some("solve") {
        bail!("{}", usage());
    }

    let mut instances_dir = PathBuf::from("instances");
    let mut output_dir = PathBuf::from("results/rust");
    let mut iterations = 800_usize;
    let mut seed = 42_u64;
    let mut cursor = 1_usize;

    while cursor < args.len() {
        match args[cursor].as_str() {
            "--instances-dir" => {
                instances_dir = parse_value::<PathBuf>(&args, &mut cursor, "--instances-dir")?;
            }
            "--output-dir" => {
                output_dir = parse_value::<PathBuf>(&args, &mut cursor, "--output-dir")?;
            }
            "--iterations" => {
                iterations = parse_value::<usize>(&args, &mut cursor, "--iterations")?;
            }
            "--seed" => {
                seed = parse_value::<u64>(&args, &mut cursor, "--seed")?;
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
  cargo run --release -- solve [--instances-dir <path>] [--output-dir <path>] [--iterations <n>] [--seed <n>]"
}
