"""
Authentication module for CALLSUP Audio Engine.

Each user/login represents exactly one business.
On registration the system auto-generates a UUID as business_id.
JWT tokens carry the business_id so no manual entry is ever needed.

User store: data/users.json  (simple flat file for local/dev usage)
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, field_validator

from app.config import get_settings

logger = logging.getLogger("callsup.auth")

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=True)

# ── User model ────────────────────────────────────────────────────────────────

class UserRecord(BaseModel):
    id: str
    username: str
    email: str
    password_hash: str
    salt: str
    business_id: str
    created_at: str
    business_name: str = ""


# ── User store (JSON file) ────────────────────────────────────────────────────

def _users_path() -> Path:
    settings = get_settings()
    p = Path(settings.data_dir) / "users.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_users() -> list[UserRecord]:
    p = _users_path()
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [UserRecord(**u) for u in raw]
    except Exception:
        return []


def _save_users(users: list[UserRecord]) -> None:
    p = _users_path()
    p.write_text(
        json.dumps([u.model_dump() for u in users], indent=2),
        encoding="utf-8",
    )


def _find_user_by_username(username: str) -> UserRecord | None:
    for u in _load_users():
        if u.username.lower() == username.lower():
            return u
    return None


# ── Password helpers ──────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(user: UserRecord) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "username": user.username,
        "business_id": user.business_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ── Dependency: get current user from Bearer token ────────────────────────────

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> UserRecord:
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    users = _load_users()
    for u in users:
        if u.id == user_id:
            return u
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")


# ── Request/response schemas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    business_name: str = ""

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, digits, - and _")
        return v

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    business_id: str
    username: str
    business_name: str = ""


class MeResponse(BaseModel):
    id: str
    username: str
    email: str
    business_id: str
    business_name: str = ""
    created_at: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest) -> TokenResponse:
    if _find_user_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    salt = secrets.token_hex(16)
    # Use business_name if provided, otherwise fall back to username
    effective_business_name = body.business_name.strip() if body.business_name.strip() else body.username
    user = UserRecord(
        id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        password_hash=_hash_password(body.password, salt),
        salt=salt,
        business_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        business_name=effective_business_name,
    )
    users = _load_users()
    users.append(user)
    _save_users(users)
    logger.info("user_registered username=%s business_id=%s", user.username, user.business_id)
    return TokenResponse(
        access_token=_create_token(user),
        business_id=user.business_id,
        username=user.username,
        business_name=user.business_name,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    user = _find_user_by_username(body.username)
    if not user or not _verify_password(body.password, user.salt, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    logger.info("user_login username=%s", user.username)
    return TokenResponse(
        access_token=_create_token(user),
        business_id=user.business_id,
        username=user.username,
        business_name=user.business_name,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: Annotated[UserRecord, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        business_id=current_user.business_id,
        business_name=current_user.business_name,
        created_at=current_user.created_at,
    )
