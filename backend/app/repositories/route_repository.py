"""Database access helpers for route persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.route import Route


class RouteRepository:
    """Encapsulate SQLAlchemy operations for route records."""

    def __init__(self, db: Session) -> None:
        """Initialize the repository with a database session."""

        self.db = db

    def create(self, route: Route) -> Route:
        """Persist a new route and return the stored object."""

        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route

    def get_by_id(self, route_id: UUID) -> Route | None:
        """Return a route by primary key if it exists."""

        statement = select(Route).where(Route.id == route_id)
        return self.db.scalar(statement)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Route]:
        """Return routes ordered by newest first with pagination."""

        statement = (
            select(Route)
            .order_by(Route.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_by_driver(self, driver_id: UUID) -> list[Route]:
        """Return routes assigned to the given driver."""

        statement = (
            select(Route)
            .where(Route.driver_id == driver_id)
            .order_by(Route.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_by_vehicle(self, vehicle_id: UUID) -> list[Route]:
        """Return routes assigned to the given vehicle."""

        statement = (
            select(Route)
            .where(Route.vehicle_id == vehicle_id)
            .order_by(Route.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def delete(self, route: Route) -> None:
        """Delete a route from the database."""

        self.db.delete(route)
        self.db.commit()
