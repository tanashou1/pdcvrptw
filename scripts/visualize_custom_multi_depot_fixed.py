from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from common import load_json, save_json

ROUTE_COLOURS = list(plt.get_cmap("tab10").colors) + list(plt.get_cmap("tab20").colors)
FIXED_COLOUR = "#4c78a8"
OPTIONAL_SERVED_COLOUR = "#54a24b"
OPTIONAL_MISSING_COLOUR = "#e45756"
REQUIRED_COLOUR = "#f58518"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize custom multi-depot fixed-task instances and solver outcomes."
    )
    parser.add_argument(
        "--instances-dir",
        type=Path,
        default=Path("instances/custom_multi_depot_fixed"),
    )
    parser.add_argument(
        "--solution-dir",
        type=Path,
        default=Path("results/custom_multi_depot_fixed/rust"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/custom_multi_depot_fixed/visualization"),
    )
    return parser.parse_args()


def build_lookup(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def axis_limits(instance: dict[str, Any]) -> tuple[float, float, float, float]:
    xs = [float(location["x"]) for location in instance["location_catalog"]]
    ys = [float(location["y"]) for location in instance["location_catalog"]]
    xs.extend(float(depot["x"]) for depot in instance["depots"])
    ys.extend(float(depot["y"]) for depot in instance["depots"])
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    margin = max(4.0, 0.08 * max(span_x, span_y, 1.0))
    return min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin


def route_polyline(instance: dict[str, Any], route: dict[str, Any]) -> tuple[list[float], list[float]]:
    depots = build_lookup(instance["depots"])
    nodes = build_lookup(instance["nodes"])
    depot = depots[route["depot_id"]]
    xs = [float(depot["x"])]
    ys = [float(depot["y"])]
    for node_id in route["node_ids"]:
        node = nodes[node_id]
        xs.append(float(node["x"]))
        ys.append(float(node["y"]))
    xs.append(float(depot["x"]))
    ys.append(float(depot["y"]))
    return xs, ys


def vehicle_colour_map(solution: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    vehicle_ids = [route["vehicle_id"] for route in solution["routes"]]
    return {
        vehicle_id: ROUTE_COLOURS[index % len(ROUTE_COLOURS)]
        for index, vehicle_id in enumerate(vehicle_ids)
    }


def fixed_task_records(instance: dict[str, Any], solution: dict[str, Any]) -> list[dict[str, Any]]:
    fixed_nodes = [node for node in instance["nodes"] if node.get("fixed_vehicle_id")]
    records = []
    for node in fixed_nodes:
        record = {
            "node_id": node["id"],
            "expected_vehicle_id": node["fixed_vehicle_id"],
            "scheduled_time": float(node["tw"]["start"]),
            "served": False,
            "served_vehicle_id": None,
            "start_service": None,
            "vehicle_ok": False,
            "time_ok": False,
        }

        for route in solution["evaluation"]["routes"]:
            stop_lookup = {stop["node_id"]: stop for stop in route["stops"]}
            if node["id"] not in stop_lookup:
                continue
            stop = stop_lookup[node["id"]]
            record["served"] = True
            record["served_vehicle_id"] = route["vehicle_id"]
            record["start_service"] = float(stop["start_service"])
            record["vehicle_ok"] = route["vehicle_id"] == node["fixed_vehicle_id"]
            record["time_ok"] = abs(float(stop["start_service"]) - float(node["tw"]["start"])) < 1e-6
            break

        records.append(record)

    return records


def summary_record(instance: dict[str, Any], solution: dict[str, Any]) -> dict[str, Any]:
    fixed_records = fixed_task_records(instance, solution)
    evaluation = solution["evaluation"]
    return {
        "instance": instance["name"],
        "vehicle_count": len(instance.get("vehicles", [])),
        "route_count": int(evaluation["route_count"]),
        "fixed_total": len(fixed_records),
        "fixed_vehicle_ok": sum(1 for record in fixed_records if record["vehicle_ok"]),
        "fixed_time_ok": sum(1 for record in fixed_records if record["time_ok"]),
        "optional_total": int(evaluation["total_optional_nodes"]),
        "optional_served": int(evaluation["served_optional_nodes"]),
        "optional_missing": len(evaluation["missing_optional_nodes"]),
        "missing_optional_nodes": list(evaluation["missing_optional_nodes"]),
        "feasible": bool(evaluation["feasible"]),
    }


def plot_map_panel(
    ax: plt.Axes,
    instance: dict[str, Any],
    solution: dict[str, Any],
    colours: dict[str, tuple[float, float, float]],
    summary: dict[str, Any],
) -> None:
    nodes = build_lookup(instance["nodes"])
    served_ids = {
        node_id
        for route in solution["routes"]
        for node_id in route["node_ids"]
    }
    optional_served = [
        node for node in instance["nodes"] if (not node.get("required", True)) and node["id"] in served_ids
    ]
    optional_missing = [
        node for node in instance["nodes"] if node["id"] in set(summary["missing_optional_nodes"])
    ]
    fixed_nodes = [node for node in instance["nodes"] if node.get("fixed_vehicle_id")]
    required_regular = [
        node
        for node in instance["nodes"]
        if node.get("required", True) and not node.get("fixed_vehicle_id")
    ]

    if required_regular:
        ax.scatter(
            [node["x"] for node in required_regular],
            [node["y"] for node in required_regular],
            marker="o",
            s=40,
            linewidths=0.8,
            facecolors="white",
            edgecolors=REQUIRED_COLOUR,
            zorder=2,
        )

    if optional_served:
        ax.scatter(
            [node["x"] for node in optional_served],
            [node["y"] for node in optional_served],
            marker="o",
            s=34,
            linewidths=0.8,
            facecolors="white",
            edgecolors=OPTIONAL_SERVED_COLOUR,
            zorder=2,
        )

    if optional_missing:
        ax.scatter(
            [node["x"] for node in optional_missing],
            [node["y"] for node in optional_missing],
            marker="x",
            s=80,
            linewidths=1.5,
            c=OPTIONAL_MISSING_COLOUR,
            zorder=3,
        )

    for route in solution["routes"]:
        colour = colours[route["vehicle_id"]]
        xs, ys = route_polyline(instance, route)
        ax.plot(xs, ys, color=colour, linewidth=1.6, alpha=0.9, zorder=1)

        for stop_index, node_id in enumerate(route["node_ids"], start=1):
            node = nodes[node_id]
            if node.get("fixed_vehicle_id"):
                marker = "D"
                size = 70
                facecolour = colour
                edgecolour = "#222222"
            elif node.get("required", True):
                marker = "o"
                size = 48
                facecolour = colour
                edgecolour = "#222222"
            else:
                marker = "o"
                size = 40
                facecolour = "white"
                edgecolour = colour

            ax.scatter(
                [node["x"]],
                [node["y"]],
                marker=marker,
                s=size,
                linewidths=1.0,
                facecolors=facecolour,
                edgecolors=edgecolour,
                zorder=4,
            )
            ax.text(
                float(node["x"]) + 0.7,
                float(node["y"]) + 0.7,
                str(stop_index),
                fontsize=6,
                color=colour,
                ha="center",
                va="center",
                bbox={
                    "boxstyle": "round,pad=0.13",
                    "facecolor": "white",
                    "edgecolor": colour,
                    "linewidth": 0.6,
                    "alpha": 0.9,
                },
                zorder=5,
            )

    for node in fixed_nodes:
        ax.annotate(
            node["fixed_vehicle_id"],
            (float(node["x"]), float(node["y"])),
            xytext=(4, -10),
            textcoords="offset points",
            fontsize=6,
            color=FIXED_COLOUR,
        )

    for node in optional_missing:
        ax.annotate(
            node["id"],
            (float(node["x"]), float(node["y"])),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=6,
            color=OPTIONAL_MISSING_COLOUR,
        )

    ax.scatter(
        [depot["x"] for depot in instance["depots"]],
        [depot["y"] for depot in instance["depots"]],
        marker="*",
        s=180,
        linewidths=0.8,
        facecolors="#f4d35e",
        edgecolors="#333333",
        zorder=6,
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
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"Map view\nroutes={summary['route_count']}/{summary['vehicle_count']} "
        f"optional served={summary['optional_served']}/{summary['optional_total']}",
        fontsize=10,
    )


def plot_timeline_panel(
    ax: plt.Axes,
    instance: dict[str, Any],
    solution: dict[str, Any],
    colours: dict[str, tuple[float, float, float]],
    fixed_records: list[dict[str, Any]],
) -> None:
    vehicle_order = [vehicle["id"] for vehicle in instance.get("vehicles", [])]
    y_positions = {vehicle_id: index for index, vehicle_id in enumerate(reversed(vehicle_order))}
    nodes = build_lookup(instance["nodes"])
    horizon_end = float(instance["planning_horizon"]["end"])

    for vehicle_id, y in y_positions.items():
        ax.hlines(y, 0.0, horizon_end, color="#e0e0e0", linewidth=1.0, zorder=0)

    fixed_lookup = {record["node_id"]: record for record in fixed_records}
    for route in solution["evaluation"]["routes"]:
        vehicle_id = route["vehicle_id"]
        y = y_positions[vehicle_id]
        colour = colours[vehicle_id]
        start_times = [float(stop["start_service"]) for stop in route["stops"]]
        ax.plot(start_times, [y] * len(start_times), color=colour, linewidth=1.4, alpha=0.9, zorder=1)

        for stop in route["stops"]:
            node = nodes[stop["node_id"]]
            x = float(stop["start_service"])
            if node.get("fixed_vehicle_id"):
                ax.scatter(
                    [x],
                    [y],
                    marker="D",
                    s=70,
                    facecolors=colour,
                    edgecolors="#222222",
                    linewidths=1.0,
                    zorder=3,
                )
                ax.vlines(
                    float(node["tw"]["start"]),
                    y - 0.22,
                    y + 0.22,
                    color=FIXED_COLOUR,
                    linestyle="--",
                    linewidth=1.0,
                    zorder=2,
                )
            else:
                ax.scatter(
                    [x],
                    [y],
                    marker="o",
                    s=38,
                    facecolors="white",
                    edgecolors=colour,
                    linewidths=1.0,
                    zorder=3,
                )

            ax.annotate(
                stop["node_id"],
                (x, y),
                xytext=(0, 7),
                textcoords="offset points",
                fontsize=6,
                ha="center",
                color=colour,
            )

    ax.set_yticks([y_positions[vehicle_id] for vehicle_id in vehicle_order[::-1]])
    ax.set_yticklabels(vehicle_order[::-1], fontsize=8)
    ax.set_xlim(0.0, horizon_end)
    ax.set_xlabel("Service start time")
    ax.set_title("Vehicle timeline\nfixed tasks shown with scheduled-time markers", fontsize=10)
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)

    fixed_status_lines = []
    for record in fixed_records:
        status = "OK" if record["vehicle_ok"] and record["time_ok"] else "NG"
        fixed_status_lines.append(
            f"{record['node_id']}: {record['expected_vehicle_id']} @ {record['scheduled_time']:.0f} -> {status}"
        )
    if fixed_status_lines:
        ax.text(
            1.01,
            0.98,
            "\n".join(fixed_status_lines),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "white",
                "edgecolor": "#cccccc",
                "alpha": 0.95,
            },
        )


def render_instance_figure(
    instance: dict[str, Any],
    solution: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    colours = vehicle_colour_map(solution)
    fixed_records = fixed_task_records(instance, solution)
    summary = summary_record(instance, solution)

    figure, (map_ax, timeline_ax) = plt.subplots(
        1,
        2,
        figsize=(15, 6.4),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.15, 1.0]},
    )
    plot_map_panel(map_ax, instance, solution, colours, summary)
    plot_timeline_panel(timeline_ax, instance, solution, colours, fixed_records)

    legend_handles = [
        Line2D([0], [0], marker="*", linestyle="None", markerfacecolor="#f4d35e", markeredgecolor="#333333", markersize=11, label="Depot"),
        Line2D([0], [0], marker="D", linestyle="None", markerfacecolor=FIXED_COLOUR, markeredgecolor="#222222", markersize=8, label="Fixed task"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor="white", markeredgecolor=OPTIONAL_SERVED_COLOUR, markersize=7, label="Optional served"),
        Line2D([0], [0], marker="x", linestyle="None", color=OPTIONAL_MISSING_COLOUR, markersize=8, label="Optional missing"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor="white", markeredgecolor=REQUIRED_COLOUR, markersize=7, label="Required task"),
    ]
    figure.legend(handles=legend_handles, loc="upper center", ncol=5, frameon=False)
    figure.suptitle(
        f"{instance['name']}: multi-depot routes, vehicle-fixed tasks, and optional overflow",
        fontsize=13,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return summary


def render_summary(records: list[dict[str, Any]], output_path: Path) -> None:
    indices = list(range(len(records)))
    names = [record["instance"] for record in records]

    figure, (fixed_ax, optional_ax) = plt.subplots(
        2,
        1,
        figsize=(12, 8),
        constrained_layout=True,
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.1]},
    )

    width = 0.34
    fixed_vehicle_ok = [record["fixed_vehicle_ok"] for record in records]
    fixed_vehicle_ng = [record["fixed_total"] - record["fixed_vehicle_ok"] for record in records]
    fixed_time_ok = [record["fixed_time_ok"] for record in records]
    fixed_time_ng = [record["fixed_total"] - record["fixed_time_ok"] for record in records]

    fixed_ax.bar(
        [index - width / 2 for index in indices],
        fixed_vehicle_ok,
        width=width,
        color=FIXED_COLOUR,
        label="Fixed task on assigned vehicle",
    )
    fixed_ax.bar(
        [index - width / 2 for index in indices],
        fixed_vehicle_ng,
        width=width,
        bottom=fixed_vehicle_ok,
        color=OPTIONAL_MISSING_COLOUR,
        label="Vehicle mismatch",
    )
    fixed_ax.bar(
        [index + width / 2 for index in indices],
        fixed_time_ok,
        width=width,
        color=OPTIONAL_SERVED_COLOUR,
        label="Fixed task on scheduled time",
    )
    fixed_ax.bar(
        [index + width / 2 for index in indices],
        fixed_time_ng,
        width=width,
        bottom=fixed_time_ok,
        color="#b279a2",
        label="Timing mismatch",
    )
    for index, record in enumerate(records):
        fixed_ax.text(index - width / 2, record["fixed_total"] + 0.05, f"{record['fixed_vehicle_ok']}/{record['fixed_total']}", ha="center", fontsize=8)
        fixed_ax.text(index + width / 2, record["fixed_total"] + 0.05, f"{record['fixed_time_ok']}/{record['fixed_total']}", ha="center", fontsize=8)
    fixed_ax.set_ylabel("Fixed tasks")
    fixed_ax.set_title("Fixed-task validation")
    fixed_ax.legend(loc="upper left", ncol=2, fontsize=8)

    optional_served = [record["optional_served"] for record in records]
    optional_missing = [record["optional_missing"] for record in records]
    optional_ax.bar(indices, optional_served, color=OPTIONAL_SERVED_COLOUR, label="Optional served")
    optional_ax.bar(
        indices,
        optional_missing,
        bottom=optional_served,
        color=OPTIONAL_MISSING_COLOUR,
        label="Optional missing",
    )
    for index, record in enumerate(records):
        optional_ax.text(
            index,
            record["optional_total"] + 0.08,
            f"routes {record['route_count']}/{record['vehicle_count']}",
            ha="center",
            fontsize=8,
        )
    optional_ax.set_ylabel("Optional tasks")
    optional_ax.set_title("Optional overflow under tight vehicle counts")
    optional_ax.legend(loc="upper left", fontsize=8)
    optional_ax.set_xticks(indices)
    optional_ax.set_xticklabels(names)
    optional_ax.set_xlabel("Instance")

    figure.suptitle("Custom multi-depot fixed-task feature summary", fontsize=13)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    args = parse_args()
    instance_paths = sorted(args.instances_dir.glob("instance_*.json"))
    if not instance_paths:
        raise SystemExit(f"No custom instances found in {args.instances_dir}")

    records = []
    for instance_path in instance_paths:
        instance = load_json(instance_path)
        solution = load_json(args.solution_dir / f"{instance['name']}.solution.json")
        record = render_instance_figure(
            instance,
            solution,
            args.output_dir / "instances" / f"{instance['name']}.png",
        )
        records.append(record)

    render_summary(records, args.output_dir / "feature_summary.png")
    save_json({"instances": records}, args.output_dir / "summary.json")
    print(
        f"Saved {len(records)} custom instance figures to {args.output_dir / 'instances'} "
        f"and summary chart to {args.output_dir / 'feature_summary.png'}"
    )


if __name__ == "__main__":
    main()
