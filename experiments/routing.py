"""Paired reactive versus forecast-advisory routing experiment."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.order import OrderStatus
from app.schemas.hgfc import HGFCRequest
from app.services.hgfc_service import HGFCService
from app.services.route_optimizer import RouteOptimizerService

from experiments.common import (
    ExperimentConfig,
    load_synthetic_dataset,
    make_dataset,
    write_results,
)
from experiments.forecasting import _seasonal_regression_forecast

OUTPUT_DIR = Path(__file__).resolve().parent / "results"


@dataclass(frozen=True)
class RoutingExperimentConfig:
    scenario_count: int = 6
    fleet_size: int = 4
    vehicle_capacity: int = 25
    solver_timeout_seconds: int = 1
    solver_solution_limit: int = 1
    advisory_horizon_days: int = 14
    depot_latitude: float = 41.8781
    depot_longitude: float = -87.6298


class OfflineRoutingService:
    """Keep the experiment independent of external OSRM availability."""

    def build_road_route(self, route_coordinates):
        return None


def _scenario_uuid(scenario_index: int, object_index: int, kind: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"research-scenario:{scenario_index}:{object_index}:{kind}")


def _build_scenario(
    scenario_index: int,
    daily_demand: float,
    routing_config: RoutingExperimentConfig,
):
    fleet_size = routing_config.fleet_size
    vehicle_capacity = routing_config.vehicle_capacity
    vehicles = [
        SimpleNamespace(
            id=_scenario_uuid(scenario_index, index, "vehicle"),
            capacity=vehicle_capacity,
            registration_number=f"R-{scenario_index}-{index}",
        )
        for index in range(fleet_size)
    ]
    drivers = [
        SimpleNamespace(
            id=_scenario_uuid(scenario_index, index, "driver"),
            vehicle_id=vehicles[index].id,
            user=SimpleNamespace(full_name=f"Scenario {scenario_index} driver {index}"),
        )
        for index in range(fleet_size)
    ]
    remaining_demand = max(round(daily_demand), 1)
    orders = []
    order_index = 0
    while remaining_demand:
        demand = min(remaining_demand, routing_config.vehicle_capacity)
        latitude = 41.0 + scenario_index * 0.001 + order_index * 0.01
        longitude = -87.0 - order_index * 0.01
        orders.append(
            SimpleNamespace(
                id=_scenario_uuid(scenario_index, order_index, "order"),
                customer_name=f"Scenario {scenario_index} customer {order_index}",
                pickup_address="Central depot",
                delivery_address=f"Delivery {order_index}",
                pickup_latitude=latitude,
                pickup_longitude=longitude,
                delivery_latitude=latitude + 0.005,
                delivery_longitude=longitude + 0.005,
                demand=demand,
                priority=1,
                status=OrderStatus.PENDING,
                time_window_start=None,
                time_window_end=None,
            )
        )
        remaining_demand -= demand
        order_index += 1
    return drivers, vehicles, orders


def _run_cvrp(
    scenario_index: int,
    demand: float,
    routing_config: RoutingExperimentConfig,
) -> dict[str, float | int | bool]:
    drivers, vehicles, orders = _build_scenario(scenario_index, demand, routing_config)
    optimizer = RouteOptimizerService(routing_service=OfflineRoutingService())
    optimizer.configure(
        optimization_timeout_seconds=routing_config.solver_timeout_seconds,
        optimization_solution_limit=routing_config.solver_solution_limit,
    )
    confirmed_demand_units = sum(int(order.demand) for order in orders)
    started_at = perf_counter()
    try:
        result = optimizer.optimize(
            drivers,
            vehicles,
            orders,
            depot_coordinates=(routing_config.depot_latitude, routing_config.depot_longitude),
        )
    except RuntimeError as error:
        if "Insufficient vehicle capacity" not in str(error) and "No feasible" not in str(error):
            raise
        runtime_seconds = perf_counter() - started_at
        return {
            "feasible": False,
            "optimization_runtime_seconds": runtime_seconds,
            "served_orders": 0,
            "requested_orders": len(orders),
            "service_level_percent": 0.0,
            "fleet_utilization_percent": 0.0,
            "route_distance_km": 0.0,
            "route_count": 0,
            "capacity_shortfall": max(0.0, confirmed_demand_units - sum(vehicle.capacity for vehicle in vehicles)),
            "confirmed_demand_units": confirmed_demand_units,
        }

    runtime_seconds = perf_counter() - started_at
    served_orders = sum(route.total_orders for route in result.routes)
    capacity_total = sum(vehicle.capacity for vehicle in vehicles)
    return {
        "feasible": True,
        "optimization_runtime_seconds": runtime_seconds,
        "served_orders": served_orders,
        "requested_orders": len(orders),
        "service_level_percent": (served_orders / len(orders)) * 100.0,
        "fleet_utilization_percent": (
            sum(route.total_demand for route in result.routes) / capacity_total
        ) * 100.0
        if capacity_total and result.routes
        else 0.0,
        "route_distance_km": result.total_distance_km,
        "route_count": result.total_routes,
        "capacity_shortfall": max(0.0, confirmed_demand_units - capacity_total),
        "confirmed_demand_units": confirmed_demand_units,
    }


def run_paired_routing_experiment(
    config: ExperimentConfig | None = None,
    routing_config: RoutingExperimentConfig | None = None,
) -> list[dict]:
    """Compare identical CVRP inputs with advisory computation enabled/absent."""
    config = config or ExperimentConfig()
    routing_config = routing_config or RoutingExperimentConfig()
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "raw" / "synthetic_demand.csv"
    if dataset_path.exists() and config.observations == 730:
        _, series = load_synthetic_dataset(dataset_path)
    else:
        series = make_dataset(config)
    training = series[: config.training_days]
    holdout = series[config.training_days : config.training_days + config.holdout_days]
    forecasts = _seasonal_regression_forecast(
        training,
        len(holdout),
        frozenset({"weekly", "annual", "lags", "rolling"}),
        config.annual_period_days,
    )
    sampled_indices = np.linspace(
        0,
        len(holdout) - 1,
        num=routing_config.scenario_count,
        dtype=int,
    )
    rows: list[dict] = []
    for scenario_index, day_index in enumerate(sampled_indices):
        confirmed_demand = float(holdout[day_index])
        forecast_demand = float(forecasts[day_index])
        available_capacity = float(routing_config.fleet_size * routing_config.vehicle_capacity)
        advisory = HGFCService(
            advisory_horizon_days=routing_config.advisory_horizon_days
        ).assess(
            HGFCRequest(
                forecast_demand=forecast_demand,
                available_capacity=available_capacity,
                horizon_days=int(day_index) + 1,
            )
        )

        # No candidate-fleet preparation policy exists; run unchanged CVRP once.
        reactive = _run_cvrp(scenario_index, confirmed_demand, routing_config)
        forecast_aware = reactive
        scenario_drivers, scenario_vehicles, scenario_orders = _build_scenario(
            scenario_index,
            confirmed_demand,
            routing_config,
        )
        rows.append(
            {
                "scenario_id": scenario_index,
                "forecast_lead_days": int(day_index) + 1,
                "confirmed_demand": confirmed_demand,
                "confirmed_demand_units": reactive["confirmed_demand_units"],
                "depot_coordinates": [routing_config.depot_latitude, routing_config.depot_longitude],
                "driver_ids": [str(driver.id) for driver in scenario_drivers],
                "vehicle_ids": [str(vehicle.id) for vehicle in scenario_vehicles],
                "vehicle_capacities": [int(vehicle.capacity) for vehicle in scenario_vehicles],
                "confirmed_order_ids": [str(order.id) for order in scenario_orders],
                "confirmed_order_demands": [int(order.demand) for order in scenario_orders],
                "delivery_coordinates": [
                    [float(order.delivery_latitude), float(order.delivery_longitude)]
                    for order in scenario_orders
                ],
                "forecast_demand": forecast_demand,
                "available_capacity": available_capacity,
                "capacity_delta": advisory.capacity_delta,
                "rho": advisory.rho,
                "capacity_risk": advisory.capacity_risk,
                "preparation_intervention": advisory.preparation_recommended,
                "reactive_feasible": reactive["feasible"],
                "hgfc_feasible": forecast_aware["feasible"],
                "reactive_optimization_runtime_seconds": reactive["optimization_runtime_seconds"],
                "hgfc_optimization_runtime_seconds": forecast_aware["optimization_runtime_seconds"],
                "reactive_service_level_percent": reactive["service_level_percent"],
                "hgfc_service_level_percent": forecast_aware["service_level_percent"],
                "reactive_fleet_utilization_percent": reactive["fleet_utilization_percent"],
                "hgfc_fleet_utilization_percent": forecast_aware["fleet_utilization_percent"],
                "reactive_route_distance_km": reactive["route_distance_km"],
                "hgfc_route_distance_km": forecast_aware["route_distance_km"],
                "reactive_capacity_shortfall": reactive["capacity_shortfall"],
                "hgfc_capacity_shortfall": forecast_aware["capacity_shortfall"],
                "reactive_route_count": reactive["route_count"],
                "hgfc_route_count": forecast_aware["route_count"],
                "served_orders": forecast_aware["served_orders"],
                "requested_orders": forecast_aware["requested_orders"],
            }
        )

    operational_fields = (
        "feasible",
        "service_level_percent",
        "fleet_utilization_percent",
        "route_distance_km",
        "capacity_shortfall",
        "route_count",
    )
    summary = {
        "configuration": asdict(routing_config),
        "scenario_count": len(rows),
        "operational_benefit_evaluation_supported": False,
        "operational_benefit_limitation": (
            "No candidate-fleet/advance-preparation policy exists in the available operational data; "
            "both arms therefore use the same actual fleet and confirmed orders."
        ),
        "advisory_interventions": sum(bool(row["preparation_intervention"]) for row in rows),
        "mean_operational_metrics": {
            arm: {
                field: float(np.mean([row[f"{arm}_{field}"] for row in rows]))
                for field in (
                    "service_level_percent",
                    "fleet_utilization_percent",
                    "route_distance_km",
                    "capacity_shortfall",
                    "route_count",
                )
            }
            for arm in ("reactive", "hgfc")
        },
        "mean_optimization_runtime_seconds": {
            arm: float(np.mean([row[f"{arm}_optimization_runtime_seconds"] for row in rows]))
            for arm in ("reactive", "hgfc")
        },
        "paired_operational_differences": {
            field: [
                float(row[f"hgfc_{field}"]) - float(row[f"reactive_{field}"])
                for row in rows
            ]
            for field in operational_fields
        },
        "paired_inference": "not_applicable_all_operational_pair_differences_are_zero_by_design",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "reactive_vs_hgfc_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    write_results(
        OUTPUT_DIR,
        "reactive_vs_hgfc",
        rows,
        config,
        {
            "scenario_sampling": "six evenly spaced forecast lead times in 60-day chronological holdout",
            "routing_configuration": asdict(routing_config),
            "routing": "real OR-Tools, PATH_CHEAPEST_ARC first solution limit, Haversine matrix, OSRM disabled",
            "routing_arms": "identical confirmed demand and fleet in both arms; invariance check, not operational benefit test",
            "capacity_cost_model": "not defined by project; delivery cost omitted",
        },
    )
    write_results(
        OUTPUT_DIR,
        "cvrp_benchmark",
        [
            {
                "scenario_id": row["scenario_id"],
                "confirmed_demand": row["confirmed_demand"],
                "confirmed_demand_units": row["confirmed_demand_units"],
                "confirmed_order_ids": row["confirmed_order_ids"],
                "confirmed_order_demands": row["confirmed_order_demands"],
                "delivery_coordinates": row["delivery_coordinates"],
                "available_capacity": row["available_capacity"],
                "feasible": row["reactive_feasible"],
                "service_level_percent": row["reactive_service_level_percent"],
                "fleet_utilization_percent": row["reactive_fleet_utilization_percent"],
                "route_distance_km": row["reactive_route_distance_km"],
                "capacity_shortfall": row["reactive_capacity_shortfall"],
                "route_count": row["reactive_route_count"],
                "optimization_runtime_seconds": row["reactive_optimization_runtime_seconds"],
            }
            for row in rows
        ],
        config,
        {
            "solver": "Google OR-Tools CVRP",
            "demand_source": "integer confirmed scenario orders only",
            "distance": "deterministic Haversine matrix, depot and delivery nodes",
        },
    )
    write_results(
        OUTPUT_DIR,
        "hgfc_advisory",
        [
            {
                "scenario_id": row["scenario_id"],
                "forecast_lead_days": row["forecast_lead_days"],
                "forecast_demand": row["forecast_demand"],
                "available_capacity": row["available_capacity"],
                "capacity_delta": row["capacity_delta"],
                "rho": row["rho"],
                "capacity_risk": row["capacity_risk"],
                "preparation_intervention": row["preparation_intervention"],
            }
            for row in rows
        ],
        config,
        {
            "capacity_interpretation": "available capacity for one daily planning period, matching daily forecast demand units",
            "horizon_gate_days": routing_config.advisory_horizon_days,
            "preparation_action": "warning only; no candidate fleet or dispatch preparation policy is present",
        },
    )
    return rows


if __name__ == "__main__":
    results = run_paired_routing_experiment()
    intervention_count = sum(bool(row["preparation_intervention"]) for row in results)
    print(f"paired_scenarios={len(results)} advisory_interventions={intervention_count} output={OUTPUT_DIR}")
