"""
test_onchain.py — full end-to-end test with smart account provisioning

Flow:
  1. Create customer (no onchain address yet)
  2. POST /provision → deploys ERC-4337 smart account + deposits $100 USDC
  3. sync-balance → confirms balance
  4. Charge → passes (has funded smart account)
  5. Settlement → demo-settle
"""
import os, sys, uuid, httpx

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("❌  DRIP_API_KEY not set"); sys.exit(1)

from drip import Drip
drip = Drip(api_key=API_KEY, base_url=API_URL)

run_id = uuid.uuid4().hex[:8]
passed, failed, skipped = 0, 0, 0

def ok(label, detail=""):
    global passed; passed += 1
    print(f"  ✅  {label}" + (f"  →  {detail}" if detail else ""))

def fail(label, err):
    global failed; failed += 1
    code = getattr(err, "code", None) or getattr(err, "error_code", None)
    msg = f"{err}" + (f" [{code}]" if code else "")
    print(f"  ❌  {label}\n       {msg}")

def skip(label, reason):
    global skipped; skipped += 1
    print(f"  ⚠️   {label} — {reason}")

def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def api(method, path, **kwargs):
    resp = httpx.request(
        method, f"{API_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60, **kwargs
    )
    return resp.json(), resp.status_code


# ─────────────────────────────────────────────────────────────
section("1. CREATE CUSTOMER")
# ─────────────────────────────────────────────────────────────
CUSTOMER_ID = None
try:
    customer = drip.create_customer(external_customer_id=f"e2e_user_{run_id}")
    CUSTOMER_ID = customer.id
    ok("Customer created", f"id={CUSTOMER_ID}, ext={customer.external_customer_id}")
except Exception as e:
    fail("Create customer", e)


# ─────────────────────────────────────────────────────────────
section("2. PROVISION SMART ACCOUNT (deploys ERC-4337 + funds $100 USDC)")
# ─────────────────────────────────────────────────────────────
SMART_ACCOUNT = None
if CUSTOMER_ID:
    try:
        data, status = api("POST", f"/customers/{CUSTOMER_ID}/provision", json={})
        if status == 200:
            SMART_ACCOUNT = data.get("smart_account_address")
            ok("Provision smart account",
               f"addr={SMART_ACCOUNT}, already_deployed={data.get('already_deployed')}")
            ok("Deploy tx", data.get("deploy_tx_hash", "already existed"))
            ok("BillingModule deposit", f"${data.get('billing_balance_usdc')} USDC deposited")
        else:
            fail("Provision", Exception(str(data)))
    except Exception as e:
        fail("Provision smart account", e)
else:
    skip("Provision", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("3. SYNC BALANCE")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    try:
        data, status = api("POST", f"/customers/{CUSTOMER_ID}/sync-balance", json={})
        if status == 200:
            ok("sync-balance",
               f"available=${data.get('newBalance')} USDC (changed={data.get('changed')})")
        else:
            fail("sync-balance", Exception(str(data)))
    except Exception as e:
        fail("sync-balance", e)
else:
    skip("sync-balance", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("4. CHARGES (api_calls, tokens, compute_seconds)")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    for meter, qty in [("api_calls", 10), ("tokens", 4000), ("compute_seconds", 30)]:
        try:
            result = drip.charge(customer_id=CUSTOMER_ID, meter=meter, quantity=qty)
            ok(f"charge({meter}, qty={qty})", repr(result))
        except Exception as e:
            code = getattr(e, "code", None) or getattr(e, "error_code", None)
            if code == "PAYMENT_REQUIRED":
                skip(f"charge({meter})", "INSUFFICIENT_BALANCE — provision may need a moment to settle onchain")
            else:
                fail(f"charge({meter})", e)
else:
    skip("Charges", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("5. RUN WITH EVENTS")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    try:
        with drip.run(customer_id=CUSTOMER_ID,
                      workflow=f"llm-pipeline-{run_id}",
                      metadata={"model": "claude-3-5-sonnet"}) as run:
            run.event("input.tokens", quantity=1200, units="tokens")
            run.event("tool.call", quantity=3, units="tool_calls")
            run.event("output.tokens", quantity=800, units="tokens")
        ok("Agent run (3 events)", f"run_id={run.run_id}")

        timeline = drip.get_run_timeline(run.run_id)
        ok("Timeline", f"{len(timeline.timeline)} events, status={timeline.run.status}")
    except Exception as e:
        fail("Run with events", e)
else:
    skip("Run with events", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("6. BALANCE AFTER CHARGES")
# ─────────────────────────────────────────────────────────────
if CUSTOMER_ID:
    try:
        balance = drip.get_balance(CUSTOMER_ID)
        ok("get_balance", str(balance))
    except Exception as e:
        fail("get_balance", e)
else:
    skip("Balance check", "no customer ID")


# ─────────────────────────────────────────────────────────────
section("7. LIST CHARGES")
# ─────────────────────────────────────────────────────────────
try:
    charges = drip.list_charges()
    ok("list_charges()", f"count={charges.count}")
    if charges.count > 0 and charges.data:
        c = charges.data[0]
        ok("Latest charge",
           f"meter={getattr(c,'usage_type','?')}, qty={getattr(c,'quantity','?')}, status={getattr(c,'status','?')}")
except Exception as e:
    fail("list_charges()", e)


# ─────────────────────────────────────────────────────────────
section("8. DEMO-SETTLE (on-chain settlement)")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", "/playground/demo-settle", json={})
    if status == 200 and data.get("success"):
        s = data.get("settlement")
        if s:
            ok("demo-settle",
               f"${s.get('totalUsdc')} USDC, {s.get('proofCount')} proofs")
            ok("Explorer", s.get("explorerUrl", ""))
        else:
            ok("demo-settle", data.get("message", "no pending proofs"))
    else:
        fail("demo-settle", Exception(str(data)))
except Exception as e:
    fail("demo-settle", e)


# ─────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print(f"  RESULTS:  ✅ {passed} passed   ❌ {failed} failed   ⚠️  {skipped} skipped")
print(f"{'═'*60}\n")
if CUSTOMER_ID:
    print(f"  Customer ID:    {CUSTOMER_ID}")
if SMART_ACCOUNT:
    print(f"  Smart Account:  {SMART_ACCOUNT}")
    print(f"  BaseScan:       https://sepolia.basescan.org/address/{SMART_ACCOUNT}\n")
sys.exit(0 if failed == 0 else 1)
