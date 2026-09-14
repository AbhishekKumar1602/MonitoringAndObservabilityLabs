-- Executed only when the PostgreSQL data volume is first initialized.
-- SQLAlchemy creates the application tables; this script prepares useful
-- extensions and preserves a clear initialization hook for later labs.

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

COMMENT ON DATABASE orders IS
  'Orders database used by the single-VM observability training environment';

