"""Idempotently seed deterministic development/demo logistics records."""

from __future__ import annotations

import os
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.driver import Driver, DriverStatus
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from sqlalchemy import select
from sqlalchemy.orm import Session


def _demo_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"ai-logistics-demo:{name}")


def _ensure_user(
    session: Session,
    *,
    name: str,
    full_name: str,
    email: str,
    password: str,
    role: UserRole,
) -> tuple[User, bool]:
    user_id = _demo_id(name)
    user = session.get(User, user_id)
    if user is not None:
        return user, False

    existing = session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ValueError(f"Cannot seed {email}: that email belongs to another user ID.")

    user = User(
        id=user_id,
        full_name=full_name,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user, True


def seed_demo(
    session: Session,
    *,
    admin_password: str,
    driver_password: str,
) -> dict[str, int]:
    """Insert demo entities if absent; never overwrite existing records."""
    created = {"users": 0, "vehicles": 0, "drivers": 0, "orders": 0}
    try:
        _admin, was_created = _ensure_user(
            session,
            name="admin",
            full_name="Demo Dispatcher",
            email="dispatcher@demo.local",
            password=admin_password,
            role=UserRole.ADMIN,
        )
        created["users"] += int(was_created)
        driver_user, was_created = _ensure_user(
            session,
            name="driver-user",
            full_name="Demo Driver",
            email="driver@demo.local",
            password=driver_password,
            role=UserRole.DRIVER,
        )
        created["users"] += int(was_created)

        vehicle_id = _demo_id("vehicle-1")
        vehicle = session.get(Vehicle, vehicle_id)
        if vehicle is None:
            existing_vehicle = session.scalar(
                select(Vehicle).where(Vehicle.registration_number == "DEMO-TRUCK-001")
            )
            if existing_vehicle is not None:
                raise ValueError("Cannot seed DEMO-TRUCK-001: registration is already in use.")
            vehicle = Vehicle(
                id=vehicle_id,
                registration_number="DEMO-TRUCK-001",
                model="Transit 350",
                manufacturer="Demo Fleet",
                capacity=60,
                status=VehicleStatus.AVAILABLE,
                is_active=True,
            )
            session.add(vehicle)
            session.flush()
            created["vehicles"] += 1

        driver_id = _demo_id("driver-1")
        driver = session.get(Driver, driver_id)
        if driver is None:
            existing_driver = session.scalar(
                select(Driver).where(Driver.license_number == "DEMO-LICENSE-001")
            )
            if existing_driver is not None:
                raise ValueError("Cannot seed DEMO-LICENSE-001: license is already in use.")
            driver = Driver(
                id=driver_id,
                user_id=driver_user.id,
                license_number="DEMO-LICENSE-001",
                phone="555-010-1001",
                vehicle_id=vehicle.id,
                status=DriverStatus.AVAILABLE,
                max_capacity=vehicle.capacity,
                is_available=True,
            )
            session.add(driver)
            session.flush()
            created["drivers"] += 1

        orders = [
            ("order-1", "North Market", 8, 41.8900, -87.6400),
            ("order-2", "River Cafe", 12, 41.9000, -87.6300),
            ("order-3", "West Books", 15, 41.8800, -87.6600),
            ("order-4", "South Supply", 10, 41.8600, -87.6400),
        ]
        for order_name, customer, demand, latitude, longitude in orders:
            order_id = _demo_id(order_name)
            if session.get(Order, order_id) is not None:
                continue
            session.add(
                Order(
                    id=order_id,
                    customer_name=customer,
                    customer_phone="555-010-2000",
                    pickup_address="Central Depot, Chicago",
                    delivery_address=f"{customer}, Chicago",
                    pickup_latitude=41.8781,
                    pickup_longitude=-87.6298,
                    delivery_latitude=latitude,
                    delivery_longitude=longitude,
                    demand=demand,
                    priority=1,
                    status=OrderStatus.PENDING,
                )
            )
            created["orders"] += 1

        session.commit()
    except Exception:
        session.rollback()
        raise

    return created


def main() -> None:
    """Run the seed command only in explicitly non-production environments."""
    settings = get_settings()
    if "environment" not in settings.model_fields_set:
        raise SystemExit("Set ENVIRONMENT explicitly before running the demo seed.")

    environment = settings.environment.strip().lower()
    if environment not in {"development", "demo", "test"}:
        raise SystemExit("Demo seeding is disabled outside development/demo/test environments.")

    admin_password = os.getenv("DEMO_ADMIN_PASSWORD")
    driver_password = os.getenv("DEMO_DRIVER_PASSWORD")
    if not admin_password or not driver_password:
        raise SystemExit(
            "Set DEMO_ADMIN_PASSWORD and DEMO_DRIVER_PASSWORD in the environment first."
        )

    with SessionLocal() as session:
        counts = seed_demo(
            session,
            admin_password=admin_password,
            driver_password=driver_password,
        )
    print("Demo seed complete: " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()