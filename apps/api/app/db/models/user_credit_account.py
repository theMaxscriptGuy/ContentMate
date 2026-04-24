from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserCreditAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_credit_accounts"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        index=True,
        nullable=False,
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lifetime_credited: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    lifetime_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    user = relationship("User", back_populates="credit_account")
    ledger_entries = relationship(
        "CreditLedgerEntry",
        back_populates="account",
        cascade="all, delete-orphan",
    )
