from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Channel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "channels"
    __table_args__ = (
        UniqueConstraint("user_id", "youtube_channel_id", name="uq_channels_user_youtube_channel"),
    )

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    youtube_channel_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    channel_url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    default_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    subscriber_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="channels")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
    generated_content = relationship("GeneratedContent", back_populates="channel")
