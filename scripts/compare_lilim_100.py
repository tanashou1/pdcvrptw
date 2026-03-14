from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import load_json, save_json, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Li-Lim reference, PyVRP, and Rust results.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances/li_lim_100"))
    parser.add_argument("--reference-dir", type=Path, default=Path("results/li_lim_100/reference"))
    parser.add_argument("--pyvrp-dir", type=Path, default=Path("results/li_lim_100/pyvrp"))
    parser.add_argument("--rust-dir", type=Path, default=Path("results/li_lim_100/rust"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/li_lim_100/comparison"))
    return parser.parse_args()


def load_solution(solution_dir: Path, instance_name: str) -> dict[str, Any]:
    return load_json(solution_dir / f"{instance_name}.solution.json")


def compare_status(
    reference_routes: int,
    solver_routes: int,
    reference_distance: float,
    solver_distance: float,
    solver_feasible: bool,
) -> str:
    if not solver_feasible:
        return "infeasible"

    if solver_routes < reference_routes:
        return "better_vehicles"

    if solver_routes > reference_routes:
        return "worse_vehicles"

    if solver_distance < reference_distance - 1e-9:
        return "better_distance"

    if abs(solver_distance - reference_distance) <= 1e-9:
        return "match"

    return "worse_distance"


def distance_gap_pct(reference_distance: float, solver_distance: float) -> float:
    if reference_distance == 0:
        return 0.0

    return ((solver_distance - reference_distance) / reference_distance) * 100.0


def average_or_none(values: list[float]) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def solver_aggregate(records: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    feasible_records = [record for record in records if record[f"{prefix}_feasible"]]
    same_vehicle_records = [
        record for record in feasible_records if record[f"{prefix}_vehicle_gap"] == 0
    ]

    aggregate = {
        "strict_feasible_count": len(feasible_records),
        "infeasible_count": len(records) - len(feasible_records),
        "same_vehicle_count": len(same_vehicle_records),
        "better_vehicle_count": sum(
            1 for record in feasible_records if record[f"{prefix}_vehicle_gap"] < 0
        ),
        "worse_vehicle_count": sum(
            1 for record in feasible_records if record[f"{prefix}_vehicle_gap"] > 0
        ),
        "match_count": sum(
            1 for record in feasible_records if record[f"{prefix}_status"] == "match"
        ),
        "average_distance_gap_pct": average_or_none(
            [record[f"{prefix}_distance_gap_pct"] for record in feasible_records]
        ),
        "same_vehicle_average_gap_pct": average_or_none(
            [record[f"{prefix}_distance_gap_pct"] for record in same_vehicle_records]
        ),
    }

    reported_key = f"{prefix}_reported_feasible"
    if any(record.get(reported_key) is not None for record in records):
        aggregate["reported_feasible_count"] = sum(
            1 for record in records if record.get(reported_key) is True
        )

    return aggregate


def format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value:.2f}%"


def feasible_label(value: bool) -> str:
    return "yes" if value else "no"


def render_markdown(records: list[dict[str, Any]], aggregate: dict[str, Any]) -> str:
    lines = [
        "# Li-Lim 100-case comparison",
        "",
        "> PyVRP uses a relaxed formulation because its public API does not expose Li-Lim pickup-delivery sibling constraints. "
        "The table below reports strict feasibility after re-evaluating the generated route sequence with the benchmark evaluator.",
        "",
        "| Instance | Ref veh | Ref dist | PyVRP veh | PyVRP dist | PyVRP gap % | PyVRP feasible | PyVRP status | Rust veh | Rust dist | Rust gap % | Rust feasible | Rust status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]

    for record in records:
        lines.append(
            "| {instance} | {reference_vehicles} | {reference_distance:.2f} | "
            "{pyvrp_vehicles} | {pyvrp_distance:.2f} | {pyvrp_distance_gap_pct:.2f} | "
            "{pyvrp_feasible_label} | {pyvrp_status} | "
            "{rust_vehicles} | {rust_distance:.2f} | {rust_distance_gap_pct:.2f} | "
            "{rust_feasible_label} | {rust_status} |".format(**record)
        )

    pyvrp = aggregate["pyvrp"]
    rust = aggregate["rust"]
    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- Instances compared: {aggregate['instance_count']}",
            "",
            "### Rust ALNS",
            "",
            f"- Strict feasible instances: {rust['strict_feasible_count']} / {aggregate['instance_count']}",
            f"- Exact matches to reference: {rust['match_count']}",
            f"- Same vehicle count as reference: {rust['same_vehicle_count']}",
            f"- Better vehicle count than reference: {rust['better_vehicle_count']}",
            f"- Worse vehicle count than reference: {rust['worse_vehicle_count']}",
            f"- Average distance gap on strict-feasible cases: {format_pct(rust['average_distance_gap_pct'])}",
            f"- Average distance gap on same-vehicle strict-feasible cases: {format_pct(rust['same_vehicle_average_gap_pct'])}",
            "",
            "### PyVRP relaxed model",
            "",
            f"- Reported feasible instances in the relaxed model: {pyvrp.get('reported_feasible_count', 0)} / {aggregate['instance_count']}",
            f"- Strict feasible instances under Li-Lim evaluation: {pyvrp['strict_feasible_count']} / {aggregate['instance_count']}",
            f"- Exact matches to reference: {pyvrp['match_count']}",
            f"- Same vehicle count as reference on strict-feasible cases: {pyvrp['same_vehicle_count']}",
            f"- Better vehicle count than reference on strict-feasible cases: {pyvrp['better_vehicle_count']}",
            f"- Worse vehicle count than reference on strict-feasible cases: {pyvrp['worse_vehicle_count']}",
            f"- Average distance gap on strict-feasible cases: {format_pct(pyvrp['average_distance_gap_pct'])}",
            f"- Average distance gap on same-vehicle strict-feasible cases: {format_pct(pyvrp['same_vehicle_average_gap_pct'])}",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for instance_path in sorted(args.instances_dir.glob("instance_*.json")):
        instance = load_json(instance_path)
        instance_name = instance["name"]
        reference_solution = load_solution(args.reference_dir, instance_name)
        pyvrp_solution = load_solution(args.pyvrp_dir, instance_name)
        rust_solution = load_solution(args.rust_dir, instance_name)

        reference_eval = reference_solution["evaluation"]
        pyvrp_eval = pyvrp_solution["evaluation"]
        rust_eval = rust_solution["evaluation"]

        reference_distance = float(reference_eval["comparison_distance"])
        pyvrp_distance = float(pyvrp_eval["comparison_distance"])
        rust_distance = float(rust_eval["comparison_distance"])
        reference_routes = int(reference_eval["route_count"])
        pyvrp_routes = int(pyvrp_eval["route_count"])
        rust_routes = int(rust_eval["route_count"])
        pyvrp_feasible = bool(pyvrp_eval["feasible"])
        rust_feasible = bool(rust_eval["feasible"])

        records.append(
            {
                "instance": instance_name,
                "reference_vehicles": reference_routes,
                "reference_feasible": bool(reference_eval["feasible"]),
                "reference_distance": reference_distance,
                "pyvrp_vehicles": pyvrp_routes,
                "pyvrp_vehicle_gap": pyvrp_routes - reference_routes,
                "pyvrp_distance": pyvrp_distance,
                "pyvrp_distance_gap": pyvrp_distance - reference_distance,
                "pyvrp_distance_gap_pct": distance_gap_pct(reference_distance, pyvrp_distance),
                "pyvrp_feasible": pyvrp_feasible,
                "pyvrp_feasible_label": feasible_label(pyvrp_feasible),
                "pyvrp_reported_feasible": pyvrp_solution.get("reported_feasible"),
                "pyvrp_runtime_seconds": round(float(pyvrp_solution.get("runtime_seconds", 0.0)), 3),
                "pyvrp_status": compare_status(
                    reference_routes,
                    pyvrp_routes,
                    reference_distance,
                    pyvrp_distance,
                    pyvrp_feasible,
                ),
                "rust_vehicles": rust_routes,
                "rust_vehicle_gap": rust_routes - reference_routes,
                "vehicle_gap": rust_routes - reference_routes,
                "rust_distance": rust_distance,
                "distance_gap": rust_distance - reference_distance,
                "rust_distance_gap_pct": distance_gap_pct(reference_distance, rust_distance),
                "rust_feasible": rust_feasible,
                "rust_feasible_label": feasible_label(rust_feasible),
                "rust_status": compare_status(
                    reference_routes,
                    rust_routes,
                    reference_distance,
                    rust_distance,
                    rust_feasible,
                ),
            }
        )

    aggregate = {
        "instance_count": len(records),
        "pyvrp": solver_aggregate(records, "pyvrp"),
        "rust": solver_aggregate(records, "rust"),
    }

    save_json(
        {
            "records": records,
            "aggregate": aggregate,
            "notes": [
                "PyVRP uses a relaxed model and is re-evaluated with the strict Li-Lim semantics.",
            ],
        },
        args.output_dir / "summary.json",
    )
    write_csv(
        rows=records,
        fieldnames=[
            "instance",
            "reference_vehicles",
            "reference_feasible",
            "reference_distance",
            "pyvrp_vehicles",
            "pyvrp_vehicle_gap",
            "pyvrp_distance",
            "pyvrp_distance_gap",
            "pyvrp_distance_gap_pct",
            "pyvrp_feasible",
            "pyvrp_feasible_label",
            "pyvrp_reported_feasible",
            "pyvrp_runtime_seconds",
            "pyvrp_status",
            "rust_vehicles",
            "rust_vehicle_gap",
            "vehicle_gap",
            "rust_distance",
            "distance_gap",
            "rust_distance_gap_pct",
            "rust_feasible",
            "rust_feasible_label",
            "rust_status",
        ],
        path=args.output_dir / "summary.csv",
    )
    markdown = render_markdown(records, aggregate)
    (args.output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
