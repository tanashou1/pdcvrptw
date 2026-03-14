from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Any

from common import DAY_END, DAY_START, save_json, time_window_from_label

DEPOT_LAYOUT = (
    ("D0", 15, 15),
    ("D1", 85, 15),
    ("D2", 50, 85),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate benchmark instances.")
    parser.add_argument("--output-dir", type=Path, default=Path("instances"))
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--request-count", type=int, default=50)
    parser.add_argument("--location-count", type=int, default=20)
    parser.add_argument("--vehicle-count", type=int, default=18)
    parser.add_argument("--base-seed", type=int, default=2026031300)
    return parser.parse_args()


def weighted_label(rng: random.Random) -> str:
    label = rng.choices(
        population=["none", "morning", "afternoon"],
        weights=[72, 14, 14],
        k=1,
    )[0]
    return str(label)


def build_depots() -> list[dict[str, Any]]:
    return [
        {
            "id": depot_id,
            "x": x,
            "y": y,
            "tw": {"start": DAY_START, "end": DAY_END},
        }
        for depot_id, x, y in DEPOT_LAYOUT
    ]


def build_location_catalog(
    rng: random.Random,
    depots: list[dict[str, Any]],
    location_count: int,
) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    used_positions = {(depot["x"], depot["y"]) for depot in depots}

    for location_idx in range(location_count):
        home_depot = depots[location_idx % len(depots)]

        while True:
            x = max(0, min(100, int(round(rng.gauss(home_depot["x"], 12)))))
            y = max(0, min(100, int(round(rng.gauss(home_depot["y"], 12)))))

            if (x, y) not in used_positions:
                used_positions.add((x, y))
                break

        catalog.append(
            {
                "id": f"L{location_idx:02d}",
                "x": x,
                "y": y,
                "home_depot_id": home_depot["id"],
            }
        )

    return catalog


def split_vehicle_count(total_vehicles: int, depots: list[dict[str, Any]]) -> dict[str, int]:
    base, remainder = divmod(total_vehicles, len(depots))
    allocation: dict[str, int] = {}

    for depot_idx, depot in enumerate(depots):
        allocation[depot["id"]] = base + (1 if depot_idx < remainder else 0)

    return allocation


def build_node(
    node_id: str,
    request_id: str,
    kind: str,
    location: dict[str, Any],
    demand: int,
    service_duration: int,
    time_window_label: str,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "request_id": request_id,
        "kind": kind,
        "x": location["x"],
        "y": location["y"],
        "demand": demand,
        "service_duration": service_duration,
        "tw": time_window_from_label(time_window_label),
        "location_id": location["id"],
        "time_window_label": time_window_label,
    }


def generate_instance(
    instance_idx: int,
    request_count: int,
    location_count: int,
    vehicle_count: int,
    base_seed: int,
) -> dict[str, Any]:
    seed = base_seed + instance_idx
    rng = random.Random(seed)
    depots = build_depots()
    location_catalog = build_location_catalog(rng, depots, location_count)
    vehicles_per_depot = split_vehicle_count(vehicle_count, depots)

    nodes: list[dict[str, Any]] = []
    time_window_counts = {"none": 0, "morning": 0, "afternoon": 0}

    for request_idx in range(request_count):
        request_id = f"R{request_idx:03d}"
        pickup_location = rng.choice(location_catalog)

        if rng.random() < 0.7:
            sibling_pool = [
                location
                for location in location_catalog
                if location["home_depot_id"] == pickup_location["home_depot_id"]
            ]
            delivery_location = rng.choice(sibling_pool)
        else:
            delivery_location = rng.choice(location_catalog)

        pickup_label = weighted_label(rng)
        delivery_label = weighted_label(rng)
        time_window_counts[pickup_label] += 1
        time_window_counts[delivery_label] += 1

        pickup_duration = rng.randint(5, 12)
        delivery_duration = rng.randint(5, 12)

        nodes.append(
            build_node(
                node_id=f"P{request_idx:03d}",
                request_id=request_id,
                kind="pickup",
                location=pickup_location,
                demand=1,
                service_duration=pickup_duration,
                time_window_label=pickup_label,
            )
        )
        nodes.append(
            build_node(
                node_id=f"D{request_idx:03d}",
                request_id=request_id,
                kind="delivery",
                location=delivery_location,
                demand=-1,
                service_duration=delivery_duration,
                time_window_label=delivery_label,
            )
        )

    return {
        "name": f"instance_{instance_idx:02d}",
        "seed": seed,
        "planning_horizon": {"start": DAY_START, "end": DAY_END},
        "capacity": 6,
        "vehicles_per_depot": vehicles_per_depot,
        "depots": depots,
        "location_catalog": location_catalog,
        "nodes": nodes,
        "metadata": {
            "request_count": request_count,
            "node_count": len(nodes),
            "location_count": location_count,
            "vehicle_count": vehicle_count,
            "variant": "multi_depot_signed_demand_pdcvrptw",
            "benchmark_group": "synthetic",
            "distance_metric": "euclidean_int_half_up",
            "load_profile": "balanced_start",
            "objective_mode": "distance_only",
            "enforce_precedence": False,
            "time_window_distribution": time_window_counts,
        },
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for instance_idx in range(1, args.count + 1):
        instance = generate_instance(
            instance_idx=instance_idx,
            request_count=args.request_count,
            location_count=args.location_count,
            vehicle_count=args.vehicle_count,
            base_seed=args.base_seed,
        )
        output_path = args.output_dir / f"{instance['name']}.json"
        save_json(instance, output_path)
        manifest.append(
            {
                "name": instance["name"],
                "seed": instance["seed"],
                "node_count": instance["metadata"]["node_count"],
                "vehicle_count": instance["metadata"]["vehicle_count"],
            }
        )

    save_json({"instances": manifest}, args.output_dir / "manifest.json")
    print(f"Generated {len(manifest)} instances in {args.output_dir}")


if __name__ == "__main__":
    main()
