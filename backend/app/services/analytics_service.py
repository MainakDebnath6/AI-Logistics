"""Business logic for fleet analytics metrics."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.driver import Driver
from app.models.order import Order
from app.models.route import Route
from app.models.vehicle import Vehicle
from app.schemas.analytics import FleetAnalyticsResponse
from app.schemas.optimization import OptimizationResponse


class AnalyticsService:
    """Compute fleet dashboard metrics from loaded domain entities."""

    def get_dashboard_metrics(
        self,
        drivers: list[Driver],
        vehicles: list[Vehicle],
        orders: list[Order],
        optimization_result: OptimizationResponse | None = None,
        route_history: list[Route] | None = None,
    ) -> FleetAnalyticsResponse:
        """Return complete fleet dashboard metrics."""
        completed_orders, open_orders, cancelled_orders = self._split_orders_by_status(orders)
        vehicle_utilization = self._compute_vehicle_utilization_percentage(
            vehicles,
            orders,
        )
        driver_utilization = self._compute_driver_utilization_percentage(
            drivers,
            orders,
        )
        average_distance = self._compute_average_route_distance_km(
            optimization_result,
            route_history or [],
        )
        average_eta = self._compute_average_eta_minutes(
            optimization_result,
            route_history or [],
        )
        total_orders = len(orders)
        completed_count = len(completed_orders)
        pending_count = len(open_orders)
        route_efficiency = self._compute_route_efficiency_percentage(
            completed_count,
            len(open_orders) + completed_count,
        )

        return FleetAnalyticsResponse(
            vehicle_utilization_percentage=vehicle_utilization,
            driver_utilization_percentage=driver_utilization,
            average_route_distance_km=average_distance,
            average_eta_minutes=average_eta,
            completed_orders=completed_count,
            pending_orders=pending_count,
            cancelled_orders=len(cancelled_orders),
            total_orders=total_orders,
            route_efficiency_percentage=route_efficiency,
            on_time_delivery_percentage=None,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _split_orders_by_status(
        orders: list[Order],
    ) -> tuple[list[Order], list[Order], list[Order]]:
        """Split delivered, non-cancelled open, and cancelled orders."""
        completed: list[Order] = []
        open_orders: list[Order] = []
        cancelled: list[Order] = []

        for order in orders:
            status_value = str(
                getattr(
                    getattr(order, "status", None),
                    "value",
                    getattr(order, "status", ""),
                )
            ).lower()
            if status_value == "delivered":
                completed.append(order)
            elif status_value == "cancelled":
                cancelled.append(order)
            else:
                open_orders.append(order)

        return completed, open_orders, cancelled

    @staticmethod
    def _compute_vehicle_utilization_percentage(
        vehicles: list[Vehicle],
        orders: list[Order],
    ) -> float | None:
        """Compute active vehicle utilization from assigned or in-transit orders."""
        active_vehicles = [
            vehicle
            for vehicle in vehicles
            if bool(getattr(vehicle, "is_active", True))
            and str(
                getattr(getattr(vehicle, "status", None), "value", getattr(vehicle, "status", ""))
            ).lower()
            in {"available", "in_use"}
        ]
        if not active_vehicles:
            return None

        assigned_vehicle_ids = {
            getattr(order, "assigned_vehicle_id", None)
            for order in orders
            if getattr(order, "assigned_vehicle_id", None) is not None
            and AnalyticsService._is_active_assignment(order)
        }
        utilized_count = sum(1 for vehicle in active_vehicles if vehicle.id in assigned_vehicle_ids)
        return round((utilized_count / len(active_vehicles)) * 100.0, 2)

    @staticmethod
    def _compute_driver_utilization_percentage(
        drivers: list[Driver],
        orders: list[Order],
    ) -> float | None:
        """Compute eligible driver utilization from assigned or in-transit orders."""
        eligible_drivers = [
            driver
            for driver in drivers
            if str(getattr(getattr(driver, "status", None), "value", getattr(driver, "status", ""))).lower()
            in {"available", "busy"}
        ]
        if not eligible_drivers:
            return None

        assigned_driver_ids = {
            getattr(order, "assigned_driver_id", None)
            for order in orders
            if getattr(order, "assigned_driver_id", None) is not None
            and AnalyticsService._is_active_assignment(order)
        }
        utilized_count = sum(1 for driver in eligible_drivers if driver.id in assigned_driver_ids)
        return round((utilized_count / len(eligible_drivers)) * 100.0, 2)

    @staticmethod
    def _is_active_assignment(order: Order) -> bool:
        status_value = str(
            getattr(getattr(order, "status", None), "value", getattr(order, "status", ""))
        ).lower()
        return status_value in {"assigned", "in_transit"}

    @staticmethod
    def _compute_average_route_distance_km(
        optimization_result: OptimizationResponse | None,
        route_history: list[Route],
    ) -> float | None:
        """Average persisted optimizer distances, keeping Haversine as its source."""
        distances = []
        if route_history:
            distances = [
                float(route.total_distance_km)
                for route in route_history
                if float(route.total_distance_km) > 0
            ]
        elif optimization_result is not None:
            distances = [
                float(route.total_distance_km)
                for route in optimization_result.routes
                if float(route.total_distance_km) > 0
            ]
        return round(sum(distances) / len(distances), 3) if distances else None

    @staticmethod
    def _compute_average_eta_minutes(
        optimization_result: OptimizationResponse | None,
        route_history: list[Route],
    ) -> float | None:
        """Average only successful OSRM durations; unavailable road ETAs stay null."""
        durations: list[float] = []
        route_results = (
            route_history
            if route_history
            else optimization_result.routes if optimization_result is not None else []
        )
        for result in route_results:
            route_data = (
                result.optimization_result
                if isinstance(result, Route)
                else result.model_dump(mode="python")
            )
            if route_data.get("road_route_status") != "available":
                continue
            duration_minutes = route_data.get("total_duration_minutes")
            if isinstance(duration_minutes, (int, float)) and duration_minutes > 0:
                durations.append(float(duration_minutes))
        return round(sum(durations) / len(durations), 2) if durations else None

    @staticmethod
    def _compute_route_efficiency_percentage(
        completed_order_count: int,
        total_order_count: int,
    ) -> float | None:
        """Compute the completed-order share; it is not a geometric route-efficiency score."""
        if total_order_count <= 0:
            return None

        efficiency = (completed_order_count / total_order_count) * 100.0
        return round(max(0.0, min(100.0, efficiency)), 2)
