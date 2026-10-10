# Demo scenarios — mock insurance API

Every scenario here is also an automated test in `tests/integration/test_demo_scenarios.py`.

## Setup

```bash
docker compose up -d --build
docker compose run --rm workflow-api python -m seed.seed --reset
API=http://localhost:8001
```

Re-run the seed command with `--reset` before each demo run to clear old refunds, the audit log and any verification lockouts.

Helper to get a token for Priya (CUST-1001):

```bash
TOKEN=$(curl -s -X POST $API/verifications -H 'content-type: application/json' \
  -d '{"customer_id":"CUST-1001","policy_id":"POL-3001","date_of_birth":"1990-04-12"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['token'])")
```

| Customer | Name | DOB | Policies |
|---|---|---|---|
| CUST-1001 | Priya Sharma | 1990-04-12 | POL-3001 health, active, premium ₹18,000 |
| CUST-1002 | Arjun Nair | 1985-11-02 | POL-3002 motor, lapsed |
| CUST-1003 | Meera Iyer | 1978-01-25 | POL-3003 life, POL-3004 health (both active) |
| CUST-1004 | Rohan Gupta | 1995-07-30 | POL-3005 motor, active, no bank account |
| CUST-1005 | Ananya Reddy | 2000-03-08 | POL-3006 health, cancelled |

## 1. Policy status lookup → `SUCCESS / POLICY_FOUND`

```bash
curl -s $API/policies/POL-3001
```

## 2. Verify, then raise a refund → `SUCCESS / REFUND_CREATED`

```bash
curl -s -X POST $API/refund-requests -H 'content-type: application/json' -H "X-Verification-Token: $TOKEN" \
  -d '{"policy_id":"POL-3001","amount":1200,"reason":"Charged twice for March premium"}'
```

## 3. Refund with no amount → `NEEDS_INFO / MISSING_FIELDS`, `missing_fields: ["amount"]`

```bash
curl -s -X POST $API/refund-requests -H 'content-type: application/json' -H "X-Verification-Token: $TOKEN" \
  -d '{"policy_id":"POL-3001","reason":"Charged twice"}'
```

## 4. Bank change without verifying → `REJECTED / VERIFICATION_REQUIRED`

```bash
curl -s -X PATCH $API/customers/CUST-1001/bank-account -H 'content-type: application/json' \
  -d '{"holder_name":"Priya Sharma","account_number":"123456789012","ifsc":"ICIC0000789"}'
```

## 5. Wrong DOB three times → 4th attempt `REJECTED / VERIFICATION_LOCKED`

```bash
for i in 1 2 3; do
  curl -s -X POST $API/verifications -H 'content-type: application/json' \
    -d '{"customer_id":"CUST-1001","policy_id":"POL-3001","date_of_birth":"1991-01-01"}'; echo
done
curl -s -X POST $API/verifications -H 'content-type: application/json' \
  -d '{"customer_id":"CUST-1001","policy_id":"POL-3001","date_of_birth":"1990-04-12"}'
```

Run the seed with `--reset` afterwards, or Priya stays locked for 15 minutes.

## 6. Bank change to someone else's name → `REJECTED / HOLDER_NAME_MISMATCH`

```bash
curl -s -X PATCH $API/customers/CUST-1001/bank-account -H 'content-type: application/json' \
  -H "X-Verification-Token: $TOKEN" \
  -d '{"holder_name":"Rahul Mehta","account_number":"123456789012","ifsc":"ICIC0000789"}'
```

## 7. Retry with the same Idempotency-Key → 201, then 200 with the same refund

Run the seed with `--reset` first, so that scenario 2's refund isn't still open.

```bash
for i in 1 2; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST $API/refund-requests -H 'content-type: application/json' \
    -H "X-Verification-Token: $TOKEN" -H 'Idempotency-Key: demo-call-1' \
    -d '{"policy_id":"POL-3001","amount":1200,"reason":"Charged twice for March premium"}'
done
```
