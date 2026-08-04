"""Business logic for fleet analytics metrics."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.driver import Driver
from app.models.order import Order
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
    ) -> FleetAnalyticsResponse:
        """Return complete fleet dashboard metrics."""
        completed_orders, pending_orders = self._split_orders_by_status(orders)
        vehicle_utilization = self._compute_vehicle_utilization_percentage(
            vehicles,
            orders,
        )
        driver_utilization = self._compute_driver_utilization_percentage(
            drivers,
            orders,
        )
        average_distance = self._compute_average_route_distance_km(
            completed_orders,
            optimization_result,
        )
        average_eta = self._compute_average_eta_minutes(
            completed_orders,
            optimization_result,
        )
        total_orders = len(orders)
        completed_count = len(completed_orders)
        pending_count = len(pending_orders)
        route_efficiency = self._compute_route_efficiency_percentage(
            completed_count,
            total_orders,
            optimization_result,
        )
        on_time = self._compute_on_time_delivery_percentage(completed_orders)

        return FleetAnalyticsResponse(
            vehicle_utilization_percentage=vehicle_utilization,
            driver_utilization_percentage=driver_utilization,
            average_route_distance_km=average_distance,
            average_eta_minutes=average_eta,
            completed_orders=completed_count,
            pending_orders=pending_count,
            total_orders=total_orders,
            route_efficiency_percentage=route_efficiency,
            on_time_delivery_percentage=on_time,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _split_orders_by_status(orders: list[Order]) -> tuple[list[Order], list[Order]]:
        """Split orders into completed and pending buckets by status values."""
        completed: list[Order] = []
        pending: list[Order] = []

        completed_statuses = {
            "completed",
            "delivered",
            "done",
            "finished",
        }

        for order in orders:
            status_value = str(
                getattr(
                    getattr(order, "status", None),
                    "value",
                    getattr(order, "status", ""),
                )
            ).lower()
            if status_value in completed_statuses:
                completed.append(order)
            else:
                pending.append(order)

        return completed, pending

    @staticmethod
    def _compute_vehicle_utilization_percentage(
        vehicles: list[Vehicle],
        orders: list[Order],
    ) -> float:
        """Compute utilization percentage for vehicles based on assignments."""
        if not vehicles:
            return 0.0

        assigned_vehicle_ids = {
            getattr(order, "assigned_vehicle_id", None)
            for order in orders
            if getattr(order, "assigned_vehicle_id", None) is not None
        }
        utilized_count = sum(1 for vehicle in vehicles if vehicle.id in assigned_vehicle_ids)
        return round((utilized_count / len(vehicles)) * 100.0, 2)

    @staticmethod
    def _compute_driver_utilization_percentage(
        drivers: list[Driver],
        orders: list[Order],
    ) -> float:
        """Compute utilization percentage for drivers based on assignments."""
        if not drivers:
            return 0.0

        assigned_driver_ids = {
            getattr(order, "assigned_driver_id", None)
            for order in orders
            if getattr(order, "assigned_driver_id", None) is not None
        }
        utilized_count = sum(1 for driver in drivers if driver.id in assigned_driver_ids)
        return round((utilized_count / len(drivers)) * 100.0, 2)

    @staticmethod
    def _compute_average_route_distance_km(
        completed_orders: list[Order],
        optimization_result: OptimizationResponse | None,
    ) -> float:
        """Compute average route distance using optimization data when available."""
        if optimization_result is not None and optimization_result.routes:
            route_distances = []
            for route in optimization_result.routes:
                distance_value = float(route.total_distance_km)
                if distance_value > 0:
                    route_distances.append(distance_value)
            if route_distances:
                return round(sum(route_distances) / len(route_distances), 3)

        distances = [
            float(getattr(order, "distance_km", 0.0) or 0.0)
            for order in completed_orders
            if float(getattr(order, "distance_km", 0.0) or 0.0) > 0
        ]
        if not distances:
            return 0.0
        return round(sum(distances) / len(distances), 3)

    @staticmethod
    def _compute_average_eta_minutes(
        completed_orders: list[Order],
        optimization_result: OptimizationResponse | None,
    ) -> float:
        """Compute average ETA in minutes across completed orders."""
        if optimization_result is not None:
            eta_values: list[float] = []
            for route in optimization_result.routes:
                arrivals = [stop.arrival_time for stop in route.stops if stop.arrival_time is not None]
                if len(arrivals) < 2:
                    continue
                route_start = min(arrivals)
                route_end = max(arrivals)
                eta_values.append((route_end - route_start).total_seconds() / 60.0)

            if eta_values:
                return round(sum(eta_values) / len(eta_values), 2)

        eta_minutes = [
            float(getattr(order, "eta_minutes", 0.0) or 0.0)
            for order in completed_orders
            if float(getattr(order, "eta_minutes", 0.0) or 0.0) > 0
        ]
        if eta_minutes:
            return round(sum(eta_minutes) / len(eta_minutes), 2)

        total_minutes = 0.0
        samples = 0
        for order in completed_orders:
            created_at = getattr(order, "created_at", None)
            completed_at = getattr(order, "completed_at", None)
            if isinstance(created_at, datetime) and isinstance(completed_at, datetime):
                delta = (completed_at - created_at).total_seconds() / 60.0
                if delta >= 0:
                    total_minutes += delta
                    samples += 1

        if samples == 0:
            return 0.0
        return round(total_minutes / samples, 2)

    @staticmethod
    def _compute_route_efficiency_percentage(
        completed_order_count: int,
        total_order_count: int,
        optimization_result: OptimizationResponse | None,
    ) -> float:
        """Compute route efficiency percentage with safe zero-division handling."""
        if total_order_count <= 0:
            return 0.0

        denominator = total_order_count
        if optimization_result is not None and optimization_result.total_orders > 0:
            denominator = optimization_result.total_orders

        efficiency = (completed_order_count / denominator) * 100.0
        return round(max(0.0, min(100.0, efficiency)), 2)

    @staticmethod
    def _compute_on_time_delivery_percentage(completed_orders: list[Order]) -> float:
        """Compute percentage of completed orders delivered on time."""
        if not completed_orders:
            return 0.0

        explicit_flags = [
            getattr(order, "is_on_time", None)
            for order in completed_orders
            if getattr(order, "is_on_time", None) is not None
        ]
        if explicit_flags:
            on_time_count = sum(1 for value in explicit_flags if bool(value))
            return round((on_time_count / len(explicit_flags)) * 100.0, 2)

        on_time_count = 0
        measured = 0
        for order in completed_orders:
            delivered_at = getattr(order, "delivered_at", None)
            eta_at = getattr(order, "eta_at", None)
            if isinstance(delivered_at, datetime) and isinstance(eta_at, datetime):
                measured += 1
                if delivered_at <= eta_at:
                    on_time_count += 1

        if measured == 0:
            return 0.0
        return round((on_time_count / measured) * 100.0, 2)
