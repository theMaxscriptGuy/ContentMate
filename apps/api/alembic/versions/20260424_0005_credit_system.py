"""Add user credit accounts and ledger."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260424_0005"
down_revision = "20260424_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_credit_accounts",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lifetime_credited", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lifetime_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_credit_accounts_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_credit_accounts")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_credit_accounts_user_id")),
    )
    op.create_index(
        op.f("ix_user_credit_accounts_user_id"),
        "user_credit_accounts",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "credit_ledger_entries",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("reference_id", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["user_credit_accounts.id"],
            name=op.f("fk_credit_ledger_entries_account_id_user_credit_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_credit_ledger_entries_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_ledger_entries")),
    )
    op.create_index(
        op.f("ix_credit_ledger_entries_account_id"),
        "credit_ledger_entries",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_credit_ledger_entries_user_id"),
        "credit_ledger_entries",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_credit_ledger_entries_user_id"), table_name="credit_ledger_entries")
    op.drop_index(op.f("ix_credit_ledger_entries_account_id"), table_name="credit_ledger_entries")
    op.drop_table("credit_ledger_entries")
    op.drop_index(op.f("ix_user_credit_accounts_user_id"), table_name="user_credit_accounts")
    op.drop_table("user_credit_accounts")
