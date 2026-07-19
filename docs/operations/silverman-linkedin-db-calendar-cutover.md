# Operator checklist: `silverman_linkedin_db` calendar cutover (BL-031 / US-041)

Implemented in worker code ≠ live cutover. Complete these steps on `192.168.0.194` before treating calendar APIs as production-ready against Postgres.

## 1. Create database

On `local-ai-stack` Postgres (superuser):

```bash
# See deploy/server/create-silverman-linkedin-db.sh
# Database name MUST be exactly: silverman_linkedin_db
```

Set a dedicated role password in the operator secret store (never commit).

## 2. Configure worker

In `/home/silverman/silverman-blog-linkedin-worker/.env` (example shape only):

```bash
SILVERMAN_CALENDAR_DATABASE_URL=postgresql://silverman_linkedin:***@postgres:5432/silverman_linkedin_db
```

Compose already forwards `SILVERMAN_CALENDAR_DATABASE_URL` (see `deploy/server/silverman-worker.compose.yaml`). Redeploy/recreate the worker container after setting the env.

## 3. Verify health

```bash
curl -sS http://127.0.0.1:8010/health | jq '{status,folders_ready,calendar_store,calendar_store_ready,calendar_database}'
```

Expect `calendar_database=silverman_linkedin_db` and `calendar_store_ready=true` when Postgres is reachable.

## 4. Optional import

Only if a valid legacy `calendar.json` exists and the DB has **zero** items:

```bash
docker exec -e SILVERMAN_CALENDAR_DATABASE_URL=... silverman-blog-linkedin-worker \
  python -m silverman_blog_linkedin.editorial_calendar_import \
  --base-path /data/silverman-blog-linkedin
```

Refuse/clobber: default refuses non-empty DB.

## 5. Functional smoke

- `GET /editorial-calendar/status` (authenticated)
- `GET /flow-a/schedule-visibility?year=&month=`
- Console Week/Month still loads without claiming wiped historical rows were restored

## Out of scope

- Restoring calendar rows wiped on 2026-07-18 without an external copy
- Migrating campaign metadata or LinkedIn Markdown into Postgres
