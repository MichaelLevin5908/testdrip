"""
test_remaining.py — covers everything not yet tested:
  1. get_or_create_customer() (Python SDK)
  2. POST /usage/internal
  3. POST /usage/async
  4. GET /charges/:id
  5. GET /playground/status
  6. GET /sandbox/status
  7. POST /sandbox/seed-runs
  8. POST /playground/create-proof
  9. Auto-settlement via ProofSettlementWorker (accumulate $5+ → wait for auto-trigger)
"""
import os, sys, uuid, time, httpx

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("❌  DRIP_API_KEY not set"); sys.exit(1)

from drip import Drip
drip = Drip(api_key=API_KEY, base_url=API_URL)

run_id = uuid.uuid4().hex[:8]
passed, failed, skipped = 0, 0, 0

def ok(label: str, detail: str = "") -> None:
    global passed; passed += 1
    print(f"  ✅  {label}" + (f"  →  {detail}" if detail else ""))

def fail(label: str, err) -> None:
    global failed
    msg = f"{err}"
    print(f"  ❌  {label}\n       {msg}")
    failed += 1

def skip(label: str, reason: str) -> None:
    global skipped; skipped += 1
    print(f"  ⚠️   {label} — {reason}")

def section(title: str) -> None:
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def api(method: str, path: str, **kwargs):
    r = httpx.request(
        method, f"{API_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60, **kwargs
    )
    return r.json(), r.status_code

# Known provisioned customer from earlier tests
PROVISIONED_CUSTOMER_ID = "cmm3eut3b0001ew6l0ivjabgh"   # auto_prov_851993d5
PROVISIONED_SMART_ACCOUNT = "0x63bdeBcA47FFBC374bB3811d1173C96283e0cEf3"

# ─────────────────────────────────────────────────────────────
section("1. get_or_create_customer() — idempotent customer creation")
# ─────────────────────────────────────────────────────────────
GOC_CUSTOMER = None
try:
    ext_id = f"goc_test_{run_id}"
    c1 = drip.get_or_create_customer(external_customer_id=ext_id)
    ok("get_or_create_customer (first call)", f"id={c1.id}, ext={c1.external_customer_id}")

    # Call again with same ext_id — should return same customer
    c2 = drip.get_or_create_customer(external_customer_id=ext_id)
    if c1.id == c2.id:
        ok("get_or_create_customer (idempotent)", f"same id={c2.id}")
    else:
        fail("get_or_create_customer idempotency", Exception(f"Different ids: {c1.id} vs {c2.id}"))
    GOC_CUSTOMER = c1
except Exception as e:
    fail("get_or_create_customer", e)


# ─────────────────────────────────────────────────────────────
section("2. GET /charges/:id — fetch single charge")
# ─────────────────────────────────────────────────────────────
try:
    charges = drip.list_charges()
    if charges.count > 0 and charges.data:
        charge_id = charges.data[0].id
        charge = drip.get_charge(charge_id)
        ok("get_charge by id", f"id={charge.id}, status={charge.status}, amt={charge.amount_usdc}")
    else:
        skip("get_charge", "no charges in account")
except Exception as e:
    fail("get_charge", e)


# ─────────────────────────────────────────────────────────────
section("3. GET /charges/:id/status — charge status endpoint")
# ─────────────────────────────────────────────────────────────
try:
    charges = drip.list_charges()
    if charges.count > 0 and charges.data:
        charge_id = charges.data[0].id
        data, status = api("GET", f"/charges/{charge_id}/status")
        if status == 200:
            ok("GET /charges/:id/status", f"id={data.get('id')}, status={data.get('status')}, confirmed={data.get('confirmedAt','?')[:10] if data.get('confirmedAt') else 'N/A'}")
        else:
            fail("GET /charges/:id/status", Exception(str(data)))
    else:
        skip("GET /charges/:id/status", "no charges in account")
except Exception as e:
    fail("GET /charges/:id/status", e)


# ─────────────────────────────────────────────────────────────
section("4. POST /usage/internal — visibility-only tracking (no billing)")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", "/usage/internal", json={
        "customerId": PROVISIONED_CUSTOMER_ID,
        "usageType": "api_calls",
        "quantity": 5,
        "idempotencyKey": f"internal_{run_id}",
        "description": "Visibility-only tracking test",
        "metadata": {"source": "test_remaining"},
    })
    if status in (200, 201):
        ok("POST /usage/internal", f"eventId={data.get('usageEventId','?')}, isDuplicate={data.get('isDuplicate')}")
    else:
        fail("POST /usage/internal", Exception(f"HTTP {status}: {data}"))
except Exception as e:
    fail("POST /usage/internal", e)


# ─────────────────────────────────────────────────────────────
section("5. POST /usage/async — async charge (returns PENDING immediately)")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", "/usage/async", json={
        "customerId": PROVISIONED_CUSTOMER_ID,
        "usageType": "api_calls",
        "quantity": 1,
        "idempotencyKey": f"async_{run_id}",
    })
    if status == 202:
        charge_status = data.get("charge", {}).get("status", "?")
        ok("POST /usage/async", f"status={charge_status}, chargeId={data.get('charge',{}).get('id','?')[:20]}")
        ok("Returns 202 immediately", f"message={data.get('message','?')[:60]}")
    elif status == 200:
        ok("POST /usage/async (200 fallback)", f"status={data.get('charge',{}).get('status','?')}")
    else:
        fail("POST /usage/async", Exception(f"HTTP {status}: {data}"))
except Exception as e:
    fail("POST /usage/async", e)


# ─────────────────────────────────────────────────────────────
section("6. GET /playground/status")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("GET", "/playground/status")
    if status == 200:
        ok("GET /playground/status", f"available={data.get('available')}, network={data.get('network')}, chainId={data.get('chainId')}")
    else:
        fail("GET /playground/status", Exception(f"HTTP {status}: {data}"))
except Exception as e:
    fail("GET /playground/status", e)


# ─────────────────────────────────────────────────────────────
section("7. GET /sandbox/status")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("GET", "/sandbox/status")
    if status == 200:
        stats = data.get("stats", {})
        ok("GET /sandbox/status", f"exists={data.get('exists')}, customers={stats.get('customers')}, runs={stats.get('runs')}")
    else:
        fail("GET /sandbox/status", Exception(f"HTTP {status}: {data}"))
except Exception as e:
    fail("GET /sandbox/status", e)


# ─────────────────────────────────────────────────────────────
section("8. POST /sandbox/seed-runs — add sample data")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", "/sandbox/seed-runs", json={"count": 2})
    if status == 200:
        ok("POST /sandbox/seed-runs", f"created={data.get('created','?')}, msg={str(data)[:80]}")
    else:
        fail("POST /sandbox/seed-runs", Exception(f"HTTP {status}: {data}"))
except Exception as e:
    fail("POST /sandbox/seed-runs", e)


# ─────────────────────────────────────────────────────────────
section("9. POST /playground/create-proof — create PaymentProof")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", "/playground/create-proof", json={
        "walletAddress": PROVISIONED_SMART_ACCOUNT,
        "amount": "0.5",
    })
    if status == 200:
        proof = data.get("proof", {})
        ok("create-proof", f"proofId={proof.get('id','?')}, amount={proof.get('amountUsdc','?')}, status={proof.get('status','?')}")
    else:
        fail("POST /playground/create-proof", Exception(f"HTTP {status}: {data}"))
except Exception as e:
    fail("POST /playground/create-proof", e)


# ─────────────────────────────────────────────────────────────
section("10. AUTO-SETTLEMENT — accumulate $5+ charges → wait for worker")
# ─────────────────────────────────────────────────────────────
print(f"  Creating 6x api_calls charges at qty=1000 ($1 each) = $6 total...")
print(f"  Using customer: {PROVISIONED_CUSTOMER_ID}")

try:
    total_charged = 0.0
    charge_ids = []
    for i in range(6):
        r = drip.charge(
            customer_id=PROVISIONED_CUSTOMER_ID,
            meter="api_calls",
            quantity=1000,
            idempotency_key=f"auto_settle_{run_id}_{i}",
            metadata={"batch": i, "source": "auto_settlement_test"},
        )
        if r.charge:
            total_charged += float(r.charge.amount_usdc)
            if r.charge.id:
                charge_ids.append(r.charge.id)
            print(f"    charge {i+1}: ${r.charge.amount_usdc} → status={r.charge.status}")

    ok(f"Accumulated ${total_charged:.2f} in PENDING_SETTLEMENT charges", f"(threshold is $5.00)")

    # Now poll the worker status for up to 90 seconds
    print(f"\n  Waiting up to 90s for ProofSettlementWorker to auto-settle...")
    settled = False
    for attempt in range(9):
        time.sleep(10)
        wdata, _ = api("GET", "/settlements/worker-status")
        last_success = wdata.get("lastSuccess")
        candidates = wdata.get("candidatesFound", 0)
        settled_hour = wdata.get("settledThisHour", 0)
        runs = wdata.get("metrics", {}).get("runsTotal", 0)
        print(f"    t+{(attempt+1)*10}s: runs={runs}, candidatesFound={candidates}, settledThisHour={settled_hour}, lastSuccess={'✅' if last_success else '❌ null'}")

        if last_success:
            ok("Auto-settlement triggered!", f"lastSuccess={last_success}, settledThisHour={settled_hour}")
            settled = True
            break

    if not settled:
        # Check if charges changed status
        data, _ = api("GET", f"/charges/{charge_ids[0]}/status") if charge_ids else ({}, 0)
        charge_status = data.get("status", "unknown")
        if charge_status == "CONFIRMED":
            ok("Auto-settlement triggered (charges confirmed)", f"chargeStatus={charge_status}")
        else:
            fail("Auto-settlement", Exception(
                f"Worker ran but no settlement occurred after 90s. "
                f"Charge status: {charge_status}. "
                f"This likely means BILLING_MODULE_ADDRESS/BILLING_AUTHORITY_PRIVATE_KEY "
                f"are not configured in production. Use demo-settle as workaround."
            ))

except Exception as e:
    code = getattr(e, "code", None) or getattr(e, "error_code", None)
    if code == "PAYMENT_REQUIRED":
        skip("Auto-settlement test", "INSUFFICIENT_BALANCE — customer needs more USDC")
    else:
        fail("Auto-settlement test", e)


# ─────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print(f"  RESULTS:  ✅ {passed} passed   ❌ {failed} failed   ⚠️  {skipped} skipped")
print(f"{'═'*60}\n")
sys.exit(0 if failed == 0 else 1)
