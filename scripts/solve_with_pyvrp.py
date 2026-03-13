from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from pyvrp import Model
from pyvrp.stop import MaxRuntime

from common import evaluate_solution, euclidean_int, load_json, route_blueprint, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve instances with PyVRP.")
    parser.add_argument("--instances-dir", type=Path, default=Path("instances"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/pyvrp"))
    parser.add_argument("--runtime-limit", type=float, default=2.5)
    parser.add_argument("--seed-offset", type=int, default=17)
    return parser.parse_args()


def build_model(instance: dict[str, Any]) -> tuple[Model, list[dict[str, Any]]]:
    model = Model()
    depot_handles = []

    for depot in instance["depots"]:
        depot_handles.append(
            model.add_depot(
                depot["x"],
                depot["y"],
                tw_early=depot["tw"]["start"],
                tw_late=depot["tw"]["end"],
                name=depot["id"],
            )
        )

    for node in instance["nodes"]:
        delivery = -int(node["demand"]) if int(node["demand"]) < 0 else 0
        pickup = int(node["demand"]) if int(node["demand"]) > 0 else 0

        model.add_client(
            node["x"],
            node["y"],
            delivery=delivery,
            pickup=pickup,
            service_duration=node["service_duration"],
            tw_early=node["tw"]["start"],
            tw_late=node["tw"]["end"],
            name=node["id"],
        )

    for depot, depot_handle in zip(instance["depots"], depot_handles, strict=True):
        model.add_vehicle_type(
            num_available=int(instance["vehicles_per_depot"][depot["id"]]),
            capacity=int(instance["capacity"]),
            start_depot=depot_handle,
            end_depot=depot_handle,
            tw_early=depot["tw"]["start"],
            tw_late=depot["tw"]["end"],
            shift_duration=instance["planning_horizon"]["end"] - instance["planning_horizon"]["start"],
            unit_distance_cost=1,
            unit_duration_cost=0,
            name=f"vehicle-{depot['id']}",
        )

    locations = instance["depots"] + instance["nodes"]
    for frm_idx, frm in enumerate(locations):
        for to_idx, to in enumerate(locations):
            if frm_idx == to_idx:
                continue

            distance = euclidean_int(frm, to)
            model.add_edge(
                model.locations[frm_idx],
                model.locations[to_idx],
                distance,
                duration=distance,
            )

    return model, locations


def solve_instance(instance: dict[str, Any], runtime_limit: float, seed_offset: int) -> dict[str, Any]:
    model, locations = build_model(instance)
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
        node_ids = [locations[location_idx]["id"] for location_idx in route.visits()]
        depot_id = instance["depots"][route.start_depot()]["id"]
        schedule = [
            {
                "node_id": locations[visit.location]["id"],
                "start_service": visit.start_service,
                "end_service": visit.end_service,
                "wait_duration": visit.wait_duration,
                "time_warp": visit.time_warp,
            }
            for visit in route.schedule()
        ]

        routes.append(
            {
                "route_index": route_idx,
                "depot_id": depot_id,
                "node_ids": node_ids,
                "reported_distance": route.distance(),
                "reported_duration": route.duration(),
                "reported_start_time": route.start_time(),
                "reported_end_time": route.end_time(),
                "schedule": schedule,
            }
        )

    evaluation = evaluate_solution(
        instance,
        [route_blueprint(route["depot_id"], route["node_ids"]) for route in routes],
    )

    return {
        "instance": instance["name"],
        "solver": "pyvrp",
        "solver_version": "0.13.3",
        "seed": solver_seed,
        "runtime_seconds": runtime_seconds,
        "reported_cost": result.cost(),
        "reported_feasible": result.is_feasible(),
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
        solution = solve_instance(instance, args.runtime_limit, args.seed_offset)
        save_json(solution, args.output_dir / f"{instance['name']}.solution.json")

        summary.append(
            {
                "instance": instance["name"],
                "objective": solution["evaluation"]["objective"],
                "route_count": solution["evaluation"]["route_count"],
                "feasible": solution["evaluation"]["feasible"],
                "runtime_seconds": round(solution["runtime_seconds"], 3),
            }
        )
        print(
            f"[pyvrp] {instance['name']}: "
            f"objective={solution['evaluation']['objective']} "
            f"routes={solution['evaluation']['route_count']} "
            f"feasible={solution['evaluation']['feasible']}"
        )

    save_json({"solutions": summary}, args.output_dir / "summary.json")


if __name__ == "__main__":
    main()
