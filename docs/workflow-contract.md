# Workflow API contract (for the conversation service)

Base URL (compose): `http://workflow-api:8001`, or `http://localhost:8001` from the host.
This is the Person 2 side of the contract. The shared request/response schema with the
conversation service (Breakdown task 3) will be agreed on top of this.

## Supported requests

| Request | Steps | Verification | Required fields | Endpoint |
|---|---|---|---|---|
| CHECK_POLICY_STATUS | IDENTIFY → DONE | no | policy_id | `GET /policies/{policy_id}` |
| REQUEST_REFUND | IDENTIFY → VERIFY → COLLECT → EXECUTE → DONE | yes | policy_id, amount, reason | `POST /refund-requests` |
| UPDATE_BANK_ACCOUNT | IDENTIFY → VERIFY → COLLECT → EXECUTE → DONE | yes | holder_name, account_number, ifsc | `PATCH /customers/{customer_id}/bank-account` |

Source of truth: `backend/mock_insurance_api/app/workflows.py`.

## Response envelope (every response, including errors)

```json
{
  "status": "SUCCESS | NEEDS_INFO | REJECTED | FAILED",
  "code": "REFUND_CREATED",
  "message": "Plain sentence the agent can say or paraphrase.",
  "data": {},
  "missing_fields": [],
  "invalid_fields": [{"field": "ifsc", "reason": "IFSC must look like HDFC0001234"}]
}
```

How the agent should react:
- `SUCCESS`: say `message`, or build a reply from `data`.
- `NEEDS_INFO`: ask the caller for everything in `missing_fields`, and re-ask for everything in `invalid_fields` (read out `reason`).
- `REJECTED`: explain `message`. If `code` is `VERIFICATION_REQUIRED`, run verification and retry.
- `FAILED`: apologise and offer to try again.

## Endpoints

| Method & path | Header | Body | Success |
|---|---|---|---|
| `GET /health` | — | — | 200 `OK` |
| `GET /customers/{id}` | — | — | 200 `CUSTOMER_FOUND`, `data.customer` (masked contact details, no DOB) |
| `GET /policies/{id}` | — | — | 200 `POLICY_FOUND`, `data.policy` |
| `POST /verifications` | — | `{customer_id, policy_id, date_of_birth: "YYYY-MM-DD", session_id?}` | 201 `VERIFIED`, `data.token`, `data.expires_in_seconds` |
| `POST /refund-requests` | `X-Verification-Token`, optional `Idempotency-Key` | `{policy_id, amount, reason, session_id?}` | 201 `REFUND_CREATED` / 200 `REFUND_ALREADY_CREATED`, `data.refund` |
| `PATCH /customers/{id}/bank-account` | `X-Verification-Token` | `{holder_name, account_number, ifsc, session_id?}` | 200 `BANK_ACCOUNT_UPDATED`, `data.bank_account` (masked) |

Notes:
- IDs are forgiving: `pol 3001`, `POL3001` and `pol-3001` all mean `POL-3001`.
- `account_number` must be sent as a **string** (leading zeros matter). Spaces are stripped.
- `amount` can be a number or a string, with at most 2 decimal places, in INR.
- Use one `Idempotency-Key` per caller intent (e.g. `<session_id>-refund-<n>`). Retries with the same key and body return the original refund.
- Pass `session_id` so the operations log can be joined to the conversation.

## Error codes

| Code | HTTP | Meaning |
|---|---|---|
| MISSING_FIELDS / INVALID_FIELDS | 422 | see `missing_fields` / `invalid_fields` |
| CUSTOMER_NOT_FOUND / POLICY_NOT_FOUND | 404 | unknown ID |
| VERIFICATION_FAILED | 401 | details don't match (deliberately doesn't say which) |
| VERIFICATION_LOCKED | 423 | 3 failures in 15 min for this customer |
| VERIFICATION_REQUIRED | 401 | no, invalid or expired token |
| TOKEN_SCOPE_MISMATCH | 403 | token belongs to another customer |
| POLICY_NOT_ACTIVE | 409 | refund on a lapsed or cancelled policy |
| AMOUNT_EXCEEDS_PREMIUM | 409 | refund larger than the premium |
| REFUND_ALREADY_OPEN | 409 | `data.open_refund_id` has the existing request |
| IDEMPOTENCY_KEY_CONFLICT | 409 | key reused for a different refund |
| HOLDER_NAME_MISMATCH | 403 | new account isn't in the customer's name |
| SAME_ACCOUNT | 409 | same account as on file |
| ROUTE_NOT_FOUND / METHOD_NOT_ALLOWED | 404 / 405 | wrong URL or method |
| INTERNAL_ERROR | 500 | unexpected; safe to retry |
