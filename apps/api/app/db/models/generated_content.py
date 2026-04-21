from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeneratedContent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generated_content"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("channels.id"), index=True, nullable=True)
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id"), index=True, nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_input: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    asset_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    user = relationship("User", back_populates="generated_content")
    channel = relationship("Channel", back_populates="generated_content")
    video = relationship("Video", back_populates="generated_content")
