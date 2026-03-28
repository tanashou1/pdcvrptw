#!/usr/bin/env python3
"""Animate the ALNS optimization process.

Usage:
    python scripts/animate_alns.py \\
        --history animation_history.json \\
        --instance instances/li_lim_100/instance_lc101.json \\
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
    parser.add_argument("--output", default="results/animation.gif", help="Output file (.gif or .mp4)")
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
    """Return list of (x, y) for a route: depot -> nodes -> depot."""
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


def draw_routes(ax, routes, node_coords, depot_coords, colors, linestyle="-", lw=2, alpha=1.0, zorder=4):
    artists = []
    for i, route in enumerate(routes):
        coords = route_to_coords(route, node_coords, depot_coords)
        if len(coords) < 2:
            continue
        xs, ys = zip(*coords)
        color = colors[i % len(colors)] if colors else "gray"
        (line,) = ax.plot(xs, ys, linestyle=linestyle, color=color, lw=lw, alpha=alpha, zorder=zorder)
        artists.append(line)
    return artists


def format_score(score):
    """Format score for display, handling large vehicle-penalty values."""
    if score >= 1e12:
        return f"{score:.3e}"
    if score >= 1e6:
        vehicles = int(score // 1_000_000)
        dist = score % 1_000_000
        return f"{vehicles}v + {dist:.1f}"
    return f"{score:.2f}"


def main():
    args = parse_args()
    history = load_json(args.history)
    instance = load_json(args.instance)

    node_coords, depot_coords = build_coords(instance)
    snapshots = history["snapshots"]
    total_iterations = history["total_iterations"]
    instance_name = history["instance_name"]

    if not snapshots:
        print("No snapshots found in history.")
        return

    # Pre-compute score/temperature arrays for the graphs
    iters = [s["iteration"] for s in snapshots]
    best_scores = [s["best_score"] for s in snapshots]
    cand_scores = [s["candidate_score"] for s in snapshots]
    temps = [s["temperature"] for s in snapshots]

    # Map bounds
    all_x = [c[0] for c in node_coords.values()]
    all_y = [c[1] for c in node_coords.values()]
    pad_x = (max(all_x) - min(all_x)) * 0.05 + 2
    pad_y = (max(all_y) - min(all_y)) * 0.05 + 2
    map_xlim = (min(all_x) - pad_x, max(all_x) + pad_x)
    map_ylim = (min(all_y) - pad_y, max(all_y) + pad_y)

    depot_xs = [c[0] for c in depot_coords.values()]
    depot_ys = [c[1] for c in depot_coords.values()]

    # Score axis range: drop extreme upper outliers for readability
    sorted_best = sorted(best_scores)
    score_min = sorted_best[0] * 0.995
    score_max = sorted(cand_scores)[int(len(cand_scores) * 0.95)] * 1.02
    score_max = max(score_max, score_min * 1.01)

    # Route color palette (tab10 cycling)
    cmap = plt.get_cmap("tab10")
    n_colors = 10
    route_colors = [cmap(i) for i in range(n_colors)]

    # ------------------------------------------------------------------ figure
    fig = plt.figure(figsize=(16, 8), facecolor="#1a1a2e")
    fig.suptitle(
        f"ALNS Optimization — {instance_name}",
        color="white", fontsize=13, fontweight="bold", y=0.98,
    )

    # Layout: left = map (60%), right column = score (top) + temperature (bottom)
    ax_map = fig.add_axes([0.02, 0.06, 0.56, 0.88])
    ax_score = fig.add_axes([0.63, 0.55, 0.35, 0.37])
    ax_temp = fig.add_axes([0.63, 0.10, 0.35, 0.37])

    # Style helpers
    def style_ax(ax, title, ylabel, xlabel=None):
        ax.set_facecolor("#0f0f1a")
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#444466")
        ax.set_title(title, color="white", fontsize=9, pad=4)
        ax.set_ylabel(ylabel, color="#aaaacc", fontsize=8)
        if xlabel:
            ax.set_xlabel(xlabel, color="#aaaacc", fontsize=8)
        ax.grid(True, color="#222244", linewidth=0.5, alpha=0.8)

    # Map axis
    ax_map.set_facecolor("#0f0f1a")
    ax_map.tick_params(colors="white", labelsize=8)
    for spine in ax_map.spines.values():
        spine.set_edgecolor("#444466")
    ax_map.set_xlim(map_xlim)
    ax_map.set_ylim(map_ylim)
    ax_map.set_aspect("equal", adjustable="box")

    # Static: nodes
    ax_map.scatter(all_x, all_y, s=12, c="#8888bb", zorder=2, alpha=0.6)
    # Static: depots
    ax_map.scatter(
        depot_xs, depot_ys, s=220, c="gold", marker="*", zorder=6,
        edgecolors="white", linewidths=0.5,
    )

    # Score axes setup
    style_ax(ax_score, "Score", "Score")
    ax_score.set_xlim(0, total_iterations)
    ax_score.set_ylim(score_min, score_max)

    style_ax(ax_temp, "Temperature", "Temperature", xlabel="Iteration")
    ax_temp.set_xlim(0, total_iterations)
    ax_temp.set_ylim(0, max(temps) * 1.05)

    # ---- persistent line objects for score / temp ----
    (line_best_score,) = ax_score.plot([], [], color="#4fc3f7", lw=2, label="Best", zorder=4)
    (line_cand_score,) = ax_score.plot(
        [], [], color="#ffb74d", lw=1.2, linestyle="--", alpha=0.75, label="Candidate", zorder=3
    )
    vline_score = ax_score.axvline(0, color="#ff5555", lw=0.8, linestyle=":", zorder=5)
    ax_score.legend(
        loc="upper right", fontsize=8, facecolor="#1a1a2e",
        edgecolor="#444466", labelcolor="white",
    )

    (line_temp,) = ax_temp.plot([], [], color="#ef5350", lw=1.5, zorder=4)
    vline_temp = ax_temp.axvline(0, color="#ff5555", lw=0.8, linestyle=":", zorder=5)

    # Info text overlay on map
    info_text = ax_map.text(
        0.02, 0.98, "", transform=ax_map.transAxes,
        verticalalignment="top", fontsize=9, color="white",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1a1a2e", alpha=0.8, edgecolor="#444466"),
        zorder=10,
    )

    # Legend for routes (map)
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], color="white", lw=2, label="Best routes"),
        Line2D([0], [0], color="#888888", lw=1.5, linestyle="--", alpha=0.7, label="Candidate routes"),
        Line2D([0], [0], marker="*", color="gold", markersize=10, lw=0, label="Depot"),
    ]
    ax_map.legend(
        handles=legend_handles, loc="lower right", fontsize=8,
        facecolor="#1a1a2e", edgecolor="#444466", labelcolor="white",
    )

    # Mutable container for route artists (cleared each frame)
    route_artists = []

    def update(frame_idx):
        snap = snapshots[frame_idx]
        iter_num = snap["iteration"]

        # ---- clear previous route lines ----
        for artist in route_artists:
            artist.remove()
        route_artists.clear()

        # ---- candidate routes (dashed gray, behind) ----
        cand_arts = draw_routes(
            ax_map, snap["candidate_routes"], node_coords, depot_coords,
            colors=["#555577"] * 20, linestyle="--", lw=1.3, alpha=0.55, zorder=3,
        )
        route_artists.extend(cand_arts)

        # ---- best routes (solid, colored, on top) ----
        best_arts = draw_routes(
            ax_map, snap["best_routes"], node_coords, depot_coords,
            colors=route_colors, linestyle="-", lw=2.0, alpha=0.9, zorder=4,
        )
        route_artists.extend(best_arts)

        # ---- score graph ----
        x_data = iters[: frame_idx + 1]
        line_best_score.set_data(x_data, best_scores[: frame_idx + 1])
        line_cand_score.set_data(x_data, cand_scores[: frame_idx + 1])
        vline_score.set_xdata([iter_num, iter_num])

        # ---- temperature graph ----
        line_temp.set_data(x_data, temps[: frame_idx + 1])
        vline_temp.set_xdata([iter_num, iter_num])

        # ---- info text ----
        marker = " ★" if snap["best_updated"] else (" ✓" if snap["accepted"] else "")
        info_text.set_text(
            f"Iteration : {iter_num:>6}\n"
            f"Best      : {format_score(snap['best_score'])}\n"
            f"Candidate : {format_score(snap['candidate_score'])}\n"
            f"Temp      : {snap['temperature']:>8.2f}\n"
            f"Routes    : {len(snap['best_routes'])}{marker}"
        )

    # ---------------------------------------------------------------- animate
    n_frames = len(snapshots)
    print(f"Rendering {n_frames} frames at {args.fps} fps...")

    ani = animation.FuncAnimation(
        fig, update, frames=n_frames, interval=1000 // args.fps, blit=False
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".mp4":
        writer = animation.FFMpegWriter(fps=args.fps, bitrate=2000,
                                         extra_args=["-vcodec", "libx264"])
    else:
        writer = animation.PillowWriter(fps=args.fps)

    ani.save(str(output_path), writer=writer, dpi=args.dpi,
             savefig_kwargs={"facecolor": "#1a1a2e"})
    print(f"Animation saved to {output_path}")
    plt.close()


if __name__ == "__main__":
    main()
