from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

DAY_START = 8 * 60
DAY_END = 18 * 60
HIERARCHICAL_OBJECTIVE_SCALE = 1_000_000.0


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


def metadata(instance: dict[str, Any]) -> dict[str, Any]:
    return dict(instance.get("metadata", {}))


def distance_metric(instance: dict[str, Any]) -> str:
    return str(metadata(instance).get("distance_metric", "euclidean_int_half_up"))


def load_profile(instance: dict[str, Any]) -> str:
    return str(metadata(instance).get("load_profile", "balanced_start"))


def objective_mode(instance: dict[str, Any]) -> str:
    return str(metadata(instance).get("objective_mode", "distance_only"))


def enforce_precedence(instance: dict[str, Any]) -> bool:
    return bool(metadata(instance).get("enforce_precedence", False))


def serialise_distance(instance: dict[str, Any], value: float) -> float | int:
    if distance_metric(instance) == "euclidean_double":
        return round(value, 6)

    return int(round(value))


def comparison_distance(instance: dict[str, Any], value: float) -> float | int:
    if distance_metric(instance) == "euclidean_double":
        return round(value, 2)

    return int(round(value))


def serialise_time(instance: dict[str, Any], value: float) -> float | int:
    if distance_metric(instance) == "euclidean_double":
        return round(value, 6)

    return int(round(value))


def euclidean_int(frm: dict[str, Any], to: dict[str, Any]) -> int:
    dx = float(frm["x"]) - float(to["x"])
    dy = float(frm["y"]) - float(to["y"])
    return int(math.floor(math.hypot(dx, dy) + 0.5))


def travel_distance(instance: dict[str, Any], frm: dict[str, Any], to: dict[str, Any]) -> float:
    if distance_metric(instance) == "euclidean_double":
        dx = float(frm["x"]) - float(to["x"])
        dy = float(frm["y"]) - float(to["y"])
        return math.hypot(dx, dy)

    return float(euclidean_int(frm, to))


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


def node_by_source_index(instance: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(node["source_index"]): node
        for node in instance["nodes"]
        if "source_index" in node and node["source_index"] is not None
    }


def route_blueprint(depot_id: str, node_ids: list[str]) -> dict[str, Any]:
    return {"depot_id": depot_id, "node_ids": list(node_ids)}


def route_precedence_violations(route_nodes: list[dict[str, Any]]) -> list[str]:
    request_positions: dict[str, dict[str, int]] = {}

    for position, node in enumerate(route_nodes):
        current = request_positions.setdefault(node["request_id"], {})
        current[node["kind"]] = position

    violations: list[str] = []
    for request_id, placement in request_positions.items():
        pickup_position = placement.get("pickup")
        delivery_position = placement.get("delivery")

        if pickup_position is None or delivery_position is None:
            violations.append(f"{request_id}:pair_split")
            continue

        if pickup_position >= delivery_position:
            violations.append(f"{request_id}:precedence")

    return sorted(violations)


def start_load_for_route(instance: dict[str, Any], route_nodes: list[dict[str, Any]]) -> int:
    if load_profile(instance) == "zero_start":
        return 0

    return sum(-min(int(node["demand"]), 0) for node in route_nodes)


def search_objective(route_count: int, total_distance: float, mode: str) -> float:
    if mode == "vehicles_then_distance":
        return route_count * HIERARCHICAL_OBJECTIVE_SCALE + total_distance

    return total_distance


def evaluate_route(
    instance: dict[str, Any],
    depot_id: str,
    node_ids: list[str],
) -> dict[str, Any]:
    depots = depot_index(instance)
    nodes = node_index(instance)
    depot = depots[depot_id]
    route_nodes = [nodes[node_id] for node_id in node_ids]

    start_load = start_load_for_route(instance, route_nodes)
    current_load = start_load
    max_load = start_load
    current_time = float(depot["tw"]["start"])
    distance = 0.0
    feasible = start_load <= int(instance["capacity"])
    violations: list[str] = []
    precedence_violations: list[str] = []

    if not feasible:
        violations.append(f"{depot_id}:initial_capacity")

    if enforce_precedence(instance):
        precedence_violations = route_precedence_violations(route_nodes)
        if precedence_violations:
            feasible = False
            violations.extend(precedence_violations)

    previous = depot
    stops: list[dict[str, Any]] = []

    for node in route_nodes:
        travel = travel_distance(instance, previous, node)
        arrival = current_time + travel
        start_service = max(arrival, float(node["tw"]["start"]))
        wait_duration = start_service - arrival

        if start_service > float(node["tw"]["end"]):
            feasible = False
            violations.append(f"{node['id']}:time_window")

        current_load += int(node["demand"])
        max_load = max(max_load, current_load)

        if current_load < 0 or current_load > int(instance["capacity"]):
            feasible = False
            violations.append(f"{node['id']}:capacity")

        departure = start_service + float(node["service_duration"])
        distance += travel
        stops.append(
            {
                "node_id": node["id"],
                "arrival": serialise_time(instance, arrival),
                "start_service": serialise_time(instance, start_service),
                "departure": serialise_time(instance, departure),
                "wait_duration": serialise_time(instance, wait_duration),
                "load_after_service": current_load,
            }
        )

        current_time = departure
        previous = node

    return_to_depot = travel_distance(instance, previous, depot)
    distance += return_to_depot
    end_time = current_time + return_to_depot

    if end_time > float(depot["tw"]["end"]):
        feasible = False
        violations.append(f"{depot_id}:depot_close")

    return {
        "depot_id": depot_id,
        "node_ids": list(node_ids),
        "distance": serialise_distance(instance, distance),
        "comparison_distance": comparison_distance(instance, distance),
        "start_load": start_load,
        "max_load": max_load,
        "end_time": serialise_time(instance, end_time),
        "feasible": feasible,
        "violations": sorted(set(violations)),
        "precedence_violations": precedence_violations,
        "stops": stops,
    }


def evaluate_solution(
    instance: dict[str, Any],
    routes: list[dict[str, Any]],
) -> dict[str, Any]:
    visit_counts = {node["id"]: 0 for node in instance["nodes"]}
    route_metrics: list[dict[str, Any]] = []
    total_distance = 0.0
    feasible = True
    vehicle_usage = {depot["id"]: 0 for depot in instance["depots"]}
    precedence_violations: list[str] = []

    for route in routes:
        depot_id = route["depot_id"]
        node_ids = list(route["node_ids"])
        vehicle_usage[depot_id] = vehicle_usage.get(depot_id, 0) + 1

        metrics = evaluate_route(instance, depot_id, node_ids)
        route_metrics.append(metrics)
        total_distance += float(metrics["distance"])
        feasible = feasible and bool(metrics["feasible"])
        precedence_violations.extend(metrics["precedence_violations"])

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
    feasible = feasible and not precedence_violations

    mode = objective_mode(instance)
    comparison_total = comparison_distance(instance, total_distance)

    return {
        "objective": comparison_total,
        "search_objective": search_objective(len(routes), total_distance, mode),
        "total_distance": serialise_distance(instance, total_distance),
        "comparison_distance": comparison_total,
        "route_count": len(routes),
        "objective_mode": mode,
        "visited_nodes": sum(len(route["node_ids"]) for route in routes),
        "unique_served_nodes": sum(1 for count in visit_counts.values() if count > 0),
        "feasible": feasible,
        "duplicate_nodes": duplicates,
        "missing_nodes": missing,
        "precedence_violations": sorted(set(precedence_violations)),
        "vehicle_usage": vehicle_usage,
        "vehicle_violations": vehicle_violations,
        "routes": route_metrics,
    }
