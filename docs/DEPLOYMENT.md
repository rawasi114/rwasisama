# Deployment Runbook

Three environments, three branches, three deployment gates.

## Pipeline Overview

```
                    ┌─── PR ───┐         ┌─── PR ───┐       ┌─── Manual ───┐
dev branch ────────▶│  Tests   │────────▶│  Smoke   │──────▶│   Approval   │
(claude/...)        │ + Lint   │ staging │  + UAT   │  main │              │
                    └──────────┘         └──────────┘       └──────────────┘
                                                                      │
                                                                      ▼
                                                                 PRODUCTION
```

## Environment Configuration

| Env        | Branch                          | DB                      | Claude model         |
|------------|---------------------------------|-------------------------|----------------------|
| dev        | `claude/intelligent-carson-SAFBz`| `rawasi_pricing_dev`    | claude-sonnet-4-5    |
| staging    | `staging`                        | `rawasi_pricing_stg`    | claude-sonnet-4-5    |
| production | `main`                           | `rawasi_pricing_prod`   | claude-sonnet-4-5    |

## Dev Deployment

Continuous: every push to `claude/intelligent-carson-SAFBz` triggers:
1. `pytest` (unit + integration + e2e).
2. `ruff check api/ scripts/`.
3. `mypy api/`.
4. Docker image build, tagged `rawasi-pricing:dev-<sha>`.
5. (Optional) deploy to the dev VPS for manual testing.

## Promotion to Staging

After the dev branch has the changes you want to ship:

```bash
# 1. Create a PR from dev → staging
gh pr create --base staging --head claude/intelligent-carson-SAFBz \
  --title "Promote $(git rev-parse --short HEAD) to staging"

# 2. Merge after CI is green
# 3. Staging deploy script runs automatically on push to `staging`
```

Smoke tests to run after staging deploy:
- `GET /health` and `/health/ready` return 200.
- Create one sample tender via Swagger UI.
- Run `/analytics/go-no-go` on the sample.
- Verify the normalizer endpoint returns a candidate.

## Promotion to Production

⚠️ **Requires explicit human approval.**

```bash
# 1. Confirm staging is healthy for at least 24 hours.
# 2. Create a PR from staging → main.
gh pr create --base main --head staging --title "Release vX.Y.Z"

# 3. Get an approval from the engineering lead.
# 4. Merge — production deploy script runs automatically.

# 5. After deploy:
#    - Watch logs for the first hour.
#    - Verify the weekly quality report generates on the next Thursday.
```

## Database Migrations

The deploy script runs `alembic upgrade head` automatically.

**Safe migration practices:**
- Never drop a column in the same migration that adds its replacement —
  do it across two releases.
- Index creation on large tables should be done concurrently (PG hint:
  `CREATE INDEX CONCURRENTLY`).
- Always test on staging with realistic data volume before production.

## Rollback

```bash
# Code rollback: revert the merge commit on main.
# DB rollback: alembic downgrade -1 (only safe if no incompatible writes happened).
```

For destructive incidents, restore from the daily backup (kept 90 days
locally, 1 year cold storage).

## Monitoring

- `/health` and `/health/ready` — liveness + readiness probes.
- Logs are structured JSON in production (configured by
  `api/core/logging.py`).
- Metrics endpoint (planned): `/metrics` for Prometheus.
- Alerts go to `ALERTS_TO` (configured in `.env`).
