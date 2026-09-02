"""
Vision — Authentication.

JWT-based auth with bcrypt password hashing. Self-contained in the vision
database (users table matches main war_room app schema for future sync).

Usage:
    from auth import create_user, authenticate, create_token, get_current_user
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import psycopg2.extras
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.db import connect, tx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET = os.environ.get("VISION_JWT_SECRET", "vision-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

security = HTTPBearer()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

VALID_ROLES = {"user", "admin", "vendor"}


def create_user(username: str, password: str, email: str | None = None,
                role: str = "user") -> dict:
    """Register a new user. Returns user dict without password_hash."""
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role!r}")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)

    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            try:
                cur.execute(
                    """INSERT INTO users (id, username, email, password_hash, role)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING id, username, email, role, is_active,
                                 created_at, updated_at""",
                    (user_id, username, email, pw_hash, role),
                )
                return dict(cur.fetchone())
            except psycopg2.errors.UniqueViolation:
                raise HTTPException(
                    status_code=409,
                    detail=f"Username '{username}' already exists",
                )


def authenticate_user(username: str, password: str) -> dict | None:
    """Validate credentials. Returns user dict without password_hash, or None."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s AND is_active = true",
                (username,),
            )
            user = cur.fetchone()
    finally:
        conn.close()

    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None

    # Update last_login
    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login = now() WHERE id = %s",
                (user["id"],),
            )

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": str(user["created_at"]),
    }


def get_user_by_id(user_id: str) -> dict | None:
    """Get user by ID. Returns user dict without password_hash."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, email, role, is_active, created_at, updated_at "
                "FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_token(user: dict) -> str:
    """Create a JWT for the given user dict."""
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# FastAPI dependencies — use in protected routes
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency. Extracts and validates JWT, returns user dict.

    Usage:
        @app.get("/api/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user}
    """
    payload = decode_token(credentials.credentials)
    user = get_user_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active"):
        raise HTTPException(status_code=401, detail="Account disabled")
    return user


async def require_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    """FastAPI dependency. Same as get_current_user but also enforces admin role.

    Usage:
        @app.post("/api/admin/users")
        def create_user(user: dict = Depends(require_admin)):
            ...
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_mta(
    user: dict = Depends(get_current_user),
) -> dict:
    """FastAPI dependency. Vendors must have an executed Master Teaming
    Agreement (MTA) to access quote-request flows; JQ staff roles pass.

    The gate derives from the vendor_teaming_agreements row — no
    denormalized profile column.

    Usage:
        @app.get("/api/vendors/quotes")
        def list_quotes(user: dict = Depends(require_mta)):
            ...
    """
    if user.get("role") == "vendor":
        from core.db import connect
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM vendor_teaming_agreements "
                    "WHERE vendor_user_id = %s AND agreement_type = 'mta' "
                    "AND status = 'executed' LIMIT 1",
                    (user["id"],),
                )
                if cur.fetchone() is None:
                    raise HTTPException(
                        status_code=403,
                        detail="Master Teaming Agreement required. "
                               "Please sign your MTA in the vendor portal.",
                    )
        finally:
            conn.close()
    return user


# ---------------------------------------------------------------------------
# Admin user management (used by /api/admin/users routes)
# ---------------------------------------------------------------------------

def list_users() -> list[dict]:
    """Return all users (without password_hash). Admin only."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, email, role, is_active, "
                "last_login, created_at, updated_at "
                "FROM users ORDER BY created_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_user(user_id: str, **kwargs) -> dict | None:
    """Update user fields. Only provided kwargs are changed.

    Allowed keys: email, role, is_active.
    Returns the updated user dict without password_hash, or None if not found.
    """
    allowed = {"email", "role", "is_active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_user_by_id(user_id)

    set_parts = []
    values = []
    for k, v in updates.items():
        set_parts.append(f"{k} = %s")
        values.append(v)
    values.append(user_id)

    with tx() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(set_parts)}, updated_at = now() "
                f"WHERE id = %s "
                f"RETURNING id, username, email, role, is_active, "
                f"last_login, created_at, updated_at",
                tuple(values),
            )
            row = cur.fetchone()
            return dict(row) if row else None
