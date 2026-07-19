#!/usr/bin/env bash
# Create dedicated Postgres database silverman_linkedin_db on local-ai-stack Postgres.
# Run as a Postgres superuser (example: docker exec into the postgres container).
# Do not commit passwords; set ROLE password via operator secret store.
set -euo pipefail

DB_NAME="${SILVERMAN_LINKEDIN_DB_NAME:-silverman_linkedin_db}"
ROLE_NAME="${SILVERMAN_LINKEDIN_DB_ROLE:-silverman_linkedin}"

psql -v ON_ERROR_STOP=1 <<SQL
SELECT 'Creating role ${ROLE_NAME} if missing';
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${ROLE_NAME}') THEN
    CREATE ROLE ${ROLE_NAME} LOGIN PASSWORD 'CHANGE_ME';
  END IF;
END
\$\$;

SELECT 'Creating database ${DB_NAME} if missing';
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${ROLE_NAME}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${ROLE_NAME};
SQL

echo "Next: set SILVERMAN_CALENDAR_DATABASE_URL=postgresql://${ROLE_NAME}:***@postgres:5432/${DB_NAME}"
echo "Then start the worker and run schema ensure on first calendar load, or import via:"
echo "  python -m silverman_blog_linkedin.editorial_calendar_import --base-path /data/silverman-blog-linkedin"
