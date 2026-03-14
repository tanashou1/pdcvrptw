from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import evaluate_solution, node_by_source_index, route_blueprint, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Li-Lim 100-case benchmark instances.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("instances/li_lim_100"))
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("results/li_lim_100/reference"),
    )
    return parser.parse_args()


def parse_raw_rows(path: Path) -> list[list[int]]:
    return [
        [int(token) for token in line.split()]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def request_id_for_row(task_id: int, pickup_sibling: int, delivery_sibling: int) -> str:
    if pickup_sibling == 0:
        return f"R{task_id:03d}"

    if delivery_sibling == 0:
        return f"R{pickup_sibling:03d}"

    raise ValueError(f"Task {task_id} does not encode a valid pickup-delivery pair.")


def looks_like_instance_file(path: Path) -> bool:
    first_line = path.read_text(encoding="utf-8").splitlines()[0].strip()
    return bool(first_line) and first_line[0].isdigit()


def convert_instance(raw_instance_path: Path) -> dict[str, Any]:
    rows = parse_raw_rows(raw_instance_path)
    vehicle_count, capacity, _speed = rows[0]
    depot_row = rows[1]
    task_rows = rows[2:]

    depot = {
        "id": "D0",
        "x": depot_row[1],
        "y": depot_row[2],
        "tw": {"start": depot_row[4], "end": depot_row[5]},
    }

    nodes: list[dict[str, Any]] = []
    location_catalog: list[dict[str, Any]] = []
    request_count = 0

    for row in task_rows:
        (
            task_id,
            x,
            y,
            demand,
            earliest,
            latest,
            service_duration,
            pickup_sibling,
            delivery_sibling,
        ) = row

        kind = "pickup" if pickup_sibling == 0 else "delivery"
        request_id = request_id_for_row(task_id, pickup_sibling, delivery_sibling)
        if kind == "pickup":
            request_count += 1

        location_id = f"L{task_id:03d}"
        location_catalog.append(
            {
                "id": location_id,
                "x": x,
                "y": y,
                "home_depot_id": "D0",
            }
        )
        nodes.append(
            {
                "id": f"T{task_id:03d}",
                "request_id": request_id,
                "kind": kind,
                "x": x,
                "y": y,
                "demand": demand,
                "service_duration": service_duration,
                "tw": {"start": earliest, "end": latest},
                "location_id": location_id,
                "time_window_label": "benchmark",
                "source_index": task_id,
                "sibling_source_index": delivery_sibling if kind == "pickup" else pickup_sibling,
            }
        )

    instance_code = raw_instance_path.stem.lower()
    return {
        "name": instance_code,
        "seed": 0,
        "planning_horizon": {"start": depot_row[4], "end": depot_row[5]},
        "capacity": capacity,
        "vehicles_per_depot": {"D0": vehicle_count},
        "depots": [depot],
        "location_catalog": location_catalog,
        "nodes": nodes,
        "metadata": {
            "request_count": request_count,
            "node_count": len(nodes),
            "location_count": len(location_catalog),
            "vehicle_count": vehicle_count,
            "variant": "li_lim_pdptw",
            "benchmark_group": "li_lim_100",
            "distance_metric": "euclidean_double",
            "load_profile": "zero_start",
            "objective_mode": "vehicles_then_distance",
            "enforce_precedence": True,
            "time_window_distribution": {"benchmark": len(nodes)},
        },
    }


def parse_reference_routes(instance: dict[str, Any], reference_path: Path) -> list[dict[str, Any]]:
    source_lookup = node_by_source_index(instance)
    routes = []

    for line in reference_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("Route "):
            continue

        task_ids = [int(token) for token in stripped.split(":", 1)[1].split()]
        node_ids = [source_lookup[task_id]["id"] for task_id in task_ids]
        routes.append(route_blueprint("D0", node_ids))

    return routes


def build_reference_solution(instance: dict[str, Any], reference_path: Path) -> dict[str, Any]:
    routes = parse_reference_routes(instance, reference_path)
    evaluation = evaluate_solution(instance, routes)

    return {
        "instance": instance["name"],
        "solver": "li-lim-reference",
        "source_file": reference_path.name,
        "route_count": len(routes),
        "routes": [
            {
                "route_index": route_index,
                "depot_id": route["depot_id"],
                "node_ids": route["node_ids"],
            }
            for route_index, route in enumerate(routes)
        ],
        "evaluation": evaluation,
    }


def main() -> None:
    args = parse_args()
    if not args.source_dir.exists() or not args.source_dir.is_dir():
        raise SystemExit(f"Li-Lim source directory does not exist: {args.source_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.reference_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    raw_instance_paths = [
        path for path in sorted(args.source_dir.glob("*")) if path.is_file() and looks_like_instance_file(path)
    ]
    if not raw_instance_paths:
        raise SystemExit(f"No raw Li-Lim instance files found in {args.source_dir}")

    for raw_instance_path in raw_instance_paths:
        instance = convert_instance(raw_instance_path)
        instance_path = args.output_dir / f"instance_{instance['name']}.json"
        save_json(instance, instance_path)

        reference_path = args.source_dir / f"{instance['name']}.sol"
        if reference_path.exists():
            reference_solution = build_reference_solution(instance, reference_path)
            save_json(
                reference_solution,
                args.reference_dir / f"{instance['name']}.solution.json",
            )

        manifest.append(
            {
                "name": instance["name"],
                "instance_path": str(instance_path),
                "reference_available": reference_path.exists(),
            }
        )

    save_json({"instances": manifest}, args.output_dir / "manifest.json")
    print(f"Imported {len(manifest)} Li-Lim 100-case instances into {args.output_dir}")


if __name__ == "__main__":
    main()
