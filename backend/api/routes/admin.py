"""
Vision — Admin API Routes.

User management for admin users: create, list, update, disable users.
All endpoints require admin role (enforced via require_admin dependency).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import create_user, list_users, update_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    role: str = "user"


class UpdateUserRequest(BaseModel):
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/users", status_code=201)
def create_user_endpoint(
    body: CreateUserRequest,
    user: dict = Depends(require_admin),
):
    """Create a new user. Admin only."""
    if body.role not in ("user", "admin"):
        raise HTTPException(
            status_code=400, detail="role must be 'user' or 'admin'"
        )
    if len(body.password) < 6:
        raise HTTPException(
            status_code=400, detail="password must be at least 6 characters"
        )
    return create_user(
        username=body.username,
        password=body.password,
        email=body.email,
        role=body.role,
    )


@router.get("/users")
def list_users_endpoint(
    user: dict = Depends(require_admin),
):
    """List all users. Admin only."""
    return {"users": list_users()}


@router.patch("/users/{user_id}")
def update_user_endpoint(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
):
    """Update a user (email, role, is_active). Admin only."""
    if body.role is not None and body.role not in ("user", "admin"):
        raise HTTPException(
            status_code=400, detail="role must be 'user' or 'admin'"
        )

    # Prevent admin from disabling themselves
    if body.is_active is False and user_id == admin["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot disable your own account",
        )

    updates = {}
    if body.email is not None:
        updates["email"] = body.email
    if body.role is not None:
        updates["role"] = body.role
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = update_user(user_id, **updates)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated
