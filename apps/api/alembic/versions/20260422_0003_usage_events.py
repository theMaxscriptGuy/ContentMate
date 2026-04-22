"""Add usage events for daily analysis limits."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260422_0003"
down_revision = "20260422_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=500), nullable=True),
        sa.Column("counted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_usage_events_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_events")),
    )
    op.create_index(op.f("ix_usage_events_action_type"), "usage_events", ["action_type"], unique=False)
    op.create_index(op.f("ix_usage_events_counted_at"), "usage_events", ["counted_at"], unique=False)
    op.create_index(op.f("ix_usage_events_user_id"), "usage_events", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_user_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_counted_at"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_action_type"), table_name="usage_events")
    op.drop_table("usage_events")
