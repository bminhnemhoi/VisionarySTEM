"""Test auth/tenant context resolution."""
import os
import pytest


def test_single_mode_default_tenant(monkeypatch):
    """In single mode, every request gets DEFAULT tenant with admin role."""
    import src.config
    monkeypatch.setattr(src.config, "TENANT_MODE", "single")
    from src.auth import tenant
    monkeypatch.setattr(tenant, "TENANT_MODE", "single")

    import asyncio
    ctx = asyncio.run(tenant.get_tenant_context(authorization=None, x_tenant_id=None))
    assert ctx.tenant_id == "default"
    assert ctx.user_id == "anonymous"
    assert ctx.is_admin is True


def test_multi_mode_no_auth_returns_anon(monkeypatch):
    """In multi mode without token, returns anonymous (won't 401 from soft dep)."""
    import src.config
    from src.auth import tenant
    monkeypatch.setattr(tenant, "TENANT_MODE", "multi")

    import asyncio
    ctx = asyncio.run(tenant.get_tenant_context(authorization=None, x_tenant_id=None))
    assert ctx.tenant_id == "default"
    assert ctx.is_authenticated is False


def test_multi_mode_x_tenant_header(monkeypatch):
    """X-Tenant-Id header lets dev/test bypass JWT (insecure for prod)."""
    from src.auth import tenant
    monkeypatch.setattr(tenant, "TENANT_MODE", "multi")

    import asyncio
    ctx = asyncio.run(tenant.get_tenant_context(authorization=None, x_tenant_id="tenant-abc"))
    assert ctx.tenant_id == "tenant-abc"
    assert ctx.is_authenticated is False  # header-based ≠ authenticated


def test_tenant_context_admin_property():
    from src.auth.tenant import TenantContext
    assert TenantContext("t", "u", role="admin").is_admin
    assert TenantContext("t", "u", role="owner").is_admin
    assert not TenantContext("t", "u", role="user").is_admin
