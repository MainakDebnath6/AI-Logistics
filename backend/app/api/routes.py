"""Read-only API for persisted optimized route summaries."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_dispatcher
from app.models.user import User
from app.repositories.route_repository import RouteRepository
from app.schemas.route import RouteResponse

router = APIRouter(prefix="/routes", tags=["Routes"])


def get_route_repository(db: Session = Depends(get_db)) -> RouteRepository:  # noqa: B008
    """Create a route repository for the active database session."""
    return RouteRepository(db)


@router.get("/", response_model=list[RouteResponse])
def list_routes(
    skip: int = 0,
    limit: int = 100,
    _current_user: User = Depends(get_current_dispatcher),  # noqa: B008
    repository: RouteRepository = Depends(get_route_repository),  # noqa: B008
) -> list[RouteResponse]:
    """Return persisted routes, newest first."""
    return repository.get_all(skip=skip, limit=limit)


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: UUID,
    _current_user: User = Depends(get_current_dispatcher),  # noqa: B008
    repository: RouteRepository = Depends(get_route_repository),  # noqa: B008
) -> RouteResponse:
    """Return one persisted route by ID."""
    route = repository.get_by_id(route_id)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found.",
        )
    return route