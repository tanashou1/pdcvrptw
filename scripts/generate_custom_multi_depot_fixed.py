from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate custom multi-depot instances with vehicle-specific fixed tasks."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("instances/custom_multi_depot_fixed"),
    )
    return parser.parse_args()


def depot(depot_id: str, x: int, y: int) -> dict[str, Any]:
    return {
        "id": depot_id,
        "x": x,
        "y": y,
        "tw": {"start": 0, "end": 480},
    }


def vehicle(vehicle_id: str, depot_id: str) -> dict[str, Any]:
    return {
        "id": vehicle_id,
        "depot_id": depot_id,
    }


def task(
    node_id: str,
    x: int,
    y: int,
    start: int,
    end: int,
    service: int,
    *,
    demand: int = 1,
    required: bool = True,
    fixed_vehicle_id: str | None = None,
    label: str,
    home_depot_id: str,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "request_id": node_id,
        "kind": "pickup",
        "x": x,
        "y": y,
        "demand": demand,
        "service_duration": service,
        "tw": {"start": start, "end": end},
        "location_id": f"L_{node_id}",
        "time_window_label": label,
        "required": required,
        "fixed_vehicle_id": fixed_vehicle_id,
        "location_home_depot_id": home_depot_id,
    }


def build_instance(
    name: str,
    depots: list[dict[str, Any]],
    vehicles: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    vehicles_per_depot = Counter(vehicle["depot_id"] for vehicle in vehicles)
    time_window_distribution = Counter(node["time_window_label"] for node in nodes)
    location_catalog = [
        {
            "id": node["location_id"],
            "x": node["x"],
            "y": node["y"],
            "home_depot_id": node.pop("location_home_depot_id"),
        }
        for node in nodes
    ]

    return {
        "name": name,
        "seed": 0,
        "planning_horizon": {"start": 0, "end": 480},
        "capacity": 4,
        "vehicles_per_depot": dict(sorted(vehicles_per_depot.items())),
        "depots": depots,
        "vehicles": vehicles,
        "location_catalog": location_catalog,
        "nodes": nodes,
        "metadata": {
            "request_count": len(nodes),
            "node_count": len(nodes),
            "location_count": len(location_catalog),
            "vehicle_count": len(vehicles),
            "variant": "custom_multi_depot_fixed",
            "benchmark_group": "custom_multi_depot_fixed",
            "distance_metric": "euclidean_double",
            "load_profile": "zero_start",
            "objective_mode": "optional_then_vehicles_then_distance",
            "enforce_precedence": False,
            "time_window_distribution": dict(sorted(time_window_distribution.items())),
        },
    }


def instance_mdf101() -> dict[str, Any]:
    depots = [
        depot("D0", 40, 50),
        depot("D1", 10, 40),
        depot("D2", 20, 80),
    ]
    vehicles = [
        vehicle("D0_V00", "D0"),
        vehicle("D0_V01", "D0"),
        vehicle("D1_V00", "D1"),
        vehicle("D2_V00", "D2"),
    ]
    nodes = [
        task(
            "FX_D0_V00",
            46,
            58,
            200,
            200,
            20,
            demand=0,
            fixed_vehicle_id="D0_V00",
            label="fixed",
            home_depot_id="D0",
        ),
        task(
            "FX_D0_V01",
            34,
            60,
            190,
            190,
            20,
            demand=0,
            fixed_vehicle_id="D0_V01",
            label="fixed",
            home_depot_id="D0",
        ),
        task(
            "FX_D1_V00",
            8,
            48,
            205,
            205,
            20,
            demand=0,
            fixed_vehicle_id="D1_V00",
            label="fixed",
            home_depot_id="D1",
        ),
        task(
            "FX_D2_V00",
            18,
            88,
            210,
            210,
            20,
            demand=0,
            fixed_vehicle_id="D2_V00",
            label="fixed",
            home_depot_id="D2",
        ),
        task("C001", 45, 68, 90, 100, 10, required=False, label="morning", home_depot_id="D0"),
        task("C002", 35, 66, 90, 100, 10, required=False, label="morning", home_depot_id="D0"),
        task("C003", 8, 40, 90, 100, 10, required=False, label="morning", home_depot_id="D1"),
        task("C004", 5, 45, 90, 100, 10, required=False, label="morning", home_depot_id="D1"),
        task("C005", 22, 85, 90, 100, 10, required=False, label="morning", home_depot_id="D2"),
        task("C006", 15, 75, 90, 100, 10, required=False, label="morning", home_depot_id="D2"),
        task("C007", 30, 52, 280, 300, 10, required=False, label="afternoon", home_depot_id="D0"),
        task("C008", 2, 40, 280, 300, 10, required=False, label="afternoon", home_depot_id="D1"),
        task("C009", 25, 55, 280, 300, 10, required=False, label="afternoon", home_depot_id="D0"),
        task("C010", 20, 50, 280, 300, 10, required=False, label="afternoon", home_depot_id="D2"),
    ]
    return build_instance("mdf101", depots, vehicles, nodes)


def instance_mdf102() -> dict[str, Any]:
    depots = [
        depot("D0", 40, 50),
        depot("D1", 10, 40),
    ]
    vehicles = [
        vehicle("D0_V00", "D0"),
        vehicle("D0_V01", "D0"),
        vehicle("D1_V00", "D1"),
        vehicle("D1_V01", "D1"),
    ]
    nodes = [
        task(
            "FX_D0_V00",
            45,
            60,
            170,
            170,
            20,
            demand=0,
            fixed_vehicle_id="D0_V00",
            label="fixed",
            home_depot_id="D0",
        ),
        task(
            "FX_D0_V01",
            38,
            64,
            220,
            220,
            20,
            demand=0,
            fixed_vehicle_id="D0_V01",
            label="fixed",
            home_depot_id="D0",
        ),
        task(
            "FX_D1_V00",
            8,
            52,
            175,
            175,
            20,
            demand=0,
            fixed_vehicle_id="D1_V00",
            label="fixed",
            home_depot_id="D1",
        ),
        task(
            "FX_D1_V01",
            6,
            48,
            225,
            225,
            20,
            demand=0,
            fixed_vehicle_id="D1_V01",
            label="fixed",
            home_depot_id="D1",
        ),
        task("C101", 44, 66, 120, 130, 10, required=False, label="midday", home_depot_id="D0"),
        task("C102", 42, 68, 120, 130, 10, required=False, label="midday", home_depot_id="D0"),
        task("C103", 10, 35, 120, 130, 10, required=False, label="midday", home_depot_id="D1"),
        task("C104", 6, 44, 120, 130, 10, required=False, label="midday", home_depot_id="D1"),
        task("C105", 18, 76, 120, 130, 10, required=False, label="midday", home_depot_id="D1"),
        task("C106", 25, 52, 295, 320, 10, required=False, label="evening", home_depot_id="D0"),
        task("C107", 20, 55, 295, 320, 10, required=False, label="evening", home_depot_id="D0"),
        task("C108", 5, 35, 295, 320, 10, required=False, label="evening", home_depot_id="D1"),
        task("C109", 0, 40, 295, 320, 10, required=False, label="evening", home_depot_id="D1"),
    ]
    return build_instance("mdf102", depots, vehicles, nodes)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    instances = [instance_mdf101(), instance_mdf102()]
    manifest = []
    for instance in instances:
        path = args.output_dir / f"instance_{instance['name']}.json"
        write_json(path, instance)
        manifest.append({"name": instance["name"], "instance_path": str(path)})

    write_json(args.output_dir / "manifest.json", {"instances": manifest})
    print(f"Generated {len(instances)} custom instances in {args.output_dir}")


if __name__ == "__main__":
    main()
