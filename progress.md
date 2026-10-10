# Progress — Workflow Backend (Person 2, Daksh)

Running log of what's been decided and built for the mock insurance workflow service.
Source of truth for scope: `Breakdown.md` → "Person 2 — Workflow Backend & Product Integration".

## Scope (agreed)

Building now (no dependency on Person 1):
- Task 1 — Insurance workflow APIs (customers, policies, refund requests, bank-account update)
- Task 2 — Business logic (supported requests, workflow states, validation, failure handling)
- Task 4 — Supabase/Postgres tables + seed data
- Task 5a — Docker for the workflow service, API tests, reproducible demo scenarios
- Extra: server-side caller verification before sensitive actions

Deferred until Aditya's conversation service exists:
- Task 3 — Backend integration / shared request-response schema with Person 1
- Task 5b — Compose with Person 1's service + cross-service integration tests

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-10 | REST endpoints exactly as listed in Breakdown.md, no `/actions` gateway yet | Follow the breakdown; gateway shape needs Person 1's input |
| 2026-10-10 | Postgres via SQLAlchemy + Alembic; local Postgres in Docker for dev/tests, hosted Supabase for demo | Fast isolated tests, demo works offline, one `DATABASE_URL` switch |
| 2026-10-10 | Only the four tables from Breakdown.md: customers, policies, refund_requests, operations | Follow the breakdown; bank details live on customers, history in operations |
| 2026-10-10 | Server-side verification (`POST /verifications`) issuing short-lived signed tokens | The voice agent can't talk its way past it; clean seam for the AegisCall layer |
| 2026-10-10 | One response envelope (`status`, `code`, `message`, `data`, `missing_fields`, `invalid_fields`) on every endpoint | Breakdown asks for structured results the voice agent can explain |
| 2026-10-10 | Optional `Idempotency-Key` on refund creation | Voice agents retry on timeouts; avoid duplicate refunds |

## Status

- [x] Read Breakdown.md, agreed scope
- [x] Design: service layout + data model
- [x] Design: API contract
- [ ] Design: business rules, testing, Docker, demo scenarios
- [ ] Written spec
- [ ] Implementation plan
- [ ] Implementation

## Log

### 2026-10-10
- Went through Breakdown.md and split my tasks into "independent" vs "needs Aditya".
- Settled service layout, data model and API contract.
