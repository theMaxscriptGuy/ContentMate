"""Add Google auth fields and user-scoped channel data."""

from alembic import op
import sqlalchemy as sa

revision = "20260422_0002"
down_revision = "20260421_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)

    op.drop_index(op.f("ix_channels_youtube_channel_id"), table_name="channels")
    op.create_index(
        op.f("ix_channels_youtube_channel_id"),
        "channels",
        ["youtube_channel_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_channels_user_youtube_channel",
        "channels",
        ["user_id", "youtube_channel_id"],
    )

    op.drop_index(op.f("ix_videos_youtube_video_id"), table_name="videos")
    op.create_index(
        op.f("ix_videos_youtube_video_id"),
        "videos",
        ["youtube_video_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_videos_channel_youtube_video",
        "videos",
        ["channel_id", "youtube_video_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_videos_channel_youtube_video", "videos", type_="unique")
    op.drop_index(op.f("ix_videos_youtube_video_id"), table_name="videos")
    op.create_index(
        op.f("ix_videos_youtube_video_id"),
        "videos",
        ["youtube_video_id"],
        unique=True,
    )

    op.drop_constraint("uq_channels_user_youtube_channel", "channels", type_="unique")
    op.drop_index(op.f("ix_channels_youtube_channel_id"), table_name="channels")
    op.create_index(
        op.f("ix_channels_youtube_channel_id"),
        "channels",
        ["youtube_channel_id"],
        unique=True,
    )

    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "google_sub")
