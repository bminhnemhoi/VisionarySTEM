# Multi-Tenant SaaS Architecture với FastAPI + PostgreSQL RLS

## Pattern khuyến nghị: Shared DB + Row-Level Security (RLS)
**Lý do**: rẻ nhất, dễ vận hành, đủ isolation cho B2B trường học/NGO. Nếu khách enterprise đòi separate DB → có path nâng cấp.

## Kiến trúc 5-tầng cho VisionarySTEM
```
┌──────────────────────────────────────────────────────┐
│  Edge / CDN (Cloudflare)                              │
├──────────────────────────────────────────────────────┤
│  Auth Layer (Auth0/Supabase Auth/Clerk)               │
│  - Multi-tenant aware: tenant_id trong JWT claims     │
├──────────────────────────────────────────────────────┤
│  FastAPI Layer                                        │
│  - Middleware extract tenant_id từ JWT                │
│  - Set DB session: SET app.tenant_id = :tid           │
│  - Rate-limit theo tenant_id                          │
├──────────────────────────────────────────────────────┤
│  PostgreSQL với RLS                                   │
│  - Mọi table có cột tenant_id                         │
│  - RLS policy: USING (tenant_id = current_setting(    │
│        'app.tenant_id')::uuid)                         │
│  - Connection pool 2 user: app_admin (no RLS) +        │
│        app_user (RLS enforce)                          │
├──────────────────────────────────────────────────────┤
│  Storage: S3-compatible (MinIO local / R2 cloud)      │
│  - Path: tenants/{tenant_id}/uploads/{doc_id}/        │
│  - Signed URL ngắn hạn (15 phút)                       │
└──────────────────────────────────────────────────────┘
```

## Bảng cốt lõi cần thiết kế
- `tenants(id, name, plan, created_at, ...)`
- `users(id, tenant_id, email, role, ...)` — role: admin/teacher/student
- `documents(id, tenant_id, filename, status, ...)`
- `content_blocks(id, document_id, tenant_id, ...)` (denormalize tenant_id để RLS)
- `tts_audio(id, block_id, tenant_id, voice, audio_url, ...)`
- `usage_logs(id, tenant_id, endpoint, tokens, cost_usd, latency_ms, ...)` — cho billing
- `subscriptions(id, tenant_id, plan, billing_cycle, ...)`

## RLS template
```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
  USING (tenant_id::text = current_setting('app.tenant_id', true));
```

## FastAPI middleware pattern
```python
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    tenant_id = decode_jwt(token).get("tenant_id")
    request.state.tenant_id = tenant_id
    # set khi mở session DB
    return await call_next(request)
```

## Pitfalls thường gặp
- **Connection pooling + session vars**: phải reset `app.tenant_id` mỗi lần lấy connection. Dùng `SET LOCAL` trong transaction để tự reset.
- **Bypass cho admin queries**: dùng user `app_admin` riêng, đừng disable RLS.
- **Test forced isolation**: viết test cố tình không set tenant_id → RLS phải block.
- **Migrations**: chạy bằng user `app_admin`, không cần RLS bypass.

## Stack hoàn chỉnh đề xuất
- **DB**: PostgreSQL 16 (managed: Supabase / Neon)
- **ORM**: SQLAlchemy 2.0 async + Alembic
- **Auth**: Supabase Auth (rẻ, có VN-friendly UI) hoặc Clerk
- **Object storage**: Cloudflare R2 (rẻ, không egress fee)
- **Queue**: Redis + RQ hoặc Celery cho async TTS/analyze
- **Observability**: Logfire (FastAPI native) hoặc OpenTelemetry → Grafana

## Sources
- [AWS RLS Multi-tenant guide](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)
- [FastAPI Multi-Tenant SaaS](https://medium.com/@hjparmar1944/fastapi-multi-tenant-saas-row-level-security-without-pain-9ef960085bf4)
- [FastAPI 5 Isolation Patterns](https://medium.com/@ThinkingLoop/fastapi-multi-tenancy-5-isolation-patterns-that-scale-f381c50e262e)
- [Madeeha-Anjum sample repo](https://github.com/Madeeha-Anjum/multi-tenancy-system)
