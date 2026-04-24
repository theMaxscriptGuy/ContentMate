"""Add unlimited analysis voucher fields to users."""

import sqlalchemy as sa

from alembic import op

revision = "20260424_0004"
down_revision = "20260422_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "has_unlimited_analysis",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("unlimited_analysis_granted_by", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "unlimited_analysis_granted_by")
    op.drop_column("users", "has_unlimited_analysis")
