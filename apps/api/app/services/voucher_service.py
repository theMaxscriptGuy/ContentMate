from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.user import User

settings = get_settings()


class VoucherError(Exception):
    pass


class VoucherService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def redeem_unlimited_analysis_voucher(self, user: User, code: str) -> User:
        normalized = self._normalize(code)
        if not normalized:
            raise VoucherError("Enter a voucher code.")

        valid_codes = self._valid_codes()
        if normalized not in valid_codes:
            raise VoucherError("Voucher code is invalid.")

        user.has_unlimited_analysis = True
        user.unlimited_analysis_granted_by = normalized
        await self.session.commit()
        await self.session.refresh(user)
        return user

    @staticmethod
    def _normalize(code: str) -> str:
        return code.strip().upper()

    @staticmethod
    def _valid_codes() -> set[str]:
        return {
            item.strip().upper()
            for item in settings.unlimited_analysis_voucher_codes.split(",")
            if item.strip()
        }
