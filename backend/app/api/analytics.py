"""Analytics API endpoints."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_dispatcher
from app.models.driver import Driver
from app.models.order import Order
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.driver_repository import DriverRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.analytics import FleetAnalyticsResponse
from app.schemas.optimization import OptimizationResponse
from app.services.analytics_service import AnalyticsService


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

RESEARCH_RESULTS_DIR = Path(__file__).resolve().parents[3] / "experiments" / "results"
SYNTHETIC_DEMAND_CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "synthetic_demand.csv"
MAX_SYNTHETIC_DEMAND_ROWS = 730


def get_analytics_service() -> AnalyticsService:
    """Create an analytics service instance."""
    return AnalyticsService()


def get_driver_repository(db: Session = Depends(get_db)) -> DriverRepository:
    """Create a driver repository instance."""
    return DriverRepository(db)


def get_vehicle_repository(db: Session = Depends(get_db)) -> VehicleRepository:
    """Create a vehicle repository instance."""
    return VehicleRepository(db)


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    """Create an order repository instance."""
    return OrderRepository(db)


def get_optimization_result_from_state(
    request: Request,
) -> OptimizationResponse | None:
    """Return optional optimization result from request state."""
    candidate = getattr(request.state, "optimization_result", None)
    if isinstance(candidate, OptimizationResponse):
        return candidate
    return None


def _is_dispatcher_or_admin(user: User) -> bool:
    """Return whether the authenticated user can access analytics."""
    role = getattr(user, "role", None)
    if role is None:
        return False

    role_value = getattr(role, "value", role)
    return isinstance(role_value, str) and role_value.lower() in {
        "dispatcher",
        "admin",
    }


def _normalize_date(value: Any) -> str | None:
    """Convert a database date-like value to ISO date text."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def summarize_synthetic_demand_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize ordered demand rows from the synthetic demand dataset."""
    ordered_rows = sorted(rows, key=lambda item: str(item.get("date") or ""))
    observations: list[dict[str, Any]] = []

    for row in ordered_rows:
        date_value = _normalize_date(row.get("date"))
        demand_value = row.get("demand")
        if date_value is None or demand_value is None:
            continue
        observations.append({"date": date_value, "demand": float(demand_value)})

    if not observations:
        return {
            "count": 0,
            "start_date": None,
            "end_date": None,
            "average_demand": 0.0,
            "min_demand": 0.0,
            "max_demand": 0.0,
            "observations": [],
        }

    demand_values = [observation["demand"] for observation in observations]
    return {
        "count": len(observations),
        "start_date": observations[0]["date"],
        "end_date": observations[-1]["date"],
        "average_demand": sum(demand_values) / len(demand_values),
        "min_demand": min(demand_values),
        "max_demand": max(demand_values),
        "observations": observations,
    }


def _fallback_synthetic_demand_summary() -> dict[str, Any]:
    """Load synthetic demand from the local CSV when database access is unavailable."""
    if not SYNTHETIC_DEMAND_CSV_PATH.exists():
        return {
            "count": 0,
            "start_date": None,
            "end_date": None,
            "average_demand": 0.0,
            "min_demand": 0.0,
            "max_demand": 0.0,
            "observations": [],
        }

    with SYNTHETIC_DEMAND_CSV_PATH.open("r", encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [{"date": row.get("date"), "demand": row.get("demand")} for row in reader]

    return summarize_synthetic_demand_rows(rows)


def summarize_synthetic_demand(
    db: Session | None = None,
    *,
    limit: int = MAX_SYNTHETIC_DEMAND_ROWS,
) -> dict[str, Any]:
    """Return ordered synthetic demand observations and summary stats, defaulting to CSV fallback for local use."""
    if db is None:
        return _fallback_synthetic_demand_summary()

    try:
        count_result = db.execute(
            text(
                """
                SELECT COUNT(*) AS count,
                       MIN(date)::text AS start_date,
                       MAX(date)::text AS end_date,
                       AVG(demand) AS average_demand,
                       MIN(demand) AS min_demand,
                       MAX(demand) AS max_demand
                FROM public.synthetic_demand
                """
            )
        ).mappings().first()

        observation_rows = db.execute(
            text(
                """
                SELECT date::text AS date, demand
                FROM public.synthetic_demand
                ORDER BY date ASC
                LIMIT :limit
                """
            ),
            {"limit": max(1, min(limit, MAX_SYNTHETIC_DEMAND_ROWS))},
        ).mappings().all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Synthetic demand dataset is unavailable: {exc}",
        ) from exc

    summary = {
        "count": int((count_result or {}).get("count") or 0) if count_result else 0,
        "start_date": _normalize_date((count_result or {}).get("start_date")) if count_result else None,
        "end_date": _normalize_date((count_result or {}).get("end_date")) if count_result else None,
        "average_demand": float((count_result or {}).get("average_demand") or 0.0) if count_result else 0.0,
        "min_demand": float((count_result or {}).get("min_demand") or 0.0) if count_result else 0.0,
        "max_demand": float((count_result or {}).get("max_demand") or 0.0) if count_result else 0.0,
        "observations": [
            {"date": _normalize_date(row["date"]), "demand": float(row["demand"])}
            for row in observation_rows
        ],
    }
    return summary


def _load_research_result_file(filename: str) -> dict[str, Any]:
    """Read the cached experiment summary file for research analytics."""
    path = RESEARCH_RESULTS_DIR / filename
    if not path.exists():
        return {"results": []}

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_research_analytics(db: Session | None = None) -> dict[str, Any]:
    """Return synthetic demand and experiment result payloads for the research analytics page."""
    summary = summarize_synthetic_demand(db=db, limit=MAX_SYNTHETIC_DEMAND_ROWS)
    return {
        "synthetic_demand": summary,
        "forecast_models": _load_research_result_file("forecast_models.json"),
        "horizon_sensitivity": _load_research_result_file("horizon_sensitivity.json"),
        "feature_ablation": _load_research_result_file("feature_ablation.json"),
        "cvrp_benchmark": _load_research_result_file("cvrp_benchmark.json"),
        "hgfc_advisory": _load_research_result_file("hgfc_advisory.json"),
    }


@router.get("/dashboard", response_model=FleetAnalyticsResponse)
def get_dashboard(
    current_user: User = Depends(get_current_dispatcher),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    driver_repository: DriverRepository = Depends(get_driver_repository),
    vehicle_repository: VehicleRepository = Depends(get_vehicle_repository),
    order_repository: OrderRepository = Depends(get_order_repository),
    optimization_result: OptimizationResponse | None = Depends(
        get_optimization_result_from_state
    ),
) -> FleetAnalyticsResponse:
    """Return fleet dashboard analytics metrics."""
    if not _is_dispatcher_or_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only dispatcher or admin users can access analytics.",
        )

    drivers: list[Driver] = driver_repository.get_all(skip=0, limit=10_000)
    vehicles: list[Vehicle] = vehicle_repository.get_all(skip=0, limit=10_000)
    orders: list[Order] = order_repository.get_all(skip=0, limit=10_000)

    return analytics_service.get_dashboard_metrics(
        drivers=drivers,
        vehicles=vehicles,
        orders=orders,
        optimization_result=optimization_result,
    )


@router.get("/synthetic-demand")
def get_synthetic_demand(
    current_user: User = Depends(get_current_dispatcher),
    db: Session = Depends(get_db),
    limit: int = Query(default=MAX_SYNTHETIC_DEMAND_ROWS, ge=1, le=MAX_SYNTHETIC_DEMAND_ROWS),
) -> dict[str, Any]:
    """Return ordered synthetic demand observations and summary statistics."""
    if not _is_dispatcher_or_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only dispatcher or admin users can access synthetic demand analytics.",
        )

    return summarize_synthetic_demand(db=db, limit=limit)


@router.get("/research")
def get_research_endpoint(
    current_user: User = Depends(get_current_dispatcher),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return cached experiment results and the current synthetic demand table summary."""
    if not _is_dispatcher_or_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only dispatcher or admin users can access research analytics.",
        )

    return get_research_analytics(db=db)
