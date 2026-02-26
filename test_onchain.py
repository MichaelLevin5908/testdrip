"""
test_onchain.py — test charges with a real onchain address
Uses 0xBF6d400400645FD357A097c7a37fBd78924be274 as the payment address.

Expected results:
  - Customer creation ✅
  - Charges → INSUFFICIENT_BALANCE (correct — $0 USDC on address)
  - Usage events / runs ✅ (don't require balance)
  - Settlement → "No pending proofs" (correct — no settled charges yet)

To make charges go through, the address needs USDC on Base Sepolia.
"""
import os, sys, uuid, httpx

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("❌  DRIP_API_KEY not set"); sys.exit(1)

from drip import Drip

drip = Drip(api_key=API_KEY, base_url=API_URL)

ONCHAIN_ADDRESS = "0xBF6d400400645FD357A097c7a37fBd78924be274"
run_id = uuid.uuid4().hex[:8]

passed, failed, skipped = 0, 0, 0

def ok(label: str, detail: str = "") -> None:
    global passed
    passed += 1
    print(f"  ✅  {label}" + (f"  →  {detail}" if detail else ""))

def fail(label: str, err: Exception) -> None:
    global failed
    msg = str(err)
    code = getattr(err, "code", None) or getattr(err, "error_code", None)
    if code:
        msg = f"{msg} [{code}]"
    print(f"  ❌  {label}\n       {msg}")
    failed += 1

def skip(label: str, reason: str) -> None:
    global skipped
    skipped += 1
    print(f"  ⚠️   {label} — {reason}")

def section(title: str) -> None:
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


# ─────────────────────────────────────────────────────────────
section("1. CREATE CUSTOMER WITH ONCHAIN ADDRESS")
# ─────────────────────────────────────────────────────────────
CUSTOMER_ID = None
try:
    customer = drip.create_customer(
        external_customer_id=f"onchain_user_{run_id}",
        onchain_address=ONCHAIN_ADDRESS,
    )
    CUSTOMER_ID = customer.id
    ok("Customer created with onchain address",
       f"id={customer.id}, addr={customer.onchain_address}")
except Exception as e:
    code = getattr(e, "code", None) or getattr(e, "error_code", None)
    if code == "DUPLICATE_CUSTOMER":
        # Address already linked — look up the existing customer
        resp = httpx.get(
            f"{API_URL}/customers",
            headers={"Authorization": f"Bearer {API_KEY}"},
            params={"onchainAddress": ONCHAIN_ADDRESS},
            timeout=10,
        )
        data = resp.json()
        if data.get("data"):
            CUSTOMER_ID = data["data"][0]["id"]
            ok("Customer already exists (reusing)",
               f"id={CUSTOMER_ID}, addr={ONCHAIN_ADDRESS}")
        else:
            fail("Lookup existing customer", e)
    else:
        fail("Create customer with onchain address", e)


# ─────────────────────────────────────────────────────────────
section("2. CHARGE — api_calls, tokens, compute_seconds")
# Note: expects INSUFFICIENT_BALANCE (402) — address has $0 USDC.
#       This proves the billing engine IS reaching the balance check.
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    for meter, qty, cost in [("api_calls", 10, 0.01), ("tokens", 4000, 0.04), ("compute_seconds", 30, 0.003)]:
        try:
            result = drip.charge(customer_id=CUSTOMER_ID, meter=meter, quantity=qty)
            ok(f"charge({meter}, qty={qty})", repr(result))
        except Exception as e:
            code = getattr(e, "code", None) or getattr(e, "error_code", None)
            if code == "PAYMENT_REQUIRED":
                skip(f"charge({meter}, qty={qty})",
                     f"INSUFFICIENT_BALANCE — address has $0 USDC, needs ${cost:.3f}. Fund address to enable charges.")
            else:
                fail(f"charge({meter}, qty={qty})", e)
else:
    skip("charge tests", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("3. RUN WITH EVENTS (no balance needed)")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    try:
        with drip.run(customer_id=CUSTOMER_ID,
                      workflow=f"llm-pipeline-{run_id}",
                      metadata={"model": "claude-3-5-sonnet", "env": "prod"}) as run:
            run.event("input.tokens", quantity=1200, units="tokens")
            run.event("tool.call", quantity=3, units="tool_calls")
            run.event("output.tokens", quantity=800, units="tokens")
        ok("Agent run with 3 events", f"run_id={run.run_id}")

        timeline = drip.get_run_timeline(run.run_id)
        ok("Timeline retrieved", f"{len(timeline.timeline)} events, status={timeline.run.status}")
    except Exception as e:
        fail("Run with events", e)
else:
    skip("Run with events", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("4. MULTI-EVENT BATCH (no balance needed)")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    try:
        with drip.run(customer_id=CUSTOMER_ID, workflow=f"batch-workflow-{run_id}") as batch_run:
            events = drip.emit_events_batch([
                {"runId": batch_run.run_id, "eventType": "step.start", "quantity": 1, "units": "steps"},
                {"runId": batch_run.run_id, "eventType": "tokens.in", "quantity": 500, "units": "tokens"},
                {"runId": batch_run.run_id, "eventType": "tokens.out", "quantity": 300, "units": "tokens"},
            ])
        ok("emit_events_batch (3 events)", f"created={events.created}, dupes={events.duplicates}")
    except Exception as e:
        fail("emit_events_batch", e)
else:
    skip("Batch events", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("5. BALANCE CHECK")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    try:
        balance = drip.get_balance(CUSTOMER_ID)
        avail = getattr(balance, 'available_balance', getattr(balance, 'available', None))
        ok("get_balance", f"available=${float(avail):.6f} USDC" if avail is not None else str(balance))
    except Exception as e:
        fail("get_customer_balance", e)
else:
    skip("Balance check", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("6. LIST CHARGES (shows 0 — expected without USDC)")
# ─────────────────────────────────────────────────────────────
try:
    charges = drip.list_charges()
    ok("list_charges()", f"count={charges.count} (charges need funded address to accumulate)")
except Exception as e:
    fail("list_charges()", e)


# ─────────────────────────────────────────────────────────────
section("7. PLAYGROUND DEMO-SETTLE")
# ─────────────────────────────────────────────────────────────
try:
    host = API_URL
    if not host.endswith("/v1"):
        host = host.rstrip("/")
    resp = httpx.post(
        f"{host}/playground/demo-settle",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={},
        timeout=30,
    )
    data = resp.json()
    if resp.status_code == 200:
        ok("playground/demo-settle", str(data))
    else:
        skip("playground/demo-settle", str(data))
except Exception as e:
    fail("playground/demo-settle", e)


# ─────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print(f"  RESULTS:  ✅ {passed} passed   ❌ {failed} failed   ⚠️  {skipped} skipped")
print(f"{'═'*60}")
print(f"\n  Customer ID: {CUSTOMER_ID}")
print(f"  Onchain:     {ONCHAIN_ADDRESS}")
print(f"  → Fund this address with USDC on Base Sepolia to enable charges")
print(f"  → Faucet: https://faucet.circle.com (select Base Sepolia)\n")
sys.exit(0 if failed == 0 else 1)
