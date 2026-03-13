from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

DAY_START = 8 * 60
DAY_END = 18 * 60


def load_json(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(data: Any, path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str], path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def euclidean_int(frm: dict[str, Any], to: dict[str, Any]) -> int:
    dx = float(frm["x"]) - float(to["x"])
    dy = float(frm["y"]) - float(to["y"])
    return int(math.floor(math.hypot(dx, dy) + 0.5))


def time_window_from_label(label: str) -> dict[str, int]:
    if label == "morning":
        return {"start": DAY_START, "end": 13 * 60}

    if label == "afternoon":
        return {"start": 13 * 60, "end": DAY_END}

    return {"start": DAY_START, "end": DAY_END}


def depot_index(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {depot["id"]: depot for depot in instance["depots"]}


def node_index(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in instance["nodes"]}


def route_blueprint(depot_id: str, node_ids: list[str]) -> dict[str, Any]:
    return {"depot_id": depot_id, "node_ids": list(node_ids)}


def evaluate_route(
    instance: dict[str, Any],
    depot_id: str,
    node_ids: list[str],
) -> dict[str, Any]:
    depots = depot_index(instance)
    nodes = node_index(instance)
    depot = depots[depot_id]
    route_nodes = [nodes[node_id] for node_id in node_ids]

    start_load = sum(-min(int(node["demand"]), 0) for node in route_nodes)
    current_load = start_load
    max_load = start_load
    current_time = int(depot["tw"]["start"])
    distance = 0
    feasible = start_load <= int(instance["capacity"])
    violations: list[str] = []

    if not feasible:
        violations.append(f"{depot_id}:initial_capacity")

    previous = depot
    stops: list[dict[str, Any]] = []

    for node in route_nodes:
        travel = euclidean_int(previous, node)
        arrival = current_time + travel
        start_service = max(arrival, int(node["tw"]["start"]))
        wait_duration = start_service - arrival

        if start_service > int(node["tw"]["end"]):
            feasible = False
            violations.append(f"{node['id']}:time_window")

        current_load += int(node["demand"])
        max_load = max(max_load, current_load)

        if current_load < 0 or current_load > int(instance["capacity"]):
            feasible = False
            violations.append(f"{node['id']}:capacity")

        departure = start_service + int(node["service_duration"])
        distance += travel
        stops.append(
            {
                "node_id": node["id"],
                "arrival": arrival,
                "start_service": start_service,
                "departure": departure,
                "wait_duration": wait_duration,
                "load_after_service": current_load,
            }
        )

        current_time = departure
        previous = node

    return_to_depot = euclidean_int(previous, depot)
    distance += return_to_depot
    end_time = current_time + return_to_depot

    if end_time > int(depot["tw"]["end"]):
        feasible = False
        violations.append(f"{depot_id}:depot_close")

    return {
        "depot_id": depot_id,
        "node_ids": list(node_ids),
        "distance": distance,
        "start_load": start_load,
        "max_load": max_load,
        "end_time": end_time,
        "feasible": feasible,
        "violations": sorted(set(violations)),
        "stops": stops,
    }


def evaluate_solution(
    instance: dict[str, Any],
    routes: list[dict[str, Any]],
) -> dict[str, Any]:
    visit_counts = {node["id"]: 0 for node in instance["nodes"]}
    route_metrics: list[dict[str, Any]] = []
    objective = 0
    feasible = True
    vehicle_usage = {depot["id"]: 0 for depot in instance["depots"]}

    for route in routes:
        depot_id = route["depot_id"]
        node_ids = list(route["node_ids"])
        vehicle_usage[depot_id] = vehicle_usage.get(depot_id, 0) + 1

        metrics = evaluate_route(instance, depot_id, node_ids)
        route_metrics.append(metrics)
        objective += int(metrics["distance"])
        feasible = feasible and bool(metrics["feasible"])

        for node_id in node_ids:
            if node_id not in visit_counts:
                feasible = False
                continue

            visit_counts[node_id] += 1

    duplicates = sorted(node_id for node_id, count in visit_counts.items() if count > 1)
    missing = sorted(node_id for node_id, count in visit_counts.items() if count == 0)

    vehicle_violations: list[str] = []
    for depot_id, used_count in vehicle_usage.items():
        limit = int(instance["vehicles_per_depot"][depot_id])
        if used_count > limit:
            vehicle_violations.append(f"{depot_id}:{used_count}>{limit}")

    feasible = feasible and not duplicates and not missing and not vehicle_violations

    return {
        "objective": objective,
        "total_distance": objective,
        "route_count": len(routes),
        "visited_nodes": sum(len(route["node_ids"]) for route in routes),
        "unique_served_nodes": sum(1 for count in visit_counts.values() if count > 0),
        "feasible": feasible,
        "duplicate_nodes": duplicates,
        "missing_nodes": missing,
        "vehicle_usage": vehicle_usage,
        "vehicle_violations": vehicle_violations,
        "routes": route_metrics,
    }
