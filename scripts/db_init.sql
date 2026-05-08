-- VisionarySTEM Postgres init
-- Runs once when container first starts (via docker-entrypoint-initdb.d/)

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application user (separate from migration user) for RLS enforcement
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vs_app') THEN
    CREATE ROLE vs_app LOGIN PASSWORD 'vs_app_pwd';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE visionarystem TO vs_app;
GRANT USAGE ON SCHEMA public TO vs_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO vs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vs_app;

-- Note: RLS policies are applied via Alembic migrations (see src/db/models.py RLS_SQL_TEMPLATE)
-- Migration user `vs` (POSTGRES_USER) bypasses RLS via BYPASSRLS or by being table owner.
