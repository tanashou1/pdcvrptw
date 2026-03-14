from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from pyvrp import Model
from pyvrp.stop import MaxRuntime

from common import HIERARCHICAL_OBJECTIVE_SCALE, evaluate_solution, load_json, route_blueprint, save_json, travel_distance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve Li-Lim 100-case instances with a relaxed PyVRP model.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances/li_lim_100"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/li_lim_100/pyvrp"))
    parser.add_argument("--runtime-limit", type=float, default=2.5)
    parser.add_argument("--seed-offset", type=int, default=211)
    parser.add_argument("--time-scale", type=int, default=100)
    parser.add_argument("--vehicle-fixed-cost", type=int, default=int(HIERARCHICAL_OBJECTIVE_SCALE))
    return parser.parse_args()


def scaled_int(value: float, scale: int) -> int:
    return int(round(value * scale))


def scaled_float(value: int | float, scale: int) -> float:
    return round(float(value) / scale, 6)


def build_model(
    instance: dict[str, Any],
    time_scale: int,
    vehicle_fixed_cost: int,
) -> tuple[Model, list[dict[str, Any]]]:
    model = Model()
    depot = instance["depots"][0]
    depot_handle = model.add_depot(
        depot["x"],
        depot["y"],
        tw_early=scaled_int(float(depot["tw"]["start"]), time_scale),
        tw_late=scaled_int(float(depot["tw"]["end"]), time_scale),
        name=depot["id"],
    )

    locations = [depot]
    for node in instance["nodes"]:
        delivery = max(-int(node["demand"]), 0)
        pickup = max(int(node["demand"]), 0)
        model.add_client(
            node["x"],
            node["y"],
            delivery=delivery,
            pickup=pickup,
            service_duration=scaled_int(float(node["service_duration"]), time_scale),
            tw_early=scaled_int(float(node["tw"]["start"]), time_scale),
            tw_late=scaled_int(float(node["tw"]["end"]), time_scale),
            name=node["id"],
        )
        locations.append(node)

    planning_horizon = instance["planning_horizon"]
    model.add_vehicle_type(
        num_available=int(instance["vehicles_per_depot"][depot["id"]]),
        capacity=int(instance["capacity"]),
        start_depot=depot_handle,
        end_depot=depot_handle,
        fixed_cost=vehicle_fixed_cost,
        tw_early=scaled_int(float(depot["tw"]["start"]), time_scale),
        tw_late=scaled_int(float(depot["tw"]["end"]), time_scale),
        shift_duration=scaled_int(float(planning_horizon["end"] - planning_horizon["start"]), time_scale),
        unit_distance_cost=1,
        unit_duration_cost=0,
        name="li-lim-vehicle",
    )

    for frm_idx, frm in enumerate(locations):
        for to_idx, to in enumerate(locations):
            if frm_idx == to_idx:
                continue

            distance = scaled_int(travel_distance(instance, frm, to), time_scale)
            model.add_edge(
                model.locations[frm_idx],
                model.locations[to_idx],
                distance,
                duration=distance,
            )

    return model, locations


def precedence_violation_counts(evaluation: dict[str, Any]) -> tuple[int, int]:
    pair_split_count = sum(
        1
        for violation in evaluation["precedence_violations"]
        if violation.endswith(":pair_split")
    )
    precedence_count = sum(
        1
        for violation in evaluation["precedence_violations"]
        if violation.endswith(":precedence")
    )
    return pair_split_count, precedence_count


def solve_instance(
    instance: dict[str, Any],
    runtime_limit: float,
    seed_offset: int,
    time_scale: int,
    vehicle_fixed_cost: int,
) -> dict[str, Any]:
    model, locations = build_model(instance, time_scale, vehicle_fixed_cost)
    solver_seed = int(instance["seed"]) + seed_offset

    started_at = time.perf_counter()
    result = model.solve(
        MaxRuntime(runtime_limit),
        seed=solver_seed,
        collect_stats=False,
        display=False,
    )
    runtime_seconds = time.perf_counter() - started_at

    routes = []
    for route_idx, route in enumerate(result.best.routes()):
        depot_id = instance["depots"][route.start_depot()]["id"]
        node_ids = [locations[location_idx]["id"] for location_idx in route.visits()]
        schedule = [
            {
                "node_id": locations[visit.location]["id"],
                "start_service": scaled_float(visit.start_service, time_scale),
                "end_service": scaled_float(visit.end_service, time_scale),
                "wait_duration": scaled_float(visit.wait_duration, time_scale),
                "time_warp": scaled_float(visit.time_warp, time_scale),
            }
            for visit in route.schedule()
        ]
        routes.append(
            {
                "route_index": route_idx,
                "depot_id": depot_id,
                "node_ids": node_ids,
                "reported_distance": scaled_float(route.distance(), time_scale),
                "reported_duration": scaled_float(route.duration(), time_scale),
                "reported_start_time": scaled_float(route.start_time(), time_scale),
                "reported_end_time": scaled_float(route.end_time(), time_scale),
                "schedule": schedule,
            }
        )

    evaluation = evaluate_solution(
        instance,
        [route_blueprint(route["depot_id"], route["node_ids"]) for route in routes],
    )
    pair_split_count, precedence_count = precedence_violation_counts(evaluation)

    return {
        "instance": instance["name"],
        "solver": "pyvrp-relaxed",
        "solver_version": "0.13.3",
        "model_note": (
            "PyVRP public APIs do not encode Li-Lim pickup-delivery sibling precedence "
            "or same-request load transfer exactly. The produced route sequence is "
            "therefore re-evaluated with the strict Li-Lim evaluator."
        ),
        "seed": solver_seed,
        "runtime_seconds": runtime_seconds,
        "time_scale": time_scale,
        "reported_cost": result.cost(),
        "reported_feasible": result.is_feasible(),
        "route_count": len(routes),
        "routes": routes,
        "evaluation": evaluation,
        "strict_pair_split_count": pair_split_count,
        "strict_precedence_count": precedence_count,
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    for instance_path in sorted(args.instances_dir.glob("instance_*.json")):
        instance = load_json(instance_path)
        solution = solve_instance(
            instance,
            args.runtime_limit,
            args.seed_offset,
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
                "pair_split_count": solution["strict_pair_split_count"],
                "precedence_count": solution["strict_precedence_count"],
                "runtime_seconds": round(solution["runtime_seconds"], 3),
            }
        )
        print(
            f"[pyvrp/li-lim] {instance['name']}: "
            f"reported_feasible={solution['reported_feasible']} "
            f"strict_feasible={solution['evaluation']['feasible']} "
            f"routes={solution['evaluation']['route_count']} "
            f"distance={solution['evaluation']['comparison_distance']:.2f} "
            f"pair_split={solution['strict_pair_split_count']} "
            f"precedence={solution['strict_precedence_count']}"
        )

    save_json({"solutions": summary}, args.output_dir / "summary.json")


if __name__ == "__main__":
    main()
