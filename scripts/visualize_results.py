from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from common import load_json, save_json

ROUTE_COLOURS = list(plt.get_cmap("tab20").colors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize solver outputs.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances"))
    parser.add_argument("--pyvrp-dir", type=Path, default=Path("results/pyvrp"))
    parser.add_argument("--rust-dir", type=Path, default=Path("results/rust"))
    parser.add_argument(
        "--comparison-summary",
        type=Path,
        default=Path("results/comparison/summary.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/visualization"))
    return parser.parse_args()


def load_solution(solution_dir: Path, instance_name: str) -> dict[str, Any]:
    return load_json(solution_dir / f"{instance_name}.solution.json")


def build_lookup(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def route_polyline(
    instance: dict[str, Any],
    route: dict[str, Any],
) -> tuple[list[float], list[float]]:
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


def plot_solution(
    ax: plt.Axes,
    instance: dict[str, Any],
    solution: dict[str, Any],
    solver_label: str,
) -> None:
    depots = build_lookup(instance["depots"])
    nodes = build_lookup(instance["nodes"])
    pickups = [node for node in instance["nodes"] if node["kind"] == "pickup"]
    deliveries = [node for node in instance["nodes"] if node["kind"] == "delivery"]

    ax.scatter(
        [location["x"] for location in instance["location_catalog"]],
        [location["y"] for location in instance["location_catalog"]],
        marker="x",
        s=20,
        linewidths=0.8,
        color="#d0d0d0",
        alpha=0.6,
        zorder=0,
    )

    ax.scatter(
        [node["x"] for node in pickups],
        [node["y"] for node in pickups],
        marker="o",
        s=24,
        linewidths=0.6,
        facecolors="white",
        edgecolors="#8c8c8c",
        zorder=2,
    )
    ax.scatter(
        [node["x"] for node in deliveries],
        [node["y"] for node in deliveries],
        marker="s",
        s=24,
        linewidths=0.6,
        facecolors="white",
        edgecolors="#8c8c8c",
        zorder=2,
    )

    for route_index, route in enumerate(solution["routes"]):
        colour = ROUTE_COLOURS[route_index % len(ROUTE_COLOURS)]
        x_values, y_values = route_polyline(instance, route)
        ax.plot(x_values, y_values, color=colour, linewidth=1.4, alpha=0.92, zorder=1)

        route_nodes = [nodes[node_id] for node_id in route["node_ids"]]
        pickup_nodes = [node for node in route_nodes if node["kind"] == "pickup"]
        delivery_nodes = [node for node in route_nodes if node["kind"] == "delivery"]

        if pickup_nodes:
            ax.scatter(
                [node["x"] for node in pickup_nodes],
                [node["y"] for node in pickup_nodes],
                marker="o",
                s=28,
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
                s=28,
                linewidths=0.9,
                facecolors="white",
                edgecolors=[colour],
                zorder=3,
            )

    ax.scatter(
        [depot["x"] for depot in instance["depots"]],
        [depot["y"] for depot in instance["depots"]],
        marker="*",
        s=180,
        linewidths=0.8,
        facecolors="#f4d35e",
        edgecolors="#333333",
        zorder=4,
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

    objective = solution["evaluation"]["objective"]
    route_count = solution["evaluation"]["route_count"]
    ax.set_title(f"{instance['name']} / {solver_label}\nobj={objective} routes={route_count}", fontsize=10)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
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
            markersize=12,
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
    ]
    fig.legend(handles=legend_handles, loc="upper center", ncol=4, frameon=False)


def render_instance_figures(
    instances: list[dict[str, Any]],
    pyvrp_solutions: dict[str, dict[str, Any]],
    rust_solutions: dict[str, dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[dict[str, str]] = []

    for instance in instances:
        instance_name = instance["name"]
        figure, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
        plot_solution(axes[0], instance, pyvrp_solutions[instance_name], "PyVRP")
        plot_solution(axes[1], instance, rust_solutions[instance_name], "Rust ALNS")
        figure.suptitle(f"Visit visualization for {instance_name}", fontsize=14)
        add_route_legend(figure)

        output_path = output_dir / f"{instance_name}.png"
        figure.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(figure)
        created_files.append({"instance": instance_name, "path": str(output_path)})

    return created_files


def render_overview_figure(
    instances: list[dict[str, Any]],
    pyvrp_solutions: dict[str, dict[str, Any]],
    rust_solutions: dict[str, dict[str, Any]],
    output_path: Path,
) -> None:
    row_count = len(instances)
    figure, axes = plt.subplots(
        row_count,
        2,
        figsize=(14, max(3.4 * row_count, 10)),
        constrained_layout=True,
    )

    for row_index, instance in enumerate(instances):
        plot_solution(axes[row_index][0], instance, pyvrp_solutions[instance["name"]], "PyVRP")
        plot_solution(axes[row_index][1], instance, rust_solutions[instance["name"]], "Rust ALNS")

    figure.suptitle("All instance visit visualizations", fontsize=16)
    add_route_legend(figure)
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def render_score_comparison(records: list[dict[str, Any]], output_path: Path) -> None:
    instance_names = [record["instance"] for record in records]
    pyvrp_scores = [record["pyvrp_objective"] for record in records]
    rust_scores = [record["rust_objective"] for record in records]
    positions = list(range(len(records)))
    width = 0.38

    figure, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)
    pyvrp_bars = ax.bar(
        [position - width / 2 for position in positions],
        pyvrp_scores,
        width=width,
        label="PyVRP",
        color="#4C72B0",
    )
    rust_bars = ax.bar(
        [position + width / 2 for position in positions],
        rust_scores,
        width=width,
        label="Rust ALNS",
        color="#DD8452",
    )

    for bar, record in zip(rust_bars, records, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 6,
            f"{record['gap_pct']:.1f}%",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#444444",
        )

    ax.set_title("Objective score comparison")
    ax.set_ylabel("Objective value")
    ax.set_xticks(positions, instance_names, rotation=30, ha="right")
    ax.yaxis.grid(True, linestyle=":", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)

    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    instance_output_dir = args.output_dir / "instances"
    instance_output_dir.mkdir(parents=True, exist_ok=True)

    comparison_summary = load_json(args.comparison_summary)
    instances = [
        load_json(instance_path)
        for instance_path in sorted(args.instances_dir.glob("instance_*.json"))
    ]
    pyvrp_solutions = {
        instance["name"]: load_solution(args.pyvrp_dir, instance["name"])
        for instance in instances
    }
    rust_solutions = {
        instance["name"]: load_solution(args.rust_dir, instance["name"])
        for instance in instances
    }

    created_instance_figures = render_instance_figures(
        instances,
        pyvrp_solutions,
        rust_solutions,
        instance_output_dir,
    )

    overview_path = args.output_dir / "route_visits_overview.png"
    render_overview_figure(instances, pyvrp_solutions, rust_solutions, overview_path)

    score_comparison_path = args.output_dir / "score_comparison.png"
    render_score_comparison(comparison_summary["records"], score_comparison_path)

    manifest = {
        "overview_path": str(overview_path),
        "score_comparison_path": str(score_comparison_path),
        "instance_figures": created_instance_figures,
    }
    save_json(manifest, args.output_dir / "manifest.json")

    print(f"Saved route overview to {overview_path}")
    print(f"Saved score comparison to {score_comparison_path}")
    print(f"Saved {len(created_instance_figures)} per-instance figures to {instance_output_dir}")


if __name__ == "__main__":
    main()
