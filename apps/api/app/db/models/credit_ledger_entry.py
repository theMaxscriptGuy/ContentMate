from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreditLedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "credit_ledger_entries"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("user_credit_accounts.id"),
        index=True,
        nullable=False,
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user = relationship("User", back_populates="credit_ledger_entries")
    account = relationship("UserCreditAccount", back_populates="ledger_entries")
