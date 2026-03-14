from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import load_json, save_json

ROUTE_COLOURS = list(plt.get_cmap("tab20").colors)
SOLVER_COLOURS = {
    "reference": "#4c78a8",
    "ortools": "#54a24b",
    "rust": "#e45756",
}


PLOTS = [
    ("Reference", None, "reference"),
    ("OR-Tools strict", "ortools_status", "ortools"),
    ("Rust ALNS", "rust_status", "rust"),
]

SCORE_BAR_SERIES = [
    ("Reference", "reference"),
    ("OR-Tools strict", "ortools"),
    ("Rust ALNS", "rust"),
]

DISTANCE_GAP_SERIES = [
    ("OR-Tools strict", "ortools"),
    ("Rust ALNS", "rust"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize Li-Lim reference, OR-Tools, and Rust visit orders.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances/li_lim_100"))
    parser.add_argument("--reference-dir", type=Path, default=Path("results/li_lim_100/reference"))
    parser.add_argument("--ortools-dir", type=Path, default=Path("results/li_lim_100/ortools"))
    parser.add_argument("--rust-dir", type=Path, default=Path("results/li_lim_100/rust"))
    parser.add_argument(
        "--comparison-summary",
        type=Path,
        default=Path("results/li_lim_100/comparison/summary.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/li_lim_100/visualization"))
    return parser.parse_args()


def load_solution(solution_dir: Path, instance_name: str) -> dict[str, Any]:
    return load_json(solution_dir / f"{instance_name}.solution.json")


def build_lookup(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def route_polyline(instance: dict[str, Any], route: dict[str, Any]) -> tuple[list[float], list[float]]:
    depots = build_lookup(instance["depots"])
    nodes = build_lookup(instance["nodes"])
    depot = depots[route["depot_id"]]

    x_values = [float(depot["x"])]
    y_values = [float(depot["y"])]
    for node_id in route["node_ids"]:
        node = nodes[node_id]
        x_values.append(float(node["x"]))
        y_values.append(float(node["y"]))

    x_values.append(float(depot["x"]))
    y_values.append(float(depot["y"]))
    return x_values, y_values


def axis_limits(instance: dict[str, Any]) -> tuple[float, float, float, float]:
    xs = [float(location["x"]) for location in instance["location_catalog"]]
    ys = [float(location["y"]) for location in instance["location_catalog"]]
    xs.extend(float(depot["x"]) for depot in instance["depots"])
    ys.extend(float(depot["y"]) for depot in instance["depots"])
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    margin = max(4.0, 0.08 * max(span_x, span_y, 1.0))
    return min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin


def plot_solution(
    ax: plt.Axes,
    instance: dict[str, Any],
    solution: dict[str, Any],
    solver_label: str,
    status_label: str,
) -> None:
    nodes = build_lookup(instance["nodes"])
    pickups = [node for node in instance["nodes"] if node["kind"] == "pickup"]
    deliveries = [node for node in instance["nodes"] if node["kind"] == "delivery"]

    ax.scatter(
        [node["x"] for node in pickups],
        [node["y"] for node in pickups],
        marker="o",
        s=18,
        linewidths=0.5,
        facecolors="white",
        edgecolors="#c0c0c0",
        zorder=1,
    )
    ax.scatter(
        [node["x"] for node in deliveries],
        [node["y"] for node in deliveries],
        marker="s",
        s=18,
        linewidths=0.5,
        facecolors="white",
        edgecolors="#c0c0c0",
        zorder=1,
    )

    for route_index, route in enumerate(solution["routes"]):
        colour = ROUTE_COLOURS[route_index % len(ROUTE_COLOURS)]
        x_values, y_values = route_polyline(instance, route)
        ax.plot(x_values, y_values, color=colour, linewidth=1.3, alpha=0.92, zorder=2)

        route_nodes = [nodes[node_id] for node_id in route["node_ids"]]
        pickup_nodes = [node for node in route_nodes if node["kind"] == "pickup"]
        delivery_nodes = [node for node in route_nodes if node["kind"] == "delivery"]
        if pickup_nodes:
            ax.scatter(
                [node["x"] for node in pickup_nodes],
                [node["y"] for node in pickup_nodes],
                marker="o",
                s=26,
                linewidths=0.9,
                facecolors="white",
                edgecolors=[colour],
                zorder=3,
            )
        if delivery_nodes:
            ax.scatter(
                [node["x"] for node in delivery_nodes],
                [node["y"] for node in delivery_nodes],
                marker="s",
                s=26,
                linewidths=0.9,
                facecolors="white",
                edgecolors=[colour],
                zorder=3,
            )

        x_offset = 0.65 if route_index % 2 == 0 else -0.65
        y_offset = 0.65 if route_index % 3 == 0 else -0.65
        for stop_index, node in enumerate(route_nodes, start=1):
            ax.text(
                float(node["x"]) + x_offset,
                float(node["y"]) + y_offset,
                str(stop_index),
                fontsize=5.5,
                color=colour,
                ha="center",
                va="center",
                bbox={
                    "boxstyle": "round,pad=0.14",
                    "facecolor": "white",
                    "edgecolor": colour,
                    "linewidth": 0.6,
                    "alpha": 0.9,
                },
                zorder=4,
            )

    ax.scatter(
        [depot["x"] for depot in instance["depots"]],
        [depot["y"] for depot in instance["depots"]],
        marker="*",
        s=150,
        linewidths=0.8,
        facecolors="#f4d35e",
        edgecolors="#333333",
        zorder=5,
    )

    for depot in instance["depots"]:
        ax.annotate(
            depot["id"],
            (depot["x"], depot["y"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=7,
            color="#333333",
        )

    x_min, x_max, y_min, y_max = axis_limits(instance)
    evaluation = solution["evaluation"]
    ax.set_title(
        f"{solver_label}\nveh={evaluation['route_count']} dist={evaluation['comparison_distance']:.2f} "
        f"feasible={evaluation['feasible']} status={status_label}",
        fontsize=9,
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)


def add_route_legend(fig: plt.Figure) -> None:
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="*",
            linestyle="None",
            markerfacecolor="#f4d35e",
            markeredgecolor="#333333",
            markersize=11,
            label="Depot",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="white",
            markeredgecolor="#666666",
            markersize=7,
            label="Pickup node",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="None",
            markerfacecolor="white",
            markeredgecolor="#666666",
            markersize=7,
            label="Delivery node",
        ),
        Line2D([0], [0], color=ROUTE_COLOURS[0], linewidth=2, label="Route path"),
        Line2D(
            [0],
            [0],
            marker="$1$",
            linestyle="None",
            color="#555555",
            markersize=9,
            label="Visit order in route",
        ),
    ]
    fig.legend(handles=legend_handles, loc="upper center", ncol=5, frameon=False)


def style_infeasible_bars(
    bars: Any,
    records: list[dict[str, Any]],
    feasible_key: str,
) -> None:
    for bar, record in zip(bars, records, strict=True):
        if not record[feasible_key]:
            bar.set_hatch("//")
            bar.set_alpha(0.45)
            bar.set_edgecolor("#7f0000")
            bar.set_linewidth(0.8)


def render_score_comparison(
    records: list[dict[str, Any]],
    output_path: Path,
) -> str:
    instance_names = [record["instance"] for record in records]
    indices = list(range(len(records)))

    figure, (vehicles_ax, gap_ax) = plt.subplots(
        2,
        1,
        figsize=(24, 10),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.0, 1.1]},
    )

    vehicles_width = 0.18
    for series_index, (label, prefix) in enumerate(SCORE_BAR_SERIES):
        offset = (series_index - (len(SCORE_BAR_SERIES) - 1) / 2) * vehicles_width
        positions = [index + offset for index in indices]
        values = [
            record["reference_vehicles"]
            if prefix == "reference"
            else record[f"{prefix}_vehicles"]
            for record in records
        ]
        bars = vehicles_ax.bar(
            positions,
            values,
            width=vehicles_width,
            label=label,
            color=SOLVER_COLOURS[prefix],
            edgecolor="#333333",
            linewidth=0.4,
        )
        if prefix != "reference":
            style_infeasible_bars(bars, records, f"{prefix}_feasible")

    gap_width = 0.24
    for series_index, (label, prefix) in enumerate(DISTANCE_GAP_SERIES):
        offset = (series_index - (len(DISTANCE_GAP_SERIES) - 1) / 2) * gap_width
        positions = [index + offset for index in indices]
        values = [
            record[f"{prefix}_distance_gap_pct"] if record[f"{prefix}_feasible"] else 0.0
            for record in records
        ]
        bars = gap_ax.bar(
            positions,
            values,
            width=gap_width,
            label=label,
            color=SOLVER_COLOURS[prefix],
            edgecolor="#333333",
            linewidth=0.4,
        )
        for bar, record, position in zip(bars, records, positions, strict=True):
            if not record[f"{prefix}_feasible"]:
                bar.set_alpha(0.0)
                gap_ax.scatter(position, 0.0, marker="x", color=SOLVER_COLOURS[prefix], s=20, zorder=3)

    vehicles_ax.set_ylabel("Vehicle count")
    vehicles_ax.set_title("Li-Lim benchmark score comparison", fontsize=13)
    vehicles_ax.grid(axis="y", linestyle="--", alpha=0.3)

    gap_ax.axhline(0.0, color="#666666", linestyle="--", linewidth=1.0)
    gap_ax.set_ylabel("Distance gap vs ref (%)")
    gap_ax.set_xlabel("Instance")
    gap_ax.grid(axis="y", linestyle="--", alpha=0.3)
    gap_ax.set_xticks(indices)
    gap_ax.set_xticklabels(instance_names, rotation=90, fontsize=8)
    gap_ax.set_title(
        "Distance gap is shown only for strict-feasible solutions; route-count differences are shown above.",
        fontsize=10,
    )

    legend_handles = [
        Patch(facecolor=SOLVER_COLOURS[prefix], edgecolor="#333333", label=label)
        for label, prefix in SCORE_BAR_SERIES
    ]
    legend_handles.append(
        Patch(
            facecolor="white",
            edgecolor="#7f0000",
            hatch="//",
            label="Strict infeasible",
        )
    )
    figure.legend(handles=legend_handles, loc="upper center", ncol=5, frameon=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return str(output_path)


def render_instance_figures(
    instances: list[dict[str, Any]],
    reference_solutions: dict[str, dict[str, Any]],
    ortools_solutions: dict[str, dict[str, Any]],
    rust_solutions: dict[str, dict[str, Any]],
    comparison_records: dict[str, dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[dict[str, str]] = []

    solver_maps = {
        "reference": reference_solutions,
        "ortools": ortools_solutions,
        "rust": rust_solutions,
    }

    for instance in instances:
        instance_name = instance["name"]
        comparison = comparison_records[instance_name]
        figure, axes = plt.subplots(1, 3, figsize=(18.5, 6.2), constrained_layout=True)

        for axis, (label, status_key, solver_key) in zip(axes, PLOTS, strict=True):
            status = "baseline" if status_key is None else comparison[status_key]
            plot_solution(axis, instance, solver_maps[solver_key][instance_name], label, status)

        figure.suptitle(
            f"Li-Lim visit order visualization for {instance_name} "
            f"(OR-Tools vs Rust: {comparison['ortools_vs_rust_status']})",
            fontsize=14,
        )
        add_route_legend(figure)

        output_path = output_dir / f"{instance_name}.png"
        figure.savefig(output_path, dpi=220, bbox_inches="tight")
        plt.close(figure)
        created_files.append({"instance": instance_name, "path": str(output_path)})

    return created_files


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    instance_output_dir = args.output_dir / "instances"
    instance_output_dir.mkdir(parents=True, exist_ok=True)

    comparison_summary = load_json(args.comparison_summary)
    records = list(comparison_summary["records"])
    comparison_records = {record["instance"]: record for record in records}
    instances = [
        load_json(instance_path)
        for instance_path in sorted(args.instances_dir.glob("instance_*.json"))
    ]
    reference_solutions = {
        instance["name"]: load_solution(args.reference_dir, instance["name"])
        for instance in instances
    }
    ortools_solutions = {
        instance["name"]: load_solution(args.ortools_dir, instance["name"])
        for instance in instances
    }
    rust_solutions = {
        instance["name"]: load_solution(args.rust_dir, instance["name"])
        for instance in instances
    }

    created_instance_figures = render_instance_figures(
        instances,
        reference_solutions,
        ortools_solutions,
        rust_solutions,
        comparison_records,
        instance_output_dir,
    )
    score_chart_path = render_score_comparison(records, args.output_dir / "score_comparison.png")

    manifest = {
        "instance_figures": created_instance_figures,
        "score_comparison_chart": score_chart_path,
        "comparison_summary": str(args.comparison_summary),
    }
    save_json(manifest, args.output_dir / "manifest.json")

    print(
        f"Saved {len(created_instance_figures)} per-instance figures to {instance_output_dir} "
        f"and score comparison chart to {score_chart_path}"
    )


if __name__ == "__main__":
    main()
