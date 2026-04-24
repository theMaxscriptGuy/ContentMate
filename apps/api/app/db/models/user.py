from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    google_sub: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    has_unlimited_analysis: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    unlimited_analysis_granted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    channels = relationship("Channel", back_populates="user")
    credit_account = relationship(
        "UserCreditAccount",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    credit_ledger_entries = relationship("CreditLedgerEntry", back_populates="user")
    generated_content = relationship("GeneratedContent", back_populates="user")
    usage_events = relationship("UsageEvent", back_populates="user")
