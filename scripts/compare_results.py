from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import load_json, save_json, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare PyVRP and Rust solutions.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances"))
    parser.add_argument("--pyvrp-dir", type=Path, default=Path("results/pyvrp"))
    parser.add_argument("--rust-dir", type=Path, default=Path("results/rust"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/comparison"))
    return parser.parse_args()


def load_solution(solution_dir: Path, instance_name: str) -> dict[str, Any]:
    return load_json(solution_dir / f"{instance_name}.solution.json")


def gap_percent(reference: int, candidate: int) -> float:
    if reference == 0:
        return 0.0

    return ((candidate - reference) / reference) * 100.0


def render_markdown(records: list[dict[str, Any]], aggregate: dict[str, Any]) -> str:
    lines = [
        "# Comparison summary",
        "",
        "| Instance | PyVRP | Rust | Gap % | PyVRP routes | Rust routes |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for record in records:
        lines.append(
            "| {instance} | {pyvrp_objective} | {rust_objective} | {gap_pct:.2f} | "
            "{pyvrp_routes} | {rust_routes} |".format(**record)
        )

    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- PyVRP feasible instances: {aggregate['pyvrp_feasible_count']} / {aggregate['instance_count']}",
            f"- Rust feasible instances: {aggregate['rust_feasible_count']} / {aggregate['instance_count']}",
            f"- Average Rust gap vs PyVRP: {aggregate['average_gap_pct']:.2f}%",
            f"- Best Rust gap vs PyVRP: {aggregate['best_gap_pct']:.2f}%",
            f"- Worst Rust gap vs PyVRP: {aggregate['worst_gap_pct']:.2f}%",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for instance_path in sorted(args.instances_dir.glob("instance_*.json")):
        instance_name = instance_path.stem
        pyvrp_solution = load_solution(args.pyvrp_dir, instance_name)
        rust_solution = load_solution(args.rust_dir, instance_name)

        pyvrp_eval = pyvrp_solution["evaluation"]
        rust_eval = rust_solution["evaluation"]
        rust_gap = gap_percent(int(pyvrp_eval["objective"]), int(rust_eval["objective"]))

        records.append(
            {
                "instance": instance_name,
                "pyvrp_objective": int(pyvrp_eval["objective"]),
                "rust_objective": int(rust_eval["objective"]),
                "gap_pct": rust_gap,
                "pyvrp_routes": int(pyvrp_eval["route_count"]),
                "rust_routes": int(rust_eval["route_count"]),
                "pyvrp_feasible": bool(pyvrp_eval["feasible"]),
                "rust_feasible": bool(rust_eval["feasible"]),
            }
        )

    average_gap = sum(record["gap_pct"] for record in records) / len(records)
    aggregate = {
        "instance_count": len(records),
        "pyvrp_feasible_count": sum(1 for record in records if record["pyvrp_feasible"]),
        "rust_feasible_count": sum(1 for record in records if record["rust_feasible"]),
        "average_gap_pct": average_gap,
        "best_gap_pct": min(record["gap_pct"] for record in records),
        "worst_gap_pct": max(record["gap_pct"] for record in records),
    }

    save_json({"records": records, "aggregate": aggregate}, args.output_dir / "summary.json")
    write_csv(
        rows=records,
        fieldnames=[
            "instance",
            "pyvrp_objective",
            "rust_objective",
            "gap_pct",
            "pyvrp_routes",
            "rust_routes",
            "pyvrp_feasible",
            "rust_feasible",
        ],
        path=args.output_dir / "summary.csv",
    )
    markdown = render_markdown(records, aggregate)
    (args.output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
