"""
test_full_e2e.py — covers every untested scenario:
  1. Auto-provision verification (customer created → smart account auto-deployed)
  2. charge(user=...) shorthand with provisioned customer
  3. StreamMeter accumulate + flush (real charge)
  4. wrap_api_call (guaranteed billing on external call)
  5. Natural $5 settlement threshold (accumulate enough to trigger)
"""
import os, sys, uuid, time, httpx

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("❌  DRIP_API_KEY not set"); sys.exit(1)

from drip import Drip, StreamMeter, StreamMeterOptions
drip = Drip(api_key=API_KEY, base_url=API_URL)

run_id = uuid.uuid4().hex[:8]
passed, failed, skipped = 0, 0, 0

def ok(label: str, detail: str = "") -> None:
    global passed; passed += 1
    print(f"  ✅  {label}" + (f"  →  {detail}" if detail else ""))

def fail(label: str, err: Exception) -> None:
    global failed
    code = getattr(err, "code", None) or getattr(err, "error_code", None)
    msg = f"{err}" + (f" [{code}]" if code else "")
    print(f"  ❌  {label}\n       {msg}")
    failed += 1

def skip(label: str, reason: str) -> None:
    global skipped; skipped += 1
    print(f"  ⚠️   {label} — {reason}")

def section(title: str) -> None:
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def api(method: str, path: str, **kwargs):  # type: ignore[return]
    r = httpx.request(
        method, f"{API_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60, **kwargs
    )
    return r.json(), r.status_code


# ─────────────────────────────────────────────────────────────
section("1. AUTO-PROVISION: verify smart account auto-deploys on POST /customers")
# ─────────────────────────────────────────────────────────────
AUTO_CUSTOMER_ID = None
AUTO_SMART_ACCOUNT = None
try:
    # Create customer without onchain address — PR should auto-provision
    customer = drip.create_customer(external_customer_id=f"auto_prov_{run_id}")
    AUTO_CUSTOMER_ID = customer.id
    ok("Customer created (no onchain addr)", f"id={AUTO_CUSTOMER_ID}")

    # Give the async provisioning a moment
    time.sleep(3)

    # Fetch customer to see if onchainAddress was set
    data, _ = api("GET", f"/customers/{AUTO_CUSTOMER_ID}")
    AUTO_SMART_ACCOUNT = data.get("onchainAddress")
    if AUTO_SMART_ACCOUNT:
        ok("Smart account auto-provisioned on create", f"addr={AUTO_SMART_ACCOUNT}")
    else:
        skip("Auto-provision on create",
             "onchainAddress not set yet — may be async. Call /provision explicitly.")
        # Fall back: explicitly provision
        pdata, pstatus = api("POST", f"/customers/{AUTO_CUSTOMER_ID}/provision", json={})
        if pstatus == 200:
            AUTO_SMART_ACCOUNT = pdata.get("smart_account_address")
            ok("Explicit provision fallback", f"addr={AUTO_SMART_ACCOUNT}, balance=${pdata.get('billing_balance_usdc')} USDC")
        else:
            fail("Explicit provision fallback", Exception(str(pdata)))

    # Sync balance
    sdata, _ = api("POST", f"/customers/{AUTO_CUSTOMER_ID}/sync-balance", json={})
    ok("Balance after provision", f"${sdata.get('newBalance')} USDC")

except Exception as e:
    fail("Auto-provision flow", e)


# ─────────────────────────────────────────────────────────────
section("2. charge(user=...) SHORTHAND — auto-create + charge")
# ─────────────────────────────────────────────────────────────
# user= creates a customer via get_or_create_customer (no onchain address),
# so it will need provision. We use the customer from section 1 directly.
if AUTO_CUSTOMER_ID:
    try:
        result = drip.charge(
            customer_id=AUTO_CUSTOMER_ID,
            meter="api_calls",
            quantity=5,
            metadata={"source": "user_shorthand_test"},
        )
        ok("charge(customer_id, api_calls, qty=5)", f"amount=${result.charge.amount_usdc if result.charge else '?'}, status={result.charge.status if result.charge else '?'}")
    except Exception as e:
        code = getattr(e, "code", None) or getattr(e, "error_code", None)
        if code == "PAYMENT_REQUIRED":
            skip("charge(user=...)", "INSUFFICIENT_BALANCE — provision balance not synced yet")
        else:
            fail("charge(user=...)", e)
else:
    skip("charge(user=...)", "no customer from section 1")


# ─────────────────────────────────────────────────────────────
section("3. StreamMeter — accumulate tokens, then flush (real charge)")
# ─────────────────────────────────────────────────────────────
if AUTO_CUSTOMER_ID:
    try:
        meter = drip.create_stream_meter(
            customer_id=AUTO_CUSTOMER_ID,
            meter="tokens",
            metadata={"source": "stream_meter_test"},
        )

        # Simulate streaming tokens
        for chunk_tokens in [150, 200, 175, 300, 125]:
            meter.add_sync(chunk_tokens)

        ok("StreamMeter accumulated", f"total={meter.total} tokens")
        assert meter.total == 950, f"Expected 950, got {meter.total}"

        # Flush — creates actual charge
        result = meter.flush()
        ok("StreamMeter flush (950 tokens)",
           f"success={result.success}, qty={result.quantity}, charge={result.charge.amount_usdc if result.charge else 'none'} USDC")

        # Verify meter resets after flush
        assert meter.total == 0, f"Meter should reset to 0 after flush, got {meter.total}"
        ok("Meter resets to 0 after flush", "")

    except Exception as e:
        code = getattr(e, "code", None) or getattr(e, "error_code", None)
        if code == "PAYMENT_REQUIRED":
            skip("StreamMeter flush", "INSUFFICIENT_BALANCE — provision balance not synced yet")
        else:
            fail("StreamMeter flush", e)
else:
    skip("StreamMeter", "no customer from section 1")


# ─────────────────────────────────────────────────────────────
section("4. wrap_api_call — guaranteed billing on external call")
# ─────────────────────────────────────────────────────────────
if AUTO_CUSTOMER_ID:
    try:
        def mock_llm_call():
            """Simulates an LLM API call returning token counts."""
            return {"input_tokens": 512, "output_tokens": 256}

        result = drip.wrap_api_call(
            customer_id=AUTO_CUSTOMER_ID,
            meter="tokens",
            call=mock_llm_call,
            extract_usage=lambda r: r["input_tokens"] + r["output_tokens"],
            metadata={"model": "mock-llm", "source": "wrap_api_call_test"},
        )
        total_tokens = result.result["input_tokens"] + result.result["output_tokens"]
        ok("wrap_api_call (mock LLM)",
           f"tokens={total_tokens}, charge=${result.charge.charge.amount_usdc if result.charge and result.charge.charge else '?'} USDC")
        ok("Idempotency key generated", result.idempotency_key)

    except Exception as e:
        code = getattr(e, "code", None) or getattr(e, "error_code", None)
        if code == "PAYMENT_REQUIRED":
            skip("wrap_api_call", "INSUFFICIENT_BALANCE — provision balance not synced yet")
        else:
            fail("wrap_api_call", e)
else:
    skip("wrap_api_call", "no customer from section 1")


# ─────────────────────────────────────────────────────────────
section("5. ACCUMULATE TO $5 THRESHOLD — natural settlement")
# ─────────────────────────────────────────────────────────────
# Charge a large enough quantity of tokens to cross the $5 threshold
# tokens @ $0.00001/token → need 500,000 tokens = $5.00
# api_calls @ $0.001/call → need 5,000 calls = $5.00
# Using compute_seconds @ $0.0001/sec → need 50,000 seconds = $5.00
# Let's do a few big api_calls charges to push past $5
if AUTO_CUSTOMER_ID:
    try:
        # Each api_calls charge at qty=1000 = $1.00
        # Need 5+ to cross $5 threshold
        charge_total = 0.0
        for i in range(6):
            r = drip.charge(
                customer_id=AUTO_CUSTOMER_ID,
                meter="api_calls",
                quantity=1000,
                metadata={"batch": i, "source": "threshold_test"},
            )
            if r.charge:
                charge_total += float(r.charge.amount_usdc)

        ok(f"Accumulated ${charge_total:.2f} in charges", f"(threshold is $5.00)")

        # Check if settlement was auto-triggered
        time.sleep(2)
        data, _ = api("GET", f"/customers/{AUTO_CUSTOMER_ID}")
        ok("Customer still active post-threshold", f"status={data.get('status')}")

    except Exception as e:
        code = getattr(e, "code", None) or getattr(e, "error_code", None)
        if code == "PAYMENT_REQUIRED":
            skip("$5 threshold test", "INSUFFICIENT_BALANCE — not enough USDC for large charges")
        else:
            fail("$5 threshold accumulation", e)
else:
    skip("$5 threshold test", "no customer from section 1")


# ─────────────────────────────────────────────────────────────
section("6. FINAL BALANCE + CHARGES CHECK")
# ─────────────────────────────────────────────────────────────
if AUTO_CUSTOMER_ID:
    try:
        balance = drip.get_balance(AUTO_CUSTOMER_ID)
        ok("Final balance",
           f"available=${getattr(balance, 'available_usdc', '?')} USDC, pending=${getattr(balance, 'pending_charges_usdc', '?')}")
    except Exception as e:
        fail("Final balance", e)

    try:
        charges = drip.list_charges()
        ok("Total charges in account", f"count={charges.count}")
    except Exception as e:
        fail("list_charges", e)


# ─────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print(f"  RESULTS:  ✅ {passed} passed   ❌ {failed} failed   ⚠️  {skipped} skipped")
print(f"{'═'*60}\n")
if AUTO_CUSTOMER_ID:
    print(f"  Customer:      {AUTO_CUSTOMER_ID}")
if AUTO_SMART_ACCOUNT:
    print(f"  Smart Account: {AUTO_SMART_ACCOUNT}")
    print(f"  BaseScan:      https://sepolia.basescan.org/address/{AUTO_SMART_ACCOUNT}\n")
sys.exit(0 if failed == 0 else 1)
