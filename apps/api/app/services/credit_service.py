from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.credit_ledger_entry import CreditLedgerEntry
from app.db.models.user import User
from app.db.models.user_credit_account import UserCreditAccount


class CreditError(Exception):
    pass


class InsufficientCreditsError(CreditError):
    pass


@dataclass(slots=True)
class CreditStatus:
    balance: int
    lifetime_credited: int
    lifetime_used: int


class CreditService:
    ANALYSIS_COST_CREDITS = 1

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_credit_status(self, user_id: str) -> CreditStatus:
        account = await self._get_or_create_account(user_id=user_id)
        return CreditStatus(
            balance=account.balance,
            lifetime_credited=account.lifetime_credited,
            lifetime_used=account.lifetime_used,
        )

    async def grant_credits(
        self,
        *,
        user_id: str,
        credits: int,
        reason: str,
        reference_id: str | None = None,
    ) -> CreditStatus:
        if credits <= 0:
            raise CreditError("Credits granted must be positive.")

        account = await self._get_or_create_account(user_id=user_id)
        account.balance += credits
        account.lifetime_credited += credits
        self.session.add(
            CreditLedgerEntry(
                user_id=user_id,
                account_id=account.id,
                delta=credits,
                balance_after=account.balance,
                reason=reason,
                reference_id=reference_id,
            )
        )
        await self.session.commit()
        await self.session.refresh(account)
        return await self.get_credit_status(user_id=user_id)

    async def consume_analysis_credit(
        self,
        *,
        user_id: str,
        reference_id: str | None = None,
    ) -> CreditStatus:
        account = await self._get_or_create_account(user_id=user_id)
        if account.balance < self.ANALYSIS_COST_CREDITS:
            raise InsufficientCreditsError("Not enough credits. Buy credits to continue.")

        account.balance -= self.ANALYSIS_COST_CREDITS
        account.lifetime_used += self.ANALYSIS_COST_CREDITS
        self.session.add(
            CreditLedgerEntry(
                user_id=user_id,
                account_id=account.id,
                delta=-self.ANALYSIS_COST_CREDITS,
                balance_after=account.balance,
                reason="analysis_run",
                reference_id=reference_id,
            )
        )
        await self.session.commit()
        await self.session.refresh(account)
        return await self.get_credit_status(user_id=user_id)

    async def _get_or_create_account(self, user_id: str) -> UserCreditAccount:
        user = await self.session.get(User, user_id)
        if user is None:
            raise CreditError("User not found.")

        query = select(UserCreditAccount).where(UserCreditAccount.user_id == user_id)
        result = await self.session.execute(query)
        account = result.scalar_one_or_none()
        if account is not None:
            return account

        account = UserCreditAccount(user_id=user_id)
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account
