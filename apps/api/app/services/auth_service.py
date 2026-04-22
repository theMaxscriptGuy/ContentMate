import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.user import User
from app.repositories.user_repository import UserRepository

settings = get_settings()


class AuthError(Exception):
    pass


@dataclass(slots=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str | None
    avatar_url: str | None


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session=session)

    async def login_with_google(self, credential: str) -> tuple[User, str]:
        identity = await self._verify_google_credential(credential)
        user = await self._upsert_user(identity)
        token = create_access_token(user_id=user.id)
        return user, token

    async def _verify_google_credential(self, credential: str) -> GoogleIdentity:
        if not settings.google_client_id:
            raise AuthError("Google login is not configured.")

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": credential},
                )
        except httpx.HTTPError as exc:
            raise AuthError("Could not verify Google login.") from exc

        if response.status_code != 200:
            raise AuthError("Google login token was rejected.")

        payload = response.json()
        if payload.get("aud") != settings.google_client_id:
            raise AuthError("Google login token was issued for another app.")
        if payload.get("email_verified") not in (True, "true", "True"):
            raise AuthError("Google account email is not verified.")

        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise AuthError("Google login token did not include a usable identity.")

        return GoogleIdentity(
            sub=sub,
            email=email,
            name=payload.get("name"),
            avatar_url=payload.get("picture"),
        )

    async def _upsert_user(self, identity: GoogleIdentity) -> User:
        user = await self.repository.get_by_google_sub(identity.sub)
        if user is None:
            user = await self.repository.get_by_email(identity.email)

        if user is None:
            user = User(
                email=identity.email,
                google_sub=identity.sub,
                name=identity.name,
                avatar_url=identity.avatar_url,
            )
            self.session.add(user)
        else:
            user.email = identity.email
            user.google_sub = identity.sub
            user.name = identity.name
            user.avatar_url = identity.avatar_url

        await self.session.commit()
        await self.session.refresh(user)
        return user


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + settings.auth_token_ttl_seconds,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url_json(header),
            _base64url_json(payload),
        ]
    )
    signature = hmac.new(
        settings.auth_token_secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def verify_access_token(token: str) -> str:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("Invalid access token.")

    signing_input = ".".join(parts[:2])
    expected_signature = hmac.new(
        settings.auth_token_secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _base64url_decode(parts[2])
    except (binascii.Error, ValueError) as exc:
        raise AuthError("Invalid access token.") from exc
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise AuthError("Invalid access token.")

    try:
        payload = json.loads(_base64url_decode(parts[1]))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AuthError("Invalid access token.") from exc

    user_id = payload.get("sub")
    expires_at = payload.get("exp")
    if not user_id or not isinstance(expires_at, int):
        raise AuthError("Invalid access token.")
    if expires_at < int(time.time()):
        raise AuthError("Access token expired.")
    return str(user_id)


def _base64url_json(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url_encode(raw)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))
