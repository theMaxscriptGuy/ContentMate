from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Video(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id"), index=True, nullable=False)
    youtube_video_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcript_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    channel = relationship("Channel", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False)
    generated_content = relationship("GeneratedContent", back_populates="video")
