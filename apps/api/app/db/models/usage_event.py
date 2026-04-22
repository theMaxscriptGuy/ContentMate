from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UsageEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_events"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    user = relationship("User", back_populates="usage_events")
