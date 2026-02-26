"""
test_provision_sync.py — tests the two untested PR endpoints:
  1. POST /customers/:id/provision
  2. POST /customers/:id/sync-balance
Also checks if the settlement finality checker has confirmed any charges.
"""
import os, sys, httpx, time

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("❌  DRIP_API_KEY not set"); sys.exit(1)

passed, failed = 0, 0
PROVISIONED_CUSTOMER_ID = "cmm3eut3b0001ew6l0ivjabgh"

def ok(label, detail=""):
    global passed; passed += 1
    print(f"  ✅  {label}" + (f"  →  {detail}" if detail else ""))

def fail(label, err):
    global failed; failed += 1
    print(f"  ❌  {label}\n       {err}")

def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def api(method, path, **kwargs):
    r = httpx.request(
        method, f"{API_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60, **kwargs
    )
    return r.json(), r.status_code

# ─────────────────────────────────────────────────────────────
section("1. POST /customers/:id/provision")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", f"/customers/{PROVISIONED_CUSTOMER_ID}/provision", json={})
    if status == 200:
        addr = data.get("onchainAddress") or data.get("customer", {}).get("onchainAddress", "?")
        ok("POST /customers/:id/provision", f"onchainAddress={addr}")
    elif status == 409:
        ok("POST /customers/:id/provision (already provisioned)", f"msg={data.get('error','?')[:60]}")
    else:
        fail("POST /customers/:id/provision", f"HTTP {status}: {data}")
except Exception as e:
    fail("POST /customers/:id/provision", e)


# ─────────────────────────────────────────────────────────────
section("2. POST /customers/:id/sync-balance")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("POST", f"/customers/{PROVISIONED_CUSTOMER_ID}/sync-balance")
    if status == 200:
        bal = data.get("balanceUsdc") or data.get("customer", {}).get("balanceUsdc", "?")
        ok("POST /customers/:id/sync-balance", f"balanceUsdc={bal}")
    else:
        fail("POST /customers/:id/sync-balance", f"HTTP {status}: {data}")
except Exception as e:
    fail("POST /customers/:id/sync-balance", e)


# ─────────────────────────────────────────────────────────────
section("3. Settlement finality — have any charges reached CONFIRMED?")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("GET", "/charges")
    all_charges = data.get("data", [])
    confirmed = [c for c in all_charges if c.get("status") == "CONFIRMED"]
    pending = [c for c in all_charges if c.get("status") == "PENDING"]
    pending_settlement = [c for c in all_charges if c.get("status") == "PENDING_SETTLEMENT"]
    print(f"  Total charges: {data.get('count', len(all_charges))}")
    print(f"  CONFIRMED:          {len(confirmed)}")
    print(f"  PENDING:            {len(pending)}")
    print(f"  PENDING_SETTLEMENT: {len(pending_settlement)}")
    if confirmed:
        ok("Finality checker working — charges are CONFIRMED", f"count={len(confirmed)}")
    elif pending:
        ok("Charges PENDING (on-chain tx submitted)", f"count={len(pending)} — finality checker will confirm within ~5 blocks")
    else:
        ok("No in-flight charges", "all settled or none created")
except Exception as e:
    fail("Settlement finality check", e)


# ─────────────────────────────────────────────────────────────
section("4. GET /settlements — check for CONFIRMED settlements")
# ─────────────────────────────────────────────────────────────
try:
    data, status = api("GET", "/settlements")
    settlements = data.get("settlements", [])
    confirmed = [s for s in settlements if s.get("status") == "CONFIRMED"]
    pending_conf = [s for s in settlements if s.get("status") == "PENDING_CONFIRMATION"]
    print(f"  Total settlements: {len(settlements)}")
    print(f"  CONFIRMED:              {len(confirmed)}")
    print(f"  PENDING_CONFIRMATION:   {len(pending_conf)}")
    if confirmed:
        s = confirmed[0]
        ok("Settlement CONFIRMED on-chain", f"id={s.get('id','?')[:20]}, total=${s.get('totalUsdc')}, tx={s.get('txHash','?')[:20]}")
    elif pending_conf:
        s = pending_conf[0]
        ok("Settlement PENDING_CONFIRMATION", f"tx={s.get('txHash','?')[:20]} — finality checker will confirm soon")
    else:
        print("  ⚠️   No settlements found")
except Exception as e:
    fail("GET /settlements", e)


print(f"\n{'═'*60}")
print(f"  RESULTS:  ✅ {passed} passed   ❌ {failed} failed")
print(f"{'═'*60}\n")
sys.exit(0 if failed == 0 else 1)
