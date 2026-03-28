#!/usr/bin/env python3
"""Animate the ALNS optimization process.

Usage:
    # Step 1: generate history JSON
    cargo run --release -- animate \\
        --instance instances/li_lim_100/instance_lrc202.json \\
        --output animation_history.json \\
        --iterations 2100 --seed 77

    # Step 2: render animation
    python scripts/animate_alns.py \\
        --history animation_history.json \\
        --instance instances/li_lim_100/instance_lrc202.json \\
        --output results/animation.gif \\
        [--fps 15] [--dpi 100]
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Animate ALNS optimization")
    parser.add_argument("--history", required=True, help="History JSON from animate command")
    parser.add_argument("--instance", required=True, help="Instance JSON file")
    parser.add_argument("--output", default="results/animation.gif",
                        help="Output file (.gif or .mp4)")
    parser.add_argument("--fps", type=int, default=15, help="Frames per second")
    parser.add_argument("--dpi", type=int, default=100, help="Output DPI")
    return parser.parse_args()


def load_json(path):
    with open(path) as f:
        return json.load(f)


def build_coords(instance):
    node_coords = {node["id"]: (node["x"], node["y"]) for node in instance["nodes"]}
    depot_coords = {depot["id"]: (depot["x"], depot["y"]) for depot in instance["depots"]}
    return node_coords, depot_coords


def route_to_coords(route, node_coords, depot_coords):
    depot_xy = depot_coords.get(route["depot_id"])
    if depot_xy is None:
        return []
    path = [depot_xy]
    for nid in route["node_ids"]:
        xy = node_coords.get(nid)
        if xy is not None:
            path.append(xy)
    path.append(depot_xy)
    return path


def draw_routes(ax, routes, node_coords, depot_coords,
                colors, linestyle="-", lw=2, alpha=1.0, zorder=4):
    artists = []
    for i, route in enumerate(routes):
        coords = route_to_coords(route, node_coords, depot_coords)
        if len(coords) < 2:
            continue
        xs, ys = zip(*coords)
        color = colors[i % len(colors)] if colors else "gray"
        (line,) = ax.plot(xs, ys, linestyle=linestyle, color=color,
                          lw=lw, alpha=alpha, zorder=zorder)
        artists.append(line)
    return artists


def decompose_score(score, is_vehicle_mode):
    """Return (route_count_from_penalty, distance) for vehicles_then_distance,
    or (None, score) for distance_only."""
    if is_vehicle_mode:
        v = int(score // 1_000_000)
        d = score % 1_000_000
        return v, d
    return None, score


def style_ax(ax, title, ylabel, xlabel=None):
    ax.set_facecolor("#0f0f1a")
    ax.tick_params(colors="white", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")
    ax.set_title(title, color="white", fontsize=9, pad=3)
    ax.set_ylabel(ylabel, color="#aaaacc", fontsize=8)
    if xlabel:
        ax.set_xlabel(xlabel, color="#aaaacc", fontsize=8)
    ax.grid(True, color="#222244", linewidth=0.5, alpha=0.8)


def main():
    args = parse_args()
    history = load_json(args.history)
    instance = load_json(args.instance)

    node_coords, depot_coords = build_coords(instance)
    snapshots = history["snapshots"]
    total_iters = history["total_iterations"]
    instance_name = history["instance_name"]

    if not snapshots:
        print("No snapshots found in history.")
        return

    # ---------------------------------------------------------------- data prep
    iters = [s["iteration"] for s in snapshots]
    best_scores = [s["best_score"] for s in snapshots]
    cand_scores = [s["candidate_score"] for s in snapshots]
    temps = [s["temperature"] for s in snapshots]
    best_route_counts = [len(s["best_routes"]) for s in snapshots]
    cand_route_counts = [len(s["candidate_routes"]) for s in snapshots]

    # Detect vehicles_then_distance mode
    is_vehicle_mode = best_scores[0] >= 1_000_000

    if is_vehicle_mode:
        best_dist = [sc % 1_000_000 for sc in best_scores]
        cand_dist = [sc % 1_000_000 for sc in cand_scores]
    else:
        best_dist = best_scores
        cand_dist = cand_scores

    # Map bounds
    all_x = [c[0] for c in node_coords.values()]
    all_y = [c[1] for c in node_coords.values()]
    pad_x = (max(all_x) - min(all_x)) * 0.05 + 2
    pad_y = (max(all_y) - min(all_y)) * 0.05 + 2
    map_xlim = (min(all_x) - pad_x, max(all_x) + pad_x)
    map_ylim = (min(all_y) - pad_y, max(all_y) + pad_y)
    depot_xs = [c[0] for c in depot_coords.values()]
    depot_ys = [c[1] for c in depot_coords.values()]

    # Score axis ranges
    dist_min = min(best_dist) * 0.995
    # Clip extreme candidate outliers (top 5%) for readability
    sorted_cand = sorted(cand_dist)
    dist_max = sorted_cand[int(len(sorted_cand) * 0.95)] * 1.02
    dist_max = max(dist_max, dist_min * 1.01)

    route_min = min(min(best_route_counts), min(cand_route_counts)) - 0.5
    route_max = max(max(best_route_counts), max(cand_route_counts)) + 0.5

    cmap = plt.get_cmap("tab10")
    route_colors = [cmap(i) for i in range(10)]

    # ----------------------------------------------------------- figure layout
    fig = plt.figure(figsize=(16, 8), facecolor="#1a1a2e")
    fig.suptitle(
        f"ALNS Optimization — {instance_name}",
        color="white", fontsize=13, fontweight="bold", y=0.98,
    )

    ax_map = fig.add_axes([0.02, 0.06, 0.56, 0.88])

    if is_vehicle_mode:
        # Three right panels: route count / distance / temperature
        ax_routes = fig.add_axes([0.63, 0.70, 0.35, 0.22])
        ax_dist   = fig.add_axes([0.63, 0.40, 0.35, 0.24])
        ax_temp   = fig.add_axes([0.63, 0.08, 0.35, 0.24])
        ax_score  = None
    else:
        # Two right panels: score / temperature
        ax_score  = fig.add_axes([0.63, 0.55, 0.35, 0.37])
        ax_temp   = fig.add_axes([0.63, 0.10, 0.35, 0.37])
        ax_routes = None
        ax_dist   = None

    # --------------------------------------------------------- map static setup
    ax_map.set_facecolor("#0f0f1a")
    ax_map.tick_params(colors="white", labelsize=8)
    for spine in ax_map.spines.values():
        spine.set_edgecolor("#444466")
    ax_map.set_xlim(map_xlim)
    ax_map.set_ylim(map_ylim)
    ax_map.set_aspect("equal", adjustable="box")

    ax_map.scatter(all_x, all_y, s=12, c="#8888bb", zorder=2, alpha=0.6)
    ax_map.scatter(depot_xs, depot_ys, s=220, c="gold", marker="*",
                   zorder=6, edgecolors="white", linewidths=0.5)

    # ------------------------------------------ right panel setup
    if is_vehicle_mode:
        style_ax(ax_routes, "Route Count", "Routes")
        ax_routes.set_xlim(0, total_iters)
        ax_routes.set_ylim(route_min, route_max)
        ax_routes.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        style_ax(ax_dist, "Distance", "Distance")
        ax_dist.set_xlim(0, total_iters)
        ax_dist.set_ylim(dist_min, dist_max)
    else:
        style_ax(ax_score, "Score", "Score")
        ax_score.set_xlim(0, total_iters)
        ax_score.set_ylim(dist_min, dist_max)

    style_ax(ax_temp, "Temperature", "Temperature", xlabel="Iteration")
    ax_temp.set_xlim(0, total_iters)
    ax_temp.set_ylim(0, max(temps) * 1.05)

    # ------------------------------------------ line objects
    route_artists = []

    if is_vehicle_mode:
        (line_best_rc,) = ax_routes.plot(
            [], [], color="#4fc3f7", lw=2, drawstyle="steps-post",
            label="Best", zorder=4)
        (line_cand_rc,) = ax_routes.plot(
            [], [], color="#ffb74d", lw=1.2, linestyle="--",
            drawstyle="steps-post", alpha=0.7, label="Candidate", zorder=3)
        vline_rc = ax_routes.axvline(0, color="#ff5555", lw=0.8, linestyle=":", zorder=5)
        ax_routes.legend(loc="upper right", fontsize=8, facecolor="#1a1a2e",
                         edgecolor="#444466", labelcolor="white")

        (line_best_d,) = ax_dist.plot(
            [], [], color="#4fc3f7", lw=2, label="Best", zorder=4)
        (line_cand_d,) = ax_dist.plot(
            [], [], color="#ffb74d", lw=1.2, linestyle="--",
            alpha=0.7, label="Candidate", zorder=3)
        vline_dist = ax_dist.axvline(0, color="#ff5555", lw=0.8, linestyle=":", zorder=5)
        ax_dist.legend(loc="upper right", fontsize=8, facecolor="#1a1a2e",
                       edgecolor="#444466", labelcolor="white")

        line_best_sc = line_cand_sc = vline_score = None
    else:
        (line_best_sc,) = ax_score.plot(
            [], [], color="#4fc3f7", lw=2, label="Best", zorder=4)
        (line_cand_sc,) = ax_score.plot(
            [], [], color="#ffb74d", lw=1.2, linestyle="--",
            alpha=0.75, label="Candidate", zorder=3)
        vline_score = ax_score.axvline(0, color="#ff5555", lw=0.8, linestyle=":", zorder=5)
        ax_score.legend(loc="upper right", fontsize=8, facecolor="#1a1a2e",
                        edgecolor="#444466", labelcolor="white")

        line_best_rc = line_cand_rc = vline_rc = None
        line_best_d = line_cand_d = vline_dist = None

    (line_temp,) = ax_temp.plot([], [], color="#ef5350", lw=1.5, zorder=4)
    vline_temp = ax_temp.axvline(0, color="#ff5555", lw=0.8, linestyle=":", zorder=5)

    # Info text on map
    info_text = ax_map.text(
        0.02, 0.98, "", transform=ax_map.transAxes,
        verticalalignment="top", fontsize=9, color="white",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1a1a2e",
                  alpha=0.85, edgecolor="#444466"),
        zorder=10,
    )

    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], color="white", lw=2, label="Best routes"),
        Line2D([0], [0], color="#888888", lw=1.5, linestyle="--",
               alpha=0.7, label="Candidate routes"),
        Line2D([0], [0], marker="*", color="gold", markersize=10,
               lw=0, label="Depot"),
    ]
    ax_map.legend(handles=legend_handles, loc="lower right", fontsize=8,
                  facecolor="#1a1a2e", edgecolor="#444466", labelcolor="white")

    # ----------------------------------------------------------- update function
    def update(frame_idx):
        snap = snapshots[frame_idx]
        iter_num = snap["iteration"]
        x_data = iters[: frame_idx + 1]

        # ---- clear previous route lines ----
        for artist in route_artists:
            artist.remove()
        route_artists.clear()

        # Candidate routes (dashed gray, behind)
        cand_arts = draw_routes(
            ax_map, snap["candidate_routes"], node_coords, depot_coords,
            colors=["#555577"] * 20,
            linestyle="--", lw=1.3, alpha=0.55, zorder=3,
        )
        route_artists.extend(cand_arts)

        # Best routes (solid, colored, on top)
        best_arts = draw_routes(
            ax_map, snap["best_routes"], node_coords, depot_coords,
            colors=route_colors,
            linestyle="-", lw=2.0, alpha=0.9, zorder=4,
        )
        route_artists.extend(best_arts)

        # ---- graphs ----
        if is_vehicle_mode:
            line_best_rc.set_data(x_data, best_route_counts[: frame_idx + 1])
            line_cand_rc.set_data(x_data, cand_route_counts[: frame_idx + 1])
            vline_rc.set_xdata([iter_num, iter_num])

            line_best_d.set_data(x_data, best_dist[: frame_idx + 1])
            line_cand_d.set_data(x_data, cand_dist[: frame_idx + 1])
            vline_dist.set_xdata([iter_num, iter_num])
        else:
            line_best_sc.set_data(x_data, best_scores[: frame_idx + 1])
            line_cand_sc.set_data(x_data, cand_scores[: frame_idx + 1])
            vline_score.set_xdata([iter_num, iter_num])

        line_temp.set_data(x_data, temps[: frame_idx + 1])
        vline_temp.set_xdata([iter_num, iter_num])

        # ---- info text ----
        bv, bd = decompose_score(snap["best_score"], is_vehicle_mode)
        cv, cd = decompose_score(snap["candidate_score"], is_vehicle_mode)
        marker = " ★" if snap["best_updated"] else (" ✓" if snap["accepted"] else "")

        if is_vehicle_mode:
            info = (
                f"Iteration : {iter_num:>6}\n"
                f"Best      : {bv}v  dist={bd:.1f}\n"
                f"Candidate : {cv}v  dist={cd:.1f}\n"
                f"Temp      : {snap['temperature']:>8.2f}{marker}"
            )
        else:
            info = (
                f"Iteration : {iter_num:>6}\n"
                f"Best      : {snap['best_score']:.2f}\n"
                f"Candidate : {snap['candidate_score']:.2f}\n"
                f"Temp      : {snap['temperature']:>8.2f}{marker}"
            )
        info_text.set_text(info)

    # ----------------------------------------------------------- render
    n_frames = len(snapshots)
    print(f"Rendering {n_frames} frames at {args.fps} fps...")

    ani = animation.FuncAnimation(
        fig, update, frames=n_frames,
        interval=1000 // args.fps, blit=False,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".mp4":
        writer = animation.FFMpegWriter(
            fps=args.fps, bitrate=2000,
            extra_args=["-vcodec", "libx264"],
        )
    else:
        writer = animation.PillowWriter(fps=args.fps)

    ani.save(str(output_path), writer=writer, dpi=args.dpi,
             savefig_kwargs={"facecolor": "#1a1a2e"})
    print(f"Animation saved to {output_path}")
    plt.close()


if __name__ == "__main__":
    main()
