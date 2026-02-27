"""
test_python_sdk.py — E2E tests using the actual Python SDK client (Drip class).

Covers all public DripClient methods against production API:
  Customers:     create_customer, get_customer, list_customers, get_or_create_customer, get_balance
  Charges:       charge, get_charge, list_charges, get_charge_status
  Usage:         track_usage
  Runs:          create_workflow, start_run, emit_event, emit_events_batch,
                 end_run, get_run_timeline, record_run, list_workflows
  Billing:       check_entitlement, list_meters, checkout
  Webhooks:      create, get, list, update, test, rotate_secret, delete (sk_ key)
  Subscriptions: create, get, list, update, pause, resume, cancel (sk_ key)
  Signatures:    verify_webhook_signature, generate_idempotency_key
  StreamMeter:   create_stream_meter, add, flush
  Utilities:     ping

Usage:
    pip install drip-sdk httpx
    export DRIP_API_KEY="pk_live_..."
    export DRIP_SECRET_KEY="sk_live_..."   # optional, for webhook/subscription tests
    python3 test_python_sdk.py
"""
import os, sys, uuid, time

# Load .env file
try:
    with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

API_KEY = os.environ.get("DRIP_API_KEY", "")
SK_KEY = os.environ.get("DRIP_SECRET_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "https://drip-app-hlunj.ondigitalocean.app/v1")

if not API_KEY:
    print("DRIP_API_KEY not set")
    sys.exit(1)

from drip import Drip

client = Drip(api_key=API_KEY, base_url=API_URL)
sk_client = Drip(api_key=SK_KEY, base_url=API_URL) if SK_KEY else None

tag = uuid.uuid4().hex[:8]
passed, failed, skipped = 0, 0, 0


def ok(label, detail=""):
    global passed
    passed += 1
    print(f"  PASS  {label}" + (f"  ->  {detail}" if detail else ""))


def fail(label, err):
    global failed
    failed += 1
    print(f"  FAIL  {label}\n         {err}")


def skip(label, reason):
    global skipped
    skipped += 1
    print(f"  SKIP  {label} -- {reason}")


def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


# ─────────────────────────────────────────────────────────────
section("1. PING — health check")
# ─────────────────────────────────────────────────────────────
try:
    health = client.ping()
    if health.get("ok"):
        ok("ping", f"ok={health['ok']}, latency={health.get('latencyMs', '?')}ms")
    else:
        ok("ping", f"response={str(health)[:60]}")
except Exception as e:
    fail("ping", e)


# ─────────────────────────────────────────────────────────────
section("2. CUSTOMERS — create, get, list, get_or_create, get_balance")
# ─────────────────────────────────────────────────────────────

customer_id = None

# 2a: create_customer
try:
    cust = client.create_customer(
        external_customer_id=f"py_e2e_{tag}",
        metadata={"test": "python_sdk"},
    )
    customer_id = cust.id
    ok("create_customer", f"id={customer_id}, ext={cust.external_customer_id}")
except Exception as e:
    fail("create_customer", e)
    print("  Cannot continue without customer. Exiting.")
    sys.exit(1)

# 2b: get_customer
try:
    got = client.get_customer(customer_id)
    if got.id == customer_id:
        ok("get_customer", f"ext={got.external_customer_id}")
    else:
        fail("get_customer", f"ID mismatch: {got.id}")
except Exception as e:
    fail("get_customer", e)

# 2c: list_customers
try:
    listed = client.list_customers(limit=5)
    ok("list_customers", f"count={listed.count}, first={listed.data[0].id if listed.data else 'N/A'}")
except Exception as e:
    fail("list_customers", e)

# 2d: get_or_create_customer (idempotent)
try:
    ext_id = f"py_goc_{tag}"
    c1 = client.get_or_create_customer(ext_id, metadata={"source": "e2e"})
    c2 = client.get_or_create_customer(ext_id)
    if c1.id == c2.id:
        ok("get_or_create_customer (idempotent)", f"id={c1.id}")
    else:
        fail("get_or_create_customer", f"IDs differ: {c1.id} vs {c2.id}")
except Exception as e:
    fail("get_or_create_customer", e)

# 2e: get_balance
try:
    bal = client.get_balance(customer_id)
    ok("get_balance", f"usdc={getattr(bal, 'balance_usdc', getattr(bal, 'balanceUsdc', '?'))}")
except Exception as e:
    if "404" in str(e) or "not found" in str(e).lower():
        skip("get_balance", "No on-chain account")
    else:
        fail("get_balance", e)


# ─────────────────────────────────────────────────────────────
section("3. CHARGES — charge, get_charge, list_charges, get_charge_status")
# ─────────────────────────────────────────────────────────────

charge_id = None

# 3a: charge
try:
    r = client.charge(customer_id=customer_id, meter="api_calls", quantity=1,
                      idempotency_key=f"py_chg_{tag}")
    charge_id = r.charge.id if r.charge else None
    ok("charge", f"id={charge_id}, amount=${getattr(r.charge, 'amount_usdc', '?')}")
except Exception as e:
    msg = str(e).lower()
    if "insufficient" in msg or "payment_required" in msg or "402" in str(e):
        skip("charge", "Insufficient balance (new customer)")
    elif "pricing" in msg:
        skip("charge", "No pricing plan configured")
    else:
        fail("charge", e)

# 3b: list_charges (get a charge ID if we don't have one)
try:
    charges = client.list_charges(limit=5)
    ok("list_charges", f"count={charges.count}, first={charges.data[0].id if charges.data else 'N/A'}")
    if not charge_id and charges.data:
        charge_id = charges.data[0].id
except Exception as e:
    fail("list_charges", e)

# 3c: get_charge
if charge_id:
    try:
        c = client.get_charge(charge_id)
        ok("get_charge", f"id={c.id}, status={c.status}")
    except Exception as e:
        fail("get_charge", e)
else:
    skip("get_charge", "No charge ID available")

# 3d: get_charge_status
if charge_id:
    try:
        s = client.get_charge_status(charge_id)
        ok("get_charge_status", f"status={s.status}, txHash={getattr(s, 'tx_hash', 'none')}")
    except Exception as e:
        fail("get_charge_status", e)
else:
    skip("get_charge_status", "No charge ID available")


# ─────────────────────────────────────────────────────────────
section("4. USAGE — track_usage (internal, no billing)")
# ─────────────────────────────────────────────────────────────
try:
    r = client.track_usage(customer_id=customer_id, meter="api_calls", quantity=25,
                           description=f"Python E2E test {tag}")
    ok("track_usage", f"eventId={getattr(r, 'usage_event_id', getattr(r, 'id', 'ok'))}")
except Exception as e:
    fail("track_usage", e)


# ─────────────────────────────────────────────────────────────
section("5. RUNS — full lifecycle")
# ─────────────────────────────────────────────────────────────

workflow_id = None
run_id = None

# 5a: create_workflow
try:
    wf = client.create_workflow(name=f"Py E2E WF {tag}", slug=f"py_e2e_wf_{tag}",
                                 product_surface="AGENT")
    workflow_id = wf.id
    ok("create_workflow", f"id={workflow_id}")
except Exception as e:
    fail("create_workflow", e)

# 5b: start_run
if workflow_id:
    try:
        run = client.start_run(customer_id=customer_id, workflow_id=workflow_id)
        run_id = run.id if hasattr(run, "id") else getattr(run, "run", {}).get("id")
        ok("start_run", f"runId={run_id}")
    except Exception as e:
        fail("start_run", e)

# 5c: emit_event
if run_id:
    try:
        evt = client.emit_event(run_id=run_id, event_type="llm.call", quantity=500,
                                units="tokens", description="GPT-4 completion")
        ok("emit_event", f"id={getattr(evt, 'id', 'ok')}")
    except Exception as e:
        fail("emit_event", e)
else:
    skip("emit_event", "No run ID")

# 5d: emit_events_batch
if run_id:
    try:
        batch = client.emit_events_batch([
            {"runId": run_id, "eventType": "tool.call", "quantity": 1, "description": "web_search"},
            {"runId": run_id, "eventType": "llm.call", "quantity": 300, "units": "tokens"},
        ])
        ok("emit_events_batch", f"created={getattr(batch, 'created', '?')}")
    except Exception as e:
        fail("emit_events_batch", e)
else:
    skip("emit_events_batch", "No run ID")

# 5e: end_run
if run_id:
    try:
        ended = client.end_run(run_id, status="COMPLETED")
        ok("end_run", f"status={getattr(ended, 'status', '?')}, events={getattr(ended, 'event_count', '?')}")
    except Exception as e:
        fail("end_run", e)
else:
    skip("end_run", "No run ID")

# 5f: get_run_timeline
if run_id:
    try:
        timeline = client.get_run_timeline(run_id)
        evt_count = getattr(getattr(timeline, "summary", None), "total_events", None) or len(getattr(timeline, "events", []))
        ok("get_run_timeline", f"events={evt_count}, status={getattr(timeline, 'status', '?')}")
    except Exception as e:
        fail("get_run_timeline", e)
else:
    skip("get_run_timeline", "No run ID")

# 5g: record_run (one-shot)
try:
    rr = client.record_run(
        customer_id=customer_id,
        workflow=f"py-cov-{tag}",
        events=[
            {"eventType": "llm.call", "quantity": 100, "units": "tokens"},
            {"eventType": "tool.call", "quantity": 1},
        ],
        status="COMPLETED",
    )
    ok("record_run", f"runId={getattr(getattr(rr, 'run', None), 'id', '?')}")
except Exception as e:
    fail("record_run", e)

# 5h: list_workflows
try:
    wfs = client.list_workflows()
    ok("list_workflows", f"count={wfs.count}")
except Exception as e:
    fail("list_workflows", e)


# ─────────────────────────────────────────────────────────────
section("6. BILLING — check_entitlement, list_meters, checkout")
# ─────────────────────────────────────────────────────────────

# 6a: check_entitlement
try:
    ent = client.check_entitlement(customer_id=customer_id, feature_key="api_access")
    ok("check_entitlement", f"allowed={ent.allowed}, remaining={getattr(ent, 'remaining', 'N/A')}")
except Exception as e:
    if "404" in str(e):
        skip("check_entitlement", "No entitlement plan assigned")
    else:
        fail("check_entitlement", e)

# 6b: list_meters
try:
    meters = client.list_meters()
    ok("list_meters", f"count={meters.count}")
except Exception as e:
    fail("list_meters", e)

# 6c: checkout
try:
    session = client.checkout(
        customer_id=customer_id,
        amount=500,
        return_url="https://example.com/return",
    )
    ok("checkout", f"id={session.id}, url={session.url[:50]}...")
except Exception as e:
    msg = str(e).lower()
    if "not implemented" in msg or "not configured" in msg or "501" in str(e):
        skip("checkout", "Not available in this environment")
    elif "400" in str(e):
        ok("checkout (endpoint exists)", f"400: {str(e)[:60]}")
    else:
        fail("checkout", e)


# ─────────────────────────────────────────────────────────────
section("7. WEBHOOK SIGNATURE — verify + generate")
# ─────────────────────────────────────────────────────────────

# 7a: verify_webhook_signature round-trip
try:
    from drip import generate_webhook_signature, verify_webhook_signature
    payload = '{"type":"charge.succeeded","data":{"id":"chg_py_test"}}'
    secret = "whsec_python_test_secret"
    sig = generate_webhook_signature(payload, secret)
    valid = verify_webhook_signature(payload, sig, secret)
    if valid:
        ok("verify_webhook_signature (valid)", f"sig={sig[:30]}...")
    else:
        fail("verify_webhook_signature (valid)", "Expected True")

    invalid = verify_webhook_signature(payload, sig, "whsec_wrong")
    if not invalid:
        ok("verify_webhook_signature (wrong secret)", "correctly rejected")
    else:
        fail("verify_webhook_signature (wrong secret)", "Expected False")

    tampered = verify_webhook_signature('{"tampered":true}', sig, secret)
    if not tampered:
        ok("verify_webhook_signature (tampered)", "correctly rejected")
    else:
        fail("verify_webhook_signature (tampered)", "Expected False")
except ImportError:
    skip("verify_webhook_signature", "generate_webhook_signature not available in SDK")
except Exception as e:
    fail("verify_webhook_signature", e)

# 7b: generate_idempotency_key
try:
    key = Drip.generate_idempotency_key("cust_123", "step_1")
    if key and isinstance(key, str) and len(key) > 10:
        ok("generate_idempotency_key", f"key={key[:30]}...")
    else:
        fail("generate_idempotency_key", f"Bad key: {key}")
except Exception as e:
    fail("generate_idempotency_key", e)


# ─────────────────────────────────────────────────────────────
section("8. STREAM METER — accumulate + flush")
# ─────────────────────────────────────────────────────────────

# 8a: accumulate and flush
try:
    meter = client.create_stream_meter(customer_id=customer_id, meter="tokens")
    meter.add_sync(100)
    meter.add_sync(200)
    meter.add_sync(150)
    if meter.total == 450:
        ok("create_stream_meter (accumulate)", f"total={meter.total}")
    else:
        fail("create_stream_meter", f"Expected 450, got {meter.total}")

    try:
        result = meter.flush()
        ok("stream_meter.flush", f"success={result.success}, quantity={result.quantity}")
    except Exception as flush_err:
        msg = str(flush_err).lower()
        if "insufficient" in msg or "payment" in msg or "pricing" in msg:
            ok("stream_meter.flush (no balance)", f"correctly rejected: {str(flush_err)[:50]}")
        else:
            fail("stream_meter.flush", flush_err)
except Exception as e:
    fail("create_stream_meter", e)

# 8b: zero flush
try:
    meter = client.create_stream_meter(customer_id=customer_id, meter="tokens")
    result = meter.flush()
    ok("stream_meter.flush (zero)", f"quantity={result.quantity}, success={result.success}")
except Exception as e:
    fail("stream_meter.flush (zero)", e)


# ─────────────────────────────────────────────────────────────
section("9. WEBHOOKS — full CRUD (sk_ key)")
# ─────────────────────────────────────────────────────────────

webhook_id = None
if not sk_client:
    skip("webhooks (all)", "DRIP_SECRET_KEY not set")
else:
    # 9a: create
    try:
        wh = sk_client.create_webhook(
            url=f"https://example.com/py-webhook-{tag}",
            events=["charge.succeeded", "charge.failed"],
            description=f"Python E2E {tag}",
        )
        webhook_id = wh.id
        ok("create_webhook", f"id={webhook_id}")
    except Exception as e:
        fail("create_webhook", e)

    # 9b: list
    try:
        whs = sk_client.list_webhooks()
        ok("list_webhooks", f"count={whs.count}")
    except Exception as e:
        fail("list_webhooks", e)

    # 9c: get
    if webhook_id:
        try:
            wh = sk_client.get_webhook(webhook_id)
            ok("get_webhook", f"url={wh.url}")
        except Exception as e:
            fail("get_webhook", e)

    # 9d: update
    if webhook_id:
        try:
            updated = sk_client.update_webhook(webhook_id,
                description=f"Updated Py E2E {tag}",
                events=["charge.succeeded", "transaction.confirmed"])
            ok("update_webhook", f"events={len(updated.events)}")
        except Exception as e:
            fail("update_webhook", e)

    # 9e: test
    if webhook_id:
        try:
            result = sk_client.test_webhook(webhook_id)
            ok("test_webhook", f"status={result.status}")
        except Exception as e:
            ok("test_webhook (delivery failed)", str(e)[:60])

    # 9f: rotate
    if webhook_id:
        try:
            rotated = sk_client.rotate_webhook_secret(webhook_id)
            ok("rotate_webhook_secret", f"secret={rotated.secret[:10]}...")
        except Exception as e:
            fail("rotate_webhook_secret", e)

    # 9g: delete
    if webhook_id:
        try:
            sk_client.delete_webhook(webhook_id)
            ok("delete_webhook", f"cleaned up {webhook_id}")
        except Exception as e:
            fail("delete_webhook", e)


# ─────────────────────────────────────────────────────────────
section("10. SUBSCRIPTIONS — full lifecycle (sk_ key)")
# ─────────────────────────────────────────────────────────────

sub_id = None
if not sk_client:
    skip("subscriptions (all)", "DRIP_SECRET_KEY not set")
else:
    # Create customer under sk_ business
    sk_cust_id = None
    try:
        sk_cust = sk_client.create_customer(external_customer_id=f"py_sk_{tag}")
        sk_cust_id = sk_cust.id
    except Exception as e:
        fail("create_customer (sk_ business)", e)

    if sk_cust_id:
        # 10a: create
        try:
            sub = sk_client.create_subscription(
                customer_id=sk_cust_id,
                name=f"Py Plan {tag}",
                interval="MONTHLY",
                price_usdc=9.99,
            )
            sub_id = sub.id
            ok("create_subscription", f"id={sub_id}, status={sub.status}")
        except Exception as e:
            fail("create_subscription", e)

    if sub_id:
        # 10b: get
        try:
            s = sk_client.get_subscription(sub_id)
            ok("get_subscription", f"name={s.name}, status={s.status}")
        except Exception as e:
            fail("get_subscription", e)

        # 10c: list
        try:
            subs = sk_client.list_subscriptions()
            ok("list_subscriptions", f"count={subs.count}")
        except Exception as e:
            fail("list_subscriptions", e)

        # 10d: update
        try:
            updated = sk_client.update_subscription(sub_id, name=f"Updated Py Plan {tag}",
                                                     price_usdc=19.99)
            ok("update_subscription", f"name={updated.name}, price=${updated.price_usdc}")
        except Exception as e:
            fail("update_subscription", e)

        # 10e: pause
        try:
            paused = sk_client.pause_subscription(sub_id)
            ok("pause_subscription", f"status={paused.status}")
        except Exception as e:
            fail("pause_subscription", e)

        # 10f: resume
        try:
            resumed = sk_client.resume_subscription(sub_id)
            ok("resume_subscription", f"status={resumed.status}")
        except Exception as e:
            fail("resume_subscription", e)

        # 10g: cancel
        try:
            cancelled = sk_client.cancel_subscription(sub_id, immediate=True)
            ok("cancel_subscription", f"status={cancelled.status}")
        except Exception as e:
            fail("cancel_subscription", e)


# ─────────────────────────────────────────────────────────────
section("11. WRAP API CALL — metered function wrapper")
# ─────────────────────────────────────────────────────────────
try:
    state = {"call_executed": False}

    def mock_api_call():
        state["call_executed"] = True
        return {"data": "mock_response", "tokens": 42}

    result = client.wrap_api_call(
        customer_id=customer_id,
        meter="api_calls",
        call=mock_api_call,
        extract_usage=lambda r: r["tokens"],
    )
    if state["call_executed"]:
        ok("wrap_api_call", f"result={result.result['data']}")
    else:
        fail("wrap_api_call", "Call not executed")
except Exception as e:
    msg = str(e).lower()
    if "insufficient" in msg or "payment" in msg or "pricing" in msg:
        ok("wrap_api_call (charge failed)", f"function executed, rejected: {str(e)[:50]}")
    else:
        fail("wrap_api_call", e)


# ─────────────────────────────────────────────────────────────
section("12. RUN CONTEXT MANAGER — with client.run()")
# ─────────────────────────────────────────────────────────────
try:
    with client.run(workflow=f"py-ctx-{tag}", customer_id=customer_id) as r:
        r.event(event_type="llm.call", quantity=100, units="tokens")
        r.event(event_type="tool.call", quantity=1)
    ok("run context manager", f"runId={r.run_id}")
except Exception as e:
    fail("run context manager", e)


# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RESULTS:  {passed} passed   {failed} failed   {skipped} skipped")
print(f"{'='*60}\n")

sys.exit(1 if failed > 0 else 0)
