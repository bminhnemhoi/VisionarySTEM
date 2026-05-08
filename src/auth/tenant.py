"""
Tenant context resolution.

In `TENANT_MODE=single` (cuộc thi): returns a constant DEFAULT tenant.
In `TENANT_MODE=multi` (production): extracts tenant_id from JWT claims.

Used as a FastAPI dependency:
    @app.post("/...")
    async def handler(tenant: TenantContext = Depends(require_tenant)):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, status

from src.config import TENANT_MODE


DEFAULT_TENANT_ID = "default"
DEFAULT_USER_ID = "anonymous"


@dataclass
class TenantContext:
    tenant_id: str
    user_id: str
    role: str = "user"
    is_authenticated: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "owner")


def _decode_jwt(token: str) -> dict:
    """
    Decode JWT and return claims. Stub for Sprint 4 — Sprint 5 will use python-jose.

    Expected claims: sub (user_id), tenant_id, role, exp.
    """
    try:
        from jose import jwt as jose_jwt
        from src.config import JWT_SECRET, JWT_ALGORITHM
        return jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT auth requested but python-jose not installed. pip install 'python-jose[cryptography]'.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def get_tenant_context(
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> TenantContext:
    """
    Returns TenantContext for the request. Soft dependency — won't 401 if no auth.

    For endpoints that REQUIRE auth, use `require_tenant` instead.
    """
    if TENANT_MODE == "single":
        return TenantContext(
            tenant_id=DEFAULT_TENANT_ID,
            user_id=DEFAULT_USER_ID,
            role="admin",  # in single mode, every request is admin
            is_authenticated=False,
        )

    # Multi-tenant: try JWT, fall back to header (for testing)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        claims = _decode_jwt(token)
        return TenantContext(
            tenant_id=claims.get("tenant_id") or DEFAULT_TENANT_ID,
            user_id=claims.get("sub") or DEFAULT_USER_ID,
            role=claims.get("role", "user"),
            is_authenticated=True,
        )

    # Fallback: X-Tenant-Id header (for dev/testing)
    if x_tenant_id:
        return TenantContext(
            tenant_id=x_tenant_id,
            user_id="header-user",
            role="user",
            is_authenticated=False,
        )

    return TenantContext(
        tenant_id=DEFAULT_TENANT_ID,
        user_id=DEFAULT_USER_ID,
        role="anonymous",
        is_authenticated=False,
    )


async def require_tenant(
    ctx: TenantContext = None,  # populated by FastAPI Depends below
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> TenantContext:
    """Strict variant: in multi mode, must have authenticated tenant."""
    ctx = await get_tenant_context(authorization, x_tenant_id)
    if TENANT_MODE == "multi" and not ctx.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
        )
    return ctx
