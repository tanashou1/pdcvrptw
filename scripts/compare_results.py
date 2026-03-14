from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import load_json, save_json, write_csv

COMPARISON_TOLERANCE = 0.005


SOLVERS = [
    {
        "key": "ortools",
        "short_label": "OR-Tools",
        "section_label": "OR-Tools strict model",
        "directory_argument": "ortools_dir",
        "reported_feasible_label": "Reported feasible instances in the OR-Tools model",
    },
    {
        "key": "rust",
        "short_label": "Rust",
        "section_label": "Rust ALNS",
        "directory_argument": "rust_dir",
        "reported_feasible_label": None,
    },
]

PAIRWISE_COMPARISON = {
    "left_key": "ortools",
    "left_label": "OR-Tools",
    "right_key": "rust",
    "right_label": "Rust",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Li-Lim reference, OR-Tools, and Rust results.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances/li_lim_100"))
    parser.add_argument("--reference-dir", type=Path, default=Path("results/li_lim_100/reference"))
    parser.add_argument("--ortools-dir", type=Path, default=Path("results/li_lim_100/ortools"))
    parser.add_argument("--rust-dir", type=Path, default=Path("results/li_lim_100/rust"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/li_lim_100/comparison"))
    return parser.parse_args()


def load_solution(solution_dir: Path, instance_name: str) -> dict[str, Any]:
    path = solution_dir / f"{instance_name}.solution.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing solution file for {instance_name}: {path}")

    return load_json(path)


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

    if abs(solver_distance - reference_distance) <= COMPARISON_TOLERANCE:
        return "match"

    if solver_distance < reference_distance:
        return "better_distance"

    return "worse_distance"


def distance_gap_pct(reference_distance: float, solver_distance: float) -> float:
    if reference_distance == 0:
        return 0.0

    return ((solver_distance - reference_distance) / reference_distance) * 100.0


def average_or_none(values: list[float]) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def pairwise_status(
    left_routes: int,
    left_distance: float,
    left_feasible: bool,
    right_routes: int,
    right_distance: float,
    right_feasible: bool,
) -> str:
    if left_feasible and not right_feasible:
        return "left_only_feasible"

    if not left_feasible and right_feasible:
        return "right_only_feasible"

    if not left_feasible and not right_feasible:
        return "both_infeasible"

    return compare_status(
        right_routes,
        left_routes,
        right_distance,
        left_distance,
        left_feasible,
    )


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


def pairwise_aggregate(
    records: list[dict[str, Any]],
    left_prefix: str,
    right_prefix: str,
) -> dict[str, Any]:
    comparable_records = [
        record
        for record in records
        if record[f"{left_prefix}_feasible"] and record[f"{right_prefix}_feasible"]
    ]
    same_vehicle_records = [
        record for record in comparable_records if record[f"{left_prefix}_vs_{right_prefix}_vehicle_gap"] == 0
    ]

    return {
        "comparable_count": len(comparable_records),
        "same_vehicle_count": len(same_vehicle_records),
        "match_count": sum(
            1
            for record in comparable_records
            if record[f"{left_prefix}_vs_{right_prefix}_status"] == "match"
        ),
        "left_better_vehicle_count": sum(
            1
            for record in comparable_records
            if record[f"{left_prefix}_vs_{right_prefix}_vehicle_gap"] < 0
        ),
        "right_better_vehicle_count": sum(
            1
            for record in comparable_records
            if record[f"{left_prefix}_vs_{right_prefix}_vehicle_gap"] > 0
        ),
        "left_better_distance_count": sum(
            1
            for record in same_vehicle_records
            if record[f"{left_prefix}_vs_{right_prefix}_status"] == "better_distance"
        ),
        "right_better_distance_count": sum(
            1
            for record in same_vehicle_records
            if record[f"{left_prefix}_vs_{right_prefix}_status"] == "worse_distance"
        ),
        "average_distance_gap_pct": average_or_none(
            [record[f"{left_prefix}_vs_{right_prefix}_distance_gap_pct"] for record in comparable_records]
        ),
        "same_vehicle_average_gap_pct": average_or_none(
            [record[f"{left_prefix}_vs_{right_prefix}_distance_gap_pct"] for record in same_vehicle_records]
        ),
    }


def format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value:.2f}%"


def feasible_label(value: bool) -> str:
    return "yes" if value else "no"


def render_row(record: dict[str, Any]) -> str:
    cells = [
        record["instance"],
        str(record["reference_vehicles"]),
        f"{record['reference_distance']:.2f}",
    ]

    for solver in SOLVERS:
        prefix = solver["key"]
        cells.extend(
            [
                str(record[f"{prefix}_vehicles"]),
                f"{record[f'{prefix}_distance']:.2f}",
                f"{record[f'{prefix}_distance_gap_pct']:.2f}",
                record[f"{prefix}_status"],
            ]
        )

    cells.extend(
        [
            f"{record['ortools_vs_rust_vehicle_gap']:+d}",
            f"{record['ortools_vs_rust_distance_gap_pct']:+.2f}",
            record["ortools_vs_rust_status"],
        ]
    )

    return "| " + " | ".join(cells) + " |"


def render_solver_section(
    aggregate: dict[str, Any],
    solver: dict[str, str],
    instance_count: int,
) -> list[str]:
    prefix = solver["key"]
    solver_aggregate_data = aggregate[prefix]
    lines = [f"### {solver['section_label']}", ""]

    reported_label = solver["reported_feasible_label"]
    if reported_label is not None:
        lines.append(
            f"- {reported_label}: {solver_aggregate_data.get('reported_feasible_count', 0)} / {instance_count}"
        )

    lines.extend(
        [
            f"- Strict feasible instances: {solver_aggregate_data['strict_feasible_count']} / {instance_count}",
            f"- Exact matches to reference: {solver_aggregate_data['match_count']}",
            f"- Same vehicle count as reference on strict-feasible cases: {solver_aggregate_data['same_vehicle_count']}",
            f"- Better vehicle count than reference on strict-feasible cases: {solver_aggregate_data['better_vehicle_count']}",
            f"- Worse vehicle count than reference on strict-feasible cases: {solver_aggregate_data['worse_vehicle_count']}",
            f"- Average distance gap on strict-feasible cases: {format_pct(solver_aggregate_data['average_distance_gap_pct'])}",
            f"- Average distance gap on same-vehicle strict-feasible cases: {format_pct(solver_aggregate_data['same_vehicle_average_gap_pct'])}",
        ]
    )
    return lines


def render_pairwise_section(
    aggregate: dict[str, Any],
    comparison: dict[str, str],
    instance_count: int,
) -> list[str]:
    left_prefix = comparison["left_key"]
    right_prefix = comparison["right_key"]
    left_label = comparison["left_label"]
    right_label = comparison["right_label"]
    pairwise = aggregate[f"{left_prefix}_vs_{right_prefix}"]

    return [
        f"### {left_label} vs {right_label}",
        "",
        f"- Cases where both solvers are strict feasible: {pairwise['comparable_count']} / {instance_count}",
        f"- Exact matches between {left_label} and {right_label}: {pairwise['match_count']}",
        f"- Same vehicle count between {left_label} and {right_label}: {pairwise['same_vehicle_count']}",
        f"- {left_label} better vehicle count than {right_label}: {pairwise['left_better_vehicle_count']}",
        f"- {right_label} better vehicle count than {left_label}: {pairwise['right_better_vehicle_count']}",
        f"- {left_label} better distance than {right_label} on same-vehicle cases: {pairwise['left_better_distance_count']}",
        f"- {right_label} better distance than {left_label} on same-vehicle cases: {pairwise['right_better_distance_count']}",
        f"- Average {left_label} distance gap vs {right_label}: {format_pct(pairwise['average_distance_gap_pct'])}",
        f"- Average {left_label} distance gap vs {right_label} on same-vehicle cases: {format_pct(pairwise['same_vehicle_average_gap_pct'])}",
    ]


def render_markdown(records: list[dict[str, Any]], aggregate: dict[str, Any]) -> str:
    lines = [
        "# Li-Lim 100-case comparison",
        "",
        "> Official result comparison now reports only the strict solvers: reference, OR-Tools, and Rust.",
        "> The `OR-Tools vs Rust` columns measure OR-Tools relative to Rust, so positive gaps mean OR-Tools is worse than Rust.",
        "",
        "| Instance | Ref veh | Ref dist | OR-Tools veh | OR-Tools dist | OR-Tools gap % | OR-Tools status | Rust veh | Rust dist | Rust gap % | Rust status | O-R veh gap | O-R gap % | O-R status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    lines.extend(render_row(record) for record in records)
    lines.extend(["", "## Aggregate", "", f"- Instances compared: {aggregate['instance_count']}", ""])

    for solver in SOLVERS:
        lines.extend(render_solver_section(aggregate, solver, aggregate["instance_count"]))
        lines.append("")

    lines.extend(render_pairwise_section(aggregate, PAIRWISE_COMPARISON, aggregate["instance_count"]))
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for instance_path in sorted(args.instances_dir.glob("instance_*.json")):
        instance = load_json(instance_path)
        instance_name = instance["name"]
        reference_solution = load_solution(args.reference_dir, instance_name)
        reference_eval = reference_solution["evaluation"]
        reference_distance = float(reference_eval["comparison_distance"])
        reference_routes = int(reference_eval["route_count"])

        record: dict[str, Any] = {
            "instance": instance_name,
            "reference_vehicles": reference_routes,
            "reference_feasible": bool(reference_eval["feasible"]),
            "reference_distance": reference_distance,
        }

        for solver in SOLVERS:
            prefix = solver["key"]
            solution = load_solution(getattr(args, solver["directory_argument"]), instance_name)
            evaluation = solution["evaluation"]
            solver_distance = float(evaluation["comparison_distance"])
            solver_routes = int(evaluation["route_count"])
            solver_feasible = bool(evaluation["feasible"])

            record.update(
                {
                    f"{prefix}_vehicles": solver_routes,
                    f"{prefix}_vehicle_gap": solver_routes - reference_routes,
                    f"{prefix}_distance": solver_distance,
                    f"{prefix}_distance_gap": solver_distance - reference_distance,
                    f"{prefix}_distance_gap_pct": distance_gap_pct(reference_distance, solver_distance),
                    f"{prefix}_feasible": solver_feasible,
                    f"{prefix}_reported_feasible": solution.get("reported_feasible"),
                    f"{prefix}_runtime_seconds": round(float(solution.get("runtime_seconds", 0.0)), 3),
                    f"{prefix}_status": compare_status(
                        reference_routes,
                        solver_routes,
                        reference_distance,
                        solver_distance,
                        solver_feasible,
                    ),
                }
            )

        record.update(
            {
                "ortools_vs_rust_vehicle_gap": record["ortools_vehicles"] - record["rust_vehicles"],
                "ortools_vs_rust_distance_gap": record["ortools_distance"] - record["rust_distance"],
                "ortools_vs_rust_distance_gap_pct": distance_gap_pct(
                    record["rust_distance"],
                    record["ortools_distance"],
                ),
                "ortools_vs_rust_status": pairwise_status(
                    record["ortools_vehicles"],
                    record["ortools_distance"],
                    record["ortools_feasible"],
                    record["rust_vehicles"],
                    record["rust_distance"],
                    record["rust_feasible"],
                ),
            }
        )

        records.append(record)

    aggregate = {"instance_count": len(records)}
    for solver in SOLVERS:
        aggregate[solver["key"]] = solver_aggregate(records, solver["key"])
    aggregate["ortools_vs_rust"] = pairwise_aggregate(records, "ortools", "rust")

    save_json(
        {
            "records": records,
            "aggregate": aggregate,
            "notes": [
                "Official comparison outputs exclude PyVRP and focus on the strict OR-Tools and Rust solvers.",
                "OR-Tools vs Rust gaps are expressed relative to Rust.",
            ],
        },
        args.output_dir / "summary.json",
    )

    fieldnames = ["instance", "reference_vehicles", "reference_feasible", "reference_distance"]
    for solver in SOLVERS:
        prefix = solver["key"]
        fieldnames.extend(
            [
                f"{prefix}_vehicles",
                f"{prefix}_vehicle_gap",
                f"{prefix}_distance",
                f"{prefix}_distance_gap",
                f"{prefix}_distance_gap_pct",
                f"{prefix}_feasible",
                f"{prefix}_reported_feasible",
                f"{prefix}_runtime_seconds",
                f"{prefix}_status",
            ]
        )
    fieldnames.extend(
        [
            "ortools_vs_rust_vehicle_gap",
            "ortools_vs_rust_distance_gap",
            "ortools_vs_rust_distance_gap_pct",
            "ortools_vs_rust_status",
        ]
    )

    write_csv(rows=records, fieldnames=fieldnames, path=args.output_dir / "summary.csv")
    markdown = render_markdown(records, aggregate)
    (args.output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
