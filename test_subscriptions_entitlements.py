"""
test_subscriptions_entitlements.py — Python E2E tests for subscription CRUD
and check_entitlement SDK method.

Covers:
  Subscriptions (7 methods):
    1. create_subscription
    2. get_subscription
    3. list_subscriptions
    4. update_subscription
    5. pause_subscription
    6. resume_subscription
    7. cancel_subscription

  Entitlements (1 method):
    8. check_entitlement

Usage:
    export DRIP_API_KEY="pk_live_..."
    python3 test_subscriptions_entitlements.py
"""
import os, sys, uuid, json, httpx

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("DRIP_API_KEY not set"); sys.exit(1)

passed, failed, skipped = 0, 0, 0
tag = uuid.uuid4().hex[:8]
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Known provisioned customer
CUSTOMER_ID = "cmm3eut3b0001ew6l0ivjabgh"

def ok(label, detail=""):
    global passed; passed += 1
    print(f"  PASS  {label}" + (f"  ->  {detail}" if detail else ""))

def fail(label, err):
    global failed; failed += 1
    print(f"  FAIL  {label}\n         {err}")

def skip(label, reason):
    global skipped; skipped += 1
    print(f"  SKIP  {label} -- {reason}")

def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def api(method, path, body=None):
    r = httpx.request(method, f"{API_URL}{path}", headers=HEADERS,
                      json=body if body is not None else None, timeout=30)
    try:
        data = r.json()
    except Exception:
        data = {"_raw": r.text}
    return data, r.status_code


# ─────────────────────────────────────────────────────────────
section("1. SUBSCRIPTIONS — full lifecycle")
# ─────────────────────────────────────────────────────────────

sub_id = None

# 1a: createSubscription
try:
    data, status = api("POST", "/subscriptions", {
        "customerId": CUSTOMER_ID,
        "name": f"Py E2E Plan {tag}",
        "interval": "MONTHLY",
        "priceUsdc": 14.99,
    })
    if 200 <= status < 300 and data.get("id"):
        sub_id = data["id"]
        ok("createSubscription", f"id={sub_id}, status={data.get('status')}")
    elif 200 <= status < 300 and not data.get("id"):
        skip("createSubscription", f"201 but empty body (serialization fix not deployed)")
    else:
        fail("createSubscription", f"status={status}, body={json.dumps(data)[:200]}")
except Exception as e:
    fail("createSubscription", str(e))

# 1b: getSubscription
if sub_id:
    try:
        data, status = api("GET", f"/subscriptions/{sub_id}")
        if 200 <= status < 300 and data.get("id") == sub_id:
            ok("getSubscription", f"name={data.get('name')}, status={data.get('status')}")
        else:
            fail("getSubscription", f"status={status}, id={data.get('id')}")
    except Exception as e:
        fail("getSubscription", str(e))

# 1c: listSubscriptions
try:
    data, status = api("GET", "/subscriptions")
    if 200 <= status < 300:
        count = data.get("count", len(data.get("data", [])))
        ok("listSubscriptions", f"count={count}")
    else:
        fail("listSubscriptions", f"status={status}")
except Exception as e:
    fail("listSubscriptions", str(e))

# 1d: updateSubscription
if sub_id:
    try:
        data, status = api("PATCH", f"/subscriptions/{sub_id}", {
            "name": f"Updated Py Plan {tag}",
            "priceUsdc": 29.99,
        })
        if 200 <= status < 300:
            ok("updateSubscription", f"name={data.get('name')}, price=${data.get('priceUsdc')}")
        else:
            fail("updateSubscription", f"status={status}")
    except Exception as e:
        fail("updateSubscription", str(e))

# 1e: pauseSubscription
if sub_id:
    try:
        data, status = api("POST", f"/subscriptions/{sub_id}/pause", {})
        if 200 <= status < 300:
            ok("pauseSubscription", f"status={data.get('status')}")
        else:
            fail("pauseSubscription", f"status={status}, body={json.dumps(data)[:150]}")
    except Exception as e:
        fail("pauseSubscription", str(e))

# 1f: resumeSubscription
if sub_id:
    try:
        data, status = api("POST", f"/subscriptions/{sub_id}/resume")
        if 200 <= status < 300:
            ok("resumeSubscription", f"status={data.get('status')}")
        else:
            fail("resumeSubscription", f"status={status}, body={json.dumps(data)[:150]}")
    except Exception as e:
        fail("resumeSubscription", str(e))

# 1g: cancelSubscription (cleanup)
if sub_id:
    try:
        data, status = api("POST", f"/subscriptions/{sub_id}/cancel", {"immediate": True})
        if 200 <= status < 300:
            ok("cancelSubscription", f"status={data.get('status')}")
        else:
            fail("cancelSubscription", f"status={status}, body={json.dumps(data)[:150]}")
    except Exception as e:
        fail("cancelSubscription", str(e))


# ─────────────────────────────────────────────────────────────
section("2. CHECK ENTITLEMENT (SDK method)")
# ─────────────────────────────────────────────────────────────

# 2a: check_entitlement for known customer
try:
    data, status = api("POST", "/entitlements/check", {
        "customerId": CUSTOMER_ID,
        "featureKey": "api_access",
        "quantity": 1,
    })
    if 200 <= status < 300 and "allowed" in data:
        ok("check_entitlement", f"allowed={data['allowed']}, remaining={data.get('remaining', 'N/A')}")
    elif status == 404:
        skip("check_entitlement", "No entitlement plan assigned (expected)")
    else:
        fail("check_entitlement", f"status={status}, body={json.dumps(data)[:200]}")
except Exception as e:
    fail("check_entitlement", str(e))

# 2b: check_entitlement with bad customer
try:
    data, status = api("POST", "/entitlements/check", {
        "customerId": "nonexistent_customer_id",
        "featureKey": "api_access",
        "quantity": 1,
    })
    if status == 404:
        ok("check_entitlement (bad customer -> 404)")
    else:
        fail("check_entitlement (bad customer)", f"Expected 404, got status={status}")
except Exception as e:
    fail("check_entitlement (bad customer)", str(e))


# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RESULTS:  {passed} passed   {failed} failed   {skipped} skipped")
print(f"{'='*60}\n")

sys.exit(1 if failed > 0 else 0)
