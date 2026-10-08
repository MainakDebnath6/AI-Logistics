"""Create route history table."""

from alembic import op
import sqlalchemy as sa


revision = "d2e6b47a1c90"
down_revision = "5c1500f53f0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("driver_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_id", sa.UUID(), nullable=False),
        sa.Column("total_distance_km", sa.Float(), nullable=False),
        sa.Column("total_load", sa.Integer(), nullable=False),
        sa.Column("optimization_result", sa.JSON(), nullable=False),
        sa.Column("optimization_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimization_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_routes_driver_id", "routes", ["driver_id"], unique=False)
    op.create_index("ix_routes_vehicle_id", "routes", ["vehicle_id"], unique=False)
    op.create_index("ix_routes_created_at", "routes", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_routes_created_at", table_name="routes")
    op.drop_index("ix_routes_vehicle_id", table_name="routes")
    op.drop_index("ix_routes_driver_id", table_name="routes")
    op.drop_table("routes")