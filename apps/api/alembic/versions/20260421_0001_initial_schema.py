"""Initial schema for ContentMate phase 1."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260421_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "channels",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("youtube_channel_id", sa.String(length=128), nullable=False),
        sa.Column("channel_url", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("default_language", sa.String(length=16), nullable=True),
        sa.Column("subscriber_count", sa.Integer(), nullable=True),
        sa.Column("video_count", sa.Integer(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_channels_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channels")),
    )
    op.create_index(op.f("ix_channels_user_id"), "channels", ["user_id"], unique=False)
    op.create_index(op.f("ix_channels_youtube_channel_id"), "channels", ["youtube_channel_id"], unique=True)

    op.create_table(
        "videos",
        sa.Column("channel_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("transcript_status", sa.String(length=32), nullable=False),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], name=op.f("fk_videos_channel_id_channels")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_videos")),
    )
    op.create_index(op.f("ix_videos_channel_id"), "videos", ["channel_id"], unique=False)
    op.create_index(op.f("ix_videos_youtube_video_id"), "videos", ["youtube_video_id"], unique=True)

    op.create_table(
        "transcripts",
        sa.Column("video_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], name=op.f("fk_transcripts_video_id_videos")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transcripts")),
        sa.UniqueConstraint("video_id", name=op.f("uq_transcripts_video_id")),
    )
    op.create_index(op.f("ix_transcripts_video_id"), "transcripts", ["video_id"], unique=True)

    op.create_table(
        "generated_content",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("prompt_input", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("asset_url", sa.String(length=500), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], name=op.f("fk_generated_content_channel_id_channels")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_generated_content_user_id_users")),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], name=op.f("fk_generated_content_video_id_videos")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_content")),
    )
    op.create_index(op.f("ix_generated_content_channel_id"), "generated_content", ["channel_id"], unique=False)
    op.create_index(op.f("ix_generated_content_user_id"), "generated_content", ["user_id"], unique=False)
    op.create_index(op.f("ix_generated_content_video_id"), "generated_content", ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_content_video_id"), table_name="generated_content")
    op.drop_index(op.f("ix_generated_content_user_id"), table_name="generated_content")
    op.drop_index(op.f("ix_generated_content_channel_id"), table_name="generated_content")
    op.drop_table("generated_content")
    op.drop_index(op.f("ix_transcripts_video_id"), table_name="transcripts")
    op.drop_table("transcripts")
    op.drop_index(op.f("ix_videos_youtube_video_id"), table_name="videos")
    op.drop_index(op.f("ix_videos_channel_id"), table_name="videos")
    op.drop_table("videos")
    op.drop_index(op.f("ix_channels_youtube_channel_id"), table_name="channels")
    op.drop_index(op.f("ix_channels_user_id"), table_name="channels")
    op.drop_table("channels")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
