# Mock Insurance API (workflow backend)

Person 2's slice of AegisCall Phase 1: a mock insurance backend the voice agent calls to look
up customers and policies, verify callers, raise refund requests and change bank details.

- Design: `docs/superpowers/specs/2026-10-10-workflow-backend-design.md`
- API contract for the conversation service: `docs/workflow-contract.md`
- Demo walkthrough: `docs/demo-scenarios.md`

## Run it

```bash
docker compose up -d --build                                      # Postgres + API on :8001
docker compose run --rm workflow-api python -m seed.seed --reset  # demo data
curl http://localhost:8001/health
```

Interactive docs: http://localhost:8001/docs

## Develop and test (from the repo root)

```bash
uv sync --project backend/mock_insurance_api
docker compose up -d db
uv run --project backend/mock_insurance_api pytest tests/integration -q
```

Tests use the `aegiscall_test` database on `localhost:5433`. Override it with `TEST_DATABASE_URL`.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5433/aegiscall` | `postgresql://` / `postgres://` URLs (e.g. from Supabase) are accepted as-is |
| `TOKEN_SECRET` | `dev-only-change-me` | **Set a real secret for any shared deployment** |
| `VERIFICATION_TTL_SECONDS` | `600` | verification token lifetime |

## Using hosted Supabase

```bash
export DATABASE_URL="postgresql://postgres.<project>:<password>@<host>:5432/postgres"
uv run --project backend/mock_insurance_api alembic -c backend/mock_insurance_api/alembic.ini upgrade head
uv run --project backend/mock_insurance_api python -m seed.seed
```
