from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import ortools
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from common import (
    HIERARCHICAL_OBJECTIVE_SCALE,
    evaluate_solution,
    load_json,
    route_blueprint,
    save_json,
    travel_distance,
)


FIRST_SOLUTION_STRATEGY = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
LOCAL_SEARCH_METAHEURISTIC = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve Li-Lim 100-case instances with OR-Tools.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances/li_lim_100"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/li_lim_100/ortools"))
    parser.add_argument("--time-limit-seconds", type=float, default=5.0)
    parser.add_argument("--time-scale", type=int, default=100)
    parser.add_argument(
        "--vehicle-fixed-cost",
        type=int,
        default=int(HIERARCHICAL_OBJECTIVE_SCALE * 100),
    )
    return parser.parse_args()


def scaled_int(value: float, scale: int) -> int:
    return int(round(value * scale))


def scaled_float(value: int | float, scale: int) -> float:
    return round(float(value) / scale, 6)


def build_request_pairs(instance: dict[str, Any]) -> list[tuple[str, int, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for location_index, node in enumerate(instance["nodes"], start=1):
        request_nodes = grouped.setdefault(node["request_id"], {})
        if node["kind"] in request_nodes:
            raise ValueError(
                f"Request {node['request_id']} has duplicate {node['kind']} nodes."
            )

        request_nodes[node["kind"]] = location_index

    pairs: list[tuple[str, int, int]] = []
    for request_id, pair in grouped.items():
        pickup_index = pair.get("pickup")
        delivery_index = pair.get("delivery")
        if pickup_index is None or delivery_index is None:
            raise ValueError(f"Request {request_id} is missing a pickup or delivery node.")
        pairs.append((request_id, pickup_index, delivery_index))

    return pairs


def build_scaled_data(
    instance: dict[str, Any],
    time_scale: int,
) -> tuple[list[list[int]], list[int], list[tuple[int, int]], list[int], int, str]:
    depot = instance["depots"][0]
    locations = [depot] + instance["nodes"]
    distance_matrix = [
        [scaled_int(travel_distance(instance, frm, to), time_scale) for to in locations]
        for frm in locations
    ]
    service_times = [0] + [scaled_int(float(node["service_duration"]), time_scale) for node in instance["nodes"]]
    time_windows = [
        (scaled_int(float(location["tw"]["start"]), time_scale), scaled_int(float(location["tw"]["end"]), time_scale))
        for location in locations
    ]
    demands = [0] + [int(node["demand"]) for node in instance["nodes"]]
    vehicle_count = int(instance["vehicles_per_depot"][depot["id"]])
    return distance_matrix, service_times, time_windows, demands, vehicle_count, depot["id"]


def build_routing_model(
    instance: dict[str, Any],
    time_scale: int,
    vehicle_fixed_cost: int,
) -> tuple[pywrapcp.RoutingIndexManager, pywrapcp.RoutingModel, Any, list[list[int]], list[int], str]:
    (
        distance_matrix,
        service_times,
        time_windows,
        demands,
        vehicle_count,
        depot_id,
    ) = build_scaled_data(instance, time_scale)

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), vehicle_count, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

    def demand_callback(from_index: int) -> int:
        return demands[manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [int(instance["capacity"])] * vehicle_count,
        True,
        "Capacity",
    )

    def time_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return service_times[from_node] + distance_matrix[from_node][to_node]

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    time_horizon = scaled_int(float(instance["planning_horizon"]["end"] - instance["planning_horizon"]["start"]), time_scale)
    routing.AddDimension(
        time_callback_index,
        time_horizon,
        time_horizon,
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")

    for node_index, window in enumerate(time_windows):
        time_var = time_dimension.CumulVar(manager.NodeToIndex(node_index))
        time_var.SetRange(window[0], window[1])

    for vehicle_id in range(vehicle_count):
        routing.SetFixedCostOfVehicle(vehicle_fixed_cost, vehicle_id)
        start_index = routing.Start(vehicle_id)
        end_index = routing.End(vehicle_id)
        depot_window = time_windows[0]
        time_dimension.CumulVar(start_index).SetRange(depot_window[0], depot_window[1])
        time_dimension.CumulVar(end_index).SetRange(depot_window[0], depot_window[1])
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(start_index))
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(end_index))

    solver = routing.solver()
    for _request_id, pickup_node, delivery_node in build_request_pairs(instance):
        pickup_index = manager.NodeToIndex(pickup_node)
        delivery_index = manager.NodeToIndex(delivery_node)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        solver.Add(routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index))
        solver.Add(time_dimension.CumulVar(pickup_index) <= time_dimension.CumulVar(delivery_index))

    return manager, routing, time_dimension, distance_matrix, service_times, depot_id


def extract_routes(
    instance: dict[str, Any],
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    time_dimension: Any,
    distance_matrix: list[list[int]],
    service_times: list[int],
    depot_id: str,
    solution: Any,
    time_scale: int,
) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []

    for vehicle_id in range(routing.vehicles()):
        start_index = routing.Start(vehicle_id)
        first_index = solution.Value(routing.NextVar(start_index))
        if routing.IsEnd(first_index):
            continue

        route_node_ids: list[str] = []
        schedule: list[dict[str, Any]] = []
        route_distance = 0
        route_start_time = solution.Value(time_dimension.CumulVar(start_index))
        previous_departure = route_start_time
        current_index = start_index

        while True:
            next_index = solution.Value(routing.NextVar(current_index))
            from_node = manager.IndexToNode(current_index)
            to_node = manager.IndexToNode(next_index)
            route_distance += distance_matrix[from_node][to_node]

            if routing.IsEnd(next_index):
                route_end_time = solution.Value(time_dimension.CumulVar(next_index))
                break

            node = instance["nodes"][to_node - 1]
            start_service = solution.Value(time_dimension.CumulVar(next_index))
            arrival = previous_departure + distance_matrix[from_node][to_node]
            wait_duration = start_service - arrival
            end_service = start_service + service_times[to_node]
            route_node_ids.append(node["id"])
            schedule.append(
                {
                    "node_id": node["id"],
                    "start_service": scaled_float(start_service, time_scale),
                    "end_service": scaled_float(end_service, time_scale),
                    "wait_duration": scaled_float(wait_duration, time_scale),
                    "time_warp": 0.0,
                }
            )
            previous_departure = end_service
            current_index = next_index

        routes.append(
            {
                "route_index": len(routes),
                "depot_id": depot_id,
                "node_ids": route_node_ids,
                "reported_distance": scaled_float(route_distance, time_scale),
                "reported_duration": scaled_float(route_end_time - route_start_time, time_scale),
                "reported_start_time": scaled_float(route_start_time, time_scale),
                "reported_end_time": scaled_float(route_end_time, time_scale),
                "schedule": schedule,
            }
        )

    return routes


def solve_instance(
    instance: dict[str, Any],
    time_limit_seconds: float,
    time_scale: int,
    vehicle_fixed_cost: int,
) -> dict[str, Any]:
    (
        manager,
        routing,
        time_dimension,
        distance_matrix,
        service_times,
        depot_id,
    ) = build_routing_model(instance, time_scale, vehicle_fixed_cost)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = FIRST_SOLUTION_STRATEGY
    search_parameters.local_search_metaheuristic = LOCAL_SEARCH_METAHEURISTIC
    search_parameters.time_limit.FromMilliseconds(max(1, int(round(time_limit_seconds * 1000))))
    search_parameters.log_search = False
    search_parameters.use_full_propagation = True

    started_at = time.perf_counter()
    solution = routing.SolveWithParameters(search_parameters)
    runtime_seconds = time.perf_counter() - started_at

    if solution is None:
        evaluation = evaluate_solution(instance, [])
        return {
            "instance": instance["name"],
            "solver": "ortools",
            "solver_version": ortools.__version__,
            "model_note": "Strict OR-Tools RoutingModel with pickup-delivery, precedence, capacity, and time windows.",
            "runtime_seconds": runtime_seconds,
            "time_scale": time_scale,
            "reported_cost": None,
            "reported_feasible": False,
            "route_count": 0,
            "routes": [],
            "evaluation": evaluation,
        }

    routes = extract_routes(
        instance,
        manager,
        routing,
        time_dimension,
        distance_matrix,
        service_times,
        depot_id,
        solution,
        time_scale,
    )
    evaluation = evaluate_solution(
        instance,
        [route_blueprint(route["depot_id"], route["node_ids"]) for route in routes],
    )

    return {
        "instance": instance["name"],
        "solver": "ortools",
        "solver_version": ortools.__version__,
        "model_note": "Strict OR-Tools RoutingModel with pickup-delivery, precedence, capacity, and time windows.",
        "runtime_seconds": runtime_seconds,
        "time_scale": time_scale,
        "reported_cost": int(solution.ObjectiveValue()),
        "reported_feasible": True,
        "route_count": len(routes),
        "routes": routes,
        "evaluation": evaluation,
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    for instance_path in sorted(args.instances_dir.glob("instance_*.json")):
        instance = load_json(instance_path)
        solution = solve_instance(
            instance,
            args.time_limit_seconds,
            args.time_scale,
            args.vehicle_fixed_cost,
        )
        save_json(solution, args.output_dir / f"{instance['name']}.solution.json")

        summary.append(
            {
                "instance": instance["name"],
                "reported_feasible": bool(solution["reported_feasible"]),
                "strict_feasible": bool(solution["evaluation"]["feasible"]),
                "route_count": solution["evaluation"]["route_count"],
                "comparison_distance": solution["evaluation"]["comparison_distance"],
                "runtime_seconds": round(solution["runtime_seconds"], 3),
            }
        )
        print(
            f"[ortools] {instance['name']}: "
            f"reported_feasible={solution['reported_feasible']} "
            f"strict_feasible={solution['evaluation']['feasible']} "
            f"routes={solution['evaluation']['route_count']} "
            f"distance={solution['evaluation']['comparison_distance']:.2f}"
        )

    save_json({"solutions": summary}, args.output_dir / "summary.json")


if __name__ == "__main__":
    main()
