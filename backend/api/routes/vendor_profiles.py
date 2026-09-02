"""
Vision — Vendor Profile API Routes.

Registration creates a user + profile in one call. Profile CRUD is
permissioned: vendor can edit their own, admin can edit all.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import create_user, get_current_user, VALID_ROLES
from core.vendor_profile import VendorProfileManager, VALID_VENDOR_TYPES

router = APIRouter(prefix="/api/vendors", tags=["vendors"])
mgr = VendorProfileManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class VendorRegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    business_name: str
    vendor_type: str = "service"         # individual | service | manufacturer
    phone: str | None = None
    website: str | None = None
    uei: str | None = None
    cage_code: str | None = None
    tax_id: str | None = None
    naics_codes: list[str] | None = None
    capabilities: str | None = None


class VendorProfileUpdate(BaseModel):
    business_name: str | None = None
    vendor_type: str | None = None
    uei: str | None = None
    cage_code: str | None = None
    tax_id: str | None = None
    naics_codes: list[str] | None = None
    capabilities: str | None = None
    website: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    bonding_capacity: float | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    years_in_business: int | None = None
    status: str | None = None          # admin only


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
def register_vendor(body: VendorRegisterRequest):
    """Register a new vendor — creates user (role=vendor) + profile."""
    if body.vendor_type not in VALID_VENDOR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"vendor_type must be one of: {sorted(VALID_VENDOR_TYPES)}",
        )
    if len(body.password) < 6:
        raise HTTPException(
            status_code=400, detail="password must be at least 6 characters"
        )

    # Create the user account
    user = create_user(
        username=body.username,
        password=body.password,
        email=body.email,
        role="vendor",
    )

    # Create the vendor profile
    profile = mgr.create(
        user_id=user["id"],
        business_name=body.business_name,
        vendor_type=body.vendor_type,
        phone=body.phone,
        website=body.website,
        uei=body.uei,
        cage_code=body.cage_code,
        tax_id=body.tax_id,
        naics_codes=body.naics_codes,
        capabilities=body.capabilities,
    )

    return {"user": user, "profile": profile}


@router.get("/profiles")
def list_profiles(
    status: str | None = None,
    vendor_type: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List vendor profiles. Admin or internal users only."""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="Access denied")
    return {"profiles": mgr.list(status=status, vendor_type=vendor_type)}


@router.get("/profile")
def get_my_profile(
    user: dict = Depends(get_current_user),
):
    """Get the current vendor's profile."""
    profile = mgr.get_by_user(user["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="No vendor profile found")
    return profile


@router.patch("/profile")
def update_my_profile(
    body: VendorProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update the current vendor's profile."""
    profile = mgr.get_by_user(user["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="No vendor profile found")

    kwargs = {}
    for field, val in body.model_dump(exclude_none=True).items():
        # Only admin can change status
        if field == "status" and user["role"] != "admin":
            continue
        kwargs[field] = val

    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated = mgr.update(profile["id"], **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return updated
