"""
SQLAlchemy 2.0 ORM models — Sprint 4 multi-tenant foundation.

Tables (all with tenant_id for RLS):
- tenants
- users
- documents
- content_blocks (denormalized tenant_id for RLS perf)
- usage_logs (per-tenant token/cost/latency tracking)
- subscriptions (Sprint 5 billing)

Migrations live in `migrations/` (Alembic). See `alembic.ini`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON}


# ============================================================
# Tenant + User
# ============================================================

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")  # free|pro|enterprise
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user")  # admin|teacher|student|user
    accessibility_prefs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # tts_rate, pitch, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
    )


# ============================================================
# Documents + Content Blocks
# ============================================================

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[Optional[str]] = mapped_column(String(1024))  # S3/R2 key
    total_pages: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|processing|done|failed
    model_used: Mapped[str] = mapped_column(String(100), default="gemini-2.5-flash")
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    blocks: Mapped[list["ContentBlockRow"]] = relationship("ContentBlockRow", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        Index("ix_documents_tenant_created", "tenant_id", "created_at"),
    )


class ContentBlockRow(Base):
    __tablename__ = "content_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)  # denormalized for RLS perf
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    block_id: Mapped[str] = mapped_column(String(50))  # block_001, block_002...
    type: Mapped[str] = mapped_column(String(20))  # text|math|chart|table|figure
    raw_content: Mapped[str] = mapped_column(Text)
    latex: Mapped[Optional[str]] = mapped_column(Text)
    spoken_text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="vi")
    confidence: Mapped[float] = mapped_column(Float)
    page: Mapped[int] = mapped_column(Integer)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    w: Mapped[float] = mapped_column(Float)
    h: Mapped[float] = mapped_column(Float)
    region: Mapped[str] = mapped_column(String(20))
    # Sprint 4 extensions
    reading_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    importance: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    alt_text_long: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mathml: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    aria_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="blocks")

    __table_args__ = (
        Index("ix_blocks_tenant_doc", "tenant_id", "document_id"),
        Index("ix_blocks_doc_block", "document_id", "block_id", unique=True),
    )


# ============================================================
# Usage tracking + Subscriptions (Sprint 5)
# ============================================================

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(200))
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    audio_seconds: Mapped[Optional[float]] = mapped_column(Float)  # for TTS billing
    pages_processed: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_usage_tenant_time", "tenant_id", "created_at"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"))
    plan: Mapped[str] = mapped_column(String(50))  # free|pro|enterprise
    provider: Mapped[Optional[str]] = mapped_column(String(50))  # paddle|payos|vnpay|momo
    external_id: Mapped[Optional[str]] = mapped_column(String(255))  # Paddle subscription ID, etc.
    status: Mapped[str] = mapped_column(String(50), default="active")  # active|past_due|canceled
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    quotas: Mapped[Optional[dict]] = mapped_column(JSON)  # {"pages_per_month": 50, ...}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# ============================================================
# RLS helper SQL (apply via Alembic migration)
# ============================================================
RLS_SQL_TEMPLATE = """
-- Apply Row-Level Security on tenant-scoped tables
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON {table};
CREATE POLICY tenant_isolation ON {table}
  USING (tenant_id::text = current_setting('app.tenant_id', true));
"""

RLS_TABLES = ["users", "documents", "content_blocks", "usage_logs", "subscriptions"]
