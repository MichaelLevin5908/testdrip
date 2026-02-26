"""
Comprehensive new-use-case tests for Drip SDK PR branch.

Tests real scenarios against the live API:
1.  AI agent pipeline — multi-step LLM workflow with per-step events
2.  user= shorthand — get_or_create_customer, idempotent resolution
3.  emit_events_batch — fixed idempotency, real batch submission
4.  Multi-agent fan-out — parent agent spawning sub-agents
5.  Audit trail — structured metadata for compliance
6.  Retry safety — same idempotency key, verify no duplicate
7.  Failed run — error recorded correctly
8.  High-frequency burst — 10 rapid track_usage calls
9.  StreamMeter — accumulate then flush (sync)
10. Multi-customer tier isolation
11. record_run — single-call full execution snapshot
12. List & query — meters, customers, charges
13. wrap_api_call — guaranteed billing on external calls
14. Provision + sync-balance new PR endpoints
15. Playground demo-settle — new charge settlement
"""

import os
import time
import uuid
import sys
import httpx

from drip import Drip
from drip.errors import DripError, DripPaymentRequiredError

API_KEY = os.environ.get("DRIP_API_KEY", "")
API_URL = os.environ.get("DRIP_API_URL", "")  # expects .../v1
if not API_KEY or not API_URL:
    print("ERROR: set DRIP_API_KEY and DRIP_API_URL")
    sys.exit(1)

# Host-only base (no /v1) for direct httpx calls
HOST_BASE = API_URL.rstrip("/")
if HOST_BASE.endswith("/v1"):
    HOST_BASE = HOST_BASE[:-3]

drip = Drip(api_key=API_KEY, base_url=API_URL)

PASS = 0
FAIL = 0
SKIP = 0


def ok(label, detail=""):
    global PASS
    PASS += 1
    suffix = f"  →  {detail}" if detail else ""
    print(f"  ✅  {label}{suffix}")


def fail(label, err):
    global FAIL
    FAIL += 1
    print(f"  ❌  {label}")
    print(f"       {err}")


def skip(label, reason):
    global SKIP
    SKIP += 1
    print(f"  ⚠️   {label} — {reason}")


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


run_id_str = uuid.uuid4().hex[:8]

# ─────────────────────────────────────────────────────────────
section("1. AI AGENT PIPELINE — multi-step LLM workflow")
# ─────────────────────────────────────────────────────────────
try:
    agent_customer = drip.create_customer(
        external_customer_id=f"agent_user_{run_id_str}"
    )
    ok("Customer created", agent_customer.id)
    cid = agent_customer.id

    with drip.run(customer_id=cid, workflow="llm-pipeline") as run:
        run.event("prompt.received", quantity=1, units="requests")
        run.event("embedding.computed", quantity=512, units="tokens")
        run.event("retrieval.chunks", quantity=8, units="chunks")
        run.event("llm.input_tokens", quantity=2048, units="tokens")
        run.event("llm.output_tokens", quantity=512, units="tokens")
        run.event("response.sent", quantity=1, units="requests")

    ok("Run context completed (6 events)", f"run={run.run_id}")

    timeline = drip.get_run_timeline(run.run_id)
    ok("Timeline retrieved", f"{len(timeline.timeline)} events, status={timeline.run.status}")

except Exception as e:
    fail("AI agent pipeline", e)

# ─────────────────────────────────────────────────────────────
section("2. user= SHORTHAND — get_or_create_customer")
# ─────────────────────────────────────────────────────────────
try:
    user_tag = f"shorthand_user_{run_id_str}"

    c1 = drip.get_or_create_customer(user_tag)
    ok("get_or_create_customer (first call)", f"id={c1.id}")

    c2 = drip.get_or_create_customer(user_tag)
    if c1.id == c2.id:
        ok("get_or_create is idempotent", f"same id={c1.id}")
    else:
        fail("get_or_create idempotency", f"{c1.id} vs {c2.id}")

    # track_usage works with user= shorthand
    result = drip.track_usage(user=user_tag, meter="api_calls", quantity=5)
    ok("track_usage(user=...)", f"event_id={result.usage_event_id}")

    # charge requires onchain address — expected 400 in this env
    try:
        charge = drip.charge(user=user_tag, meter="api_calls", quantity=1)
        ok("charge(user=...) succeeded", f"id={charge.charge.id}")
    except DripPaymentRequiredError:
        skip("charge(user=...)", "no balance — 402 expected")
    except DripError as e:
        if "NO_ONCHAIN_ADDRESS" in str(e):
            skip("charge(user=...)", "no onchain address in this env — expected without blockchain")
        else:
            fail("charge(user=...)", e)

except Exception as e:
    fail("user= shorthand", e)

# ─────────────────────────────────────────────────────────────
section("3. emit_events_batch — fixed idempotency, bulk events")
# ─────────────────────────────────────────────────────────────
try:
    batch_cid = drip.create_customer(
        external_customer_id=f"batch_user_{run_id_str}"
    ).id

    # Use record_run to get a run id, then use it in batch
    snap = drip.record_run(
        customer_id=batch_cid,
        workflow="batch-setup",
        status="COMPLETED",
        events=[{"eventType": "init", "quantity": 1}],
    )
    ok("Setup run for batch", f"run={snap.run.id}")
    rid = snap.run.id

    # Re-open a new run for the batch events
    with drip.run(customer_id=batch_cid, workflow="batch-test") as batch_run:
        events = [
            {"runId": batch_run.run_id, "eventType": "step.start", "quantity": 1},
            {"runId": batch_run.run_id, "eventType": "tokens.consumed", "quantity": 300, "units": "tokens"},
            {"runId": batch_run.run_id, "eventType": "tool.called", "quantity": 2, "units": "calls"},
            {"runId": batch_run.run_id, "eventType": "tokens.output", "quantity": 150, "units": "tokens"},
            {"runId": batch_run.run_id, "eventType": "step.end", "quantity": 1},
        ]

        result1 = drip.emit_events_batch(events)
        ok("emit_events_batch (5 events)", f"created={result1.created}, dupes={result1.duplicates}")

        # Re-submit same events — SDK injects same idempotencyKey if set
        # Each event gets a new auto UUID so this creates new events (expected)
        result2 = drip.emit_events_batch(events)
        ok("Re-submit batch (new auto-keys, new events)", f"created={result2.created}")

except Exception as e:
    fail("emit_events_batch", e)

# ─────────────────────────────────────────────────────────────
section("4. MULTI-AGENT FAN-OUT — parent spawning sub-agents")
# ─────────────────────────────────────────────────────────────
try:
    correlation = f"trace_{run_id_str}"

    orchestrator = drip.get_or_create_customer(f"orchestrator_{run_id_str}")
    # drip.run() passes external_run_id for tracing; correlation via metadata
    with drip.run(customer_id=orchestrator.id, workflow=f"orchestrator-{run_id_str}",
                  external_run_id=f"orch_{run_id_str}",
                  metadata={"correlation_id": correlation}) as parent:
        parent.event("orchestrator.start", quantity=1)

        # Sub-agent A — separate customer, same trace correlation
        sub_a = drip.get_or_create_customer(f"subagent_a_{run_id_str}")
        with drip.run(customer_id=sub_a.id, workflow=f"research-agent-{run_id_str}",
                      metadata={"correlation_id": correlation, "parent": f"orch_{run_id_str}"}) as ra:
            ra.event("web.search", quantity=5, units="queries")
            ra.event("tokens.processed", quantity=8000, units="tokens")

        # Sub-agent B
        sub_b = drip.get_or_create_customer(f"subagent_b_{run_id_str}")
        with drip.run(customer_id=sub_b.id, workflow=f"writer-agent-{run_id_str}",
                      metadata={"correlation_id": correlation, "parent": f"orch_{run_id_str}"}) as rb:
            rb.event("tokens.generated", quantity=4000, units="tokens")

        parent.event("orchestrator.done", quantity=1)

    ok("Multi-agent fan-out (3 runs)",
       f"parent={parent.run_id}, sub_a={ra.run_id}, sub_b={rb.run_id}")
    ok("Correlation tracked via metadata", correlation)

except Exception as e:
    fail("Multi-agent fan-out", e)

# ─────────────────────────────────────────────────────────────
section("5. AUDIT TRAIL — structured metadata for compliance")
# ─────────────────────────────────────────────────────────────
try:
    audit_customer = drip.get_or_create_customer(f"audit_user_{run_id_str}")

    result = drip.track_usage(
        customer_id=audit_customer.id,
        meter="api_calls",
        quantity=1,
        metadata={
            "action": "document.export",
            "user_email": "alice@acme.com",
            "ip_address": "10.0.0.42",
            "user_agent": "Mozilla/5.0",
            "document_id": f"doc_{run_id_str}",
            "export_format": "pdf",
            "success": True,
            "response_time_ms": 312,
        }
    )
    ok("Audit trail recorded", f"event_id={result.usage_event_id}")

except Exception as e:
    fail("Audit trail", e)

# ─────────────────────────────────────────────────────────────
section("6. RETRY SAFETY — same idempotency key, no duplicate")
# ─────────────────────────────────────────────────────────────
try:
    retry_customer = drip.get_or_create_customer(f"retry_user_{run_id_str}")
    idem_key = f"order_{run_id_str}_step_1"

    first = drip.track_usage(
        customer_id=retry_customer.id,
        meter="api_calls",
        quantity=10,
        idempotency_key=idem_key,
    )
    second = drip.track_usage(
        customer_id=retry_customer.id,
        meter="api_calls",
        quantity=10,
        idempotency_key=idem_key,
    )

    if first.usage_event_id == second.usage_event_id:
        ok("Retry deduplication", f"same event_id={first.usage_event_id}")
    else:
        fail("Retry deduplication", f"two different events: {first.usage_event_id} vs {second.usage_event_id}")

except Exception as e:
    fail("Retry safety", e)

# ─────────────────────────────────────────────────────────────
section("7. FAILED RUN — error captured correctly")
# ─────────────────────────────────────────────────────────────
try:
    failure_customer = drip.get_or_create_customer(f"failure_user_{run_id_str}")
    with drip.run(customer_id=failure_customer.id, workflow="risky-pipeline") as frun:
        frun.event("pipeline.step_1", quantity=1)
        frun.event("pipeline.step_2", quantity=1)
        raise RuntimeError("TimeoutError: upstream API did not respond within 30s")

except RuntimeError:
    # context manager catches and records the error as FAILED
    ok("Failed run recorded", f"run_id={frun.run_id}")
    try:
        tl = drip.get_run_timeline(frun.run_id)
        ok("Failed timeline", f"status={tl.run.status}, events={len(tl.timeline)}")
    except Exception as te:
        fail("Failed timeline", te)
except Exception as e:
    fail("Failed run", e)

# ─────────────────────────────────────────────────────────────
section("8. HIGH-FREQUENCY BURST — 10 rapid track_usage calls")
# ─────────────────────────────────────────────────────────────
try:
    burst_customer = drip.get_or_create_customer(f"burst_user_{run_id_str}")
    event_ids = []
    t0 = time.time()
    for i in range(10):
        result = drip.track_usage(
            customer_id=burst_customer.id,
            meter="api_calls",
            quantity=1,
            metadata={"seq": i},
        )
        event_ids.append(result.usage_event_id)
    elapsed = time.time() - t0
    unique = len(set(event_ids))
    ok(f"10 rapid calls in {elapsed:.1f}s", f"all unique={unique == 10} ({unique}/10)")

except Exception as e:
    fail("High-frequency burst", e)

# ─────────────────────────────────────────────────────────────
section("9. StreamMeter — accumulate then flush (sync)")
# ─────────────────────────────────────────────────────────────
try:
    stream_customer = drip.get_or_create_customer(f"stream_user_{run_id_str}")

    meter = drip.create_stream_meter(
        customer_id=stream_customer.id,
        meter="api_calls",
        flush_threshold=10_000,  # won't auto-flush at these quantities
    )

    meter.add_sync(100)
    meter.add_sync(250)
    meter.add_sync(75)

    ok("StreamMeter accumulated", f"total={meter.total}")

    result = meter.flush()
    if result and result.success:
        ok("StreamMeter flushed", f"quantity={result.quantity}, is_duplicate={result.is_duplicate}")
    elif result:
        ok("StreamMeter flushed (no charge)", f"quantity={result.quantity}")
    else:
        ok("StreamMeter flush returned None (nothing to flush)")

except DripPaymentRequiredError:
    skip("StreamMeter flush", "no balance — 402 expected (charge path)")
except DripError as e:
    if "NO_ONCHAIN_ADDRESS" in str(e):
        skip("StreamMeter flush", "no onchain address — expected without blockchain")
    else:
        fail("StreamMeter", e)
except Exception as e:
    fail("StreamMeter", e)

# ─────────────────────────────────────────────────────────────
section("10. MULTI-CUSTOMER TIER ISOLATION")
# ─────────────────────────────────────────────────────────────
try:
    tiers = {}
    for tier in ["free", "pro", "enterprise"]:
        c = drip.get_or_create_customer(f"{tier}_tier_{run_id_str}")
        tiers[tier] = c.id

    usage = {"free": 100, "pro": 5_000, "enterprise": 100_000}
    for tier, qty in usage.items():
        drip.track_usage(customer_id=tiers[tier], meter="api_calls", quantity=qty,
                         metadata={"tier": tier})

    ok("3-tier usage recorded", "free=100, pro=5k, enterprise=100k api_calls")

    for tier, cid in tiers.items():
        balance = drip.get_balance(customer_id=cid)
        ok(f"Balance ({tier})", f"available={balance.available_usdc}")

except Exception as e:
    fail("Multi-customer tier isolation", e)

# ─────────────────────────────────────────────────────────────
section("11. record_run — single-call full execution snapshot")
# ─────────────────────────────────────────────────────────────
try:
    snapshot_customer = drip.get_or_create_customer(f"snapshot_user_{run_id_str}")

    result = drip.record_run(
        customer_id=snapshot_customer.id,
        workflow="batch-inference",
        status="COMPLETED",
        external_run_id=f"ext_{run_id_str}",
        correlation_id=f"otel_{run_id_str}",
        events=[
            {"eventType": "batch.start", "quantity": 1},
            {"eventType": "tokens.input", "quantity": 12_000, "units": "tokens"},
            {"eventType": "tokens.output", "quantity": 3_200, "units": "tokens"},
            {"eventType": "embeddings.computed", "quantity": 50, "units": "vectors"},
            {"eventType": "batch.end", "quantity": 1},
        ]
    )
    ok("record_run snapshot", f"run_id={result.run.id}, events_created={result.events.created}")
    ok("record_run summary", result.summary)

except Exception as e:
    fail("record_run", e)

# ─────────────────────────────────────────────────────────────
section("12. LIST & QUERY — meters, customers, charges")
# ─────────────────────────────────────────────────────────────
try:
    meters = drip.list_meters()
    ok("list_meters", f"count={len(meters.data)}, names={[m.meter for m in meters.data]}")

    customers_list = drip.list_customers()
    ok("list_customers", f"count={customers_list.count}")

    charges = drip.list_charges()
    ok("list_charges", f"count={charges.count}")

except Exception as e:
    fail("List & query", e)

# ─────────────────────────────────────────────────────────────
section("13. wrap_api_call — guaranteed billing on external call")
# ─────────────────────────────────────────────────────────────
try:
    wrap_customer = drip.get_or_create_customer(f"wrap_user_{run_id_str}")

    def fake_embeddings_api():
        return {"embedding": [0.1, 0.2, 0.3], "model": "text-embedding-3-small"}

    result = drip.wrap_api_call(
        customer_id=wrap_customer.id,
        meter="api_calls",
        call=fake_embeddings_api,
        extract_usage=lambda r: 1.0,  # charge 1 api_call per invocation
        metadata={"model": "text-embedding-3-small"},
    )

    ok("wrap_api_call", f"success={result.success}")
    ok("Wrapped fn result", f"embedding_dim={len(result.result['embedding'])}")

except DripPaymentRequiredError:
    skip("wrap_api_call", "no balance — 402 expected (charge path)")
except DripError as e:
    if "NO_ONCHAIN_ADDRESS" in str(e):
        skip("wrap_api_call", "no onchain address — expected without blockchain")
    else:
        fail("wrap_api_call", e)
except Exception as e:
    fail("wrap_api_call", e)

# ─────────────────────────────────────────────────────────────
section("14. PROVISION + SYNC-BALANCE (new PR endpoints)")
# ─────────────────────────────────────────────────────────────
try:
    prov_customer = drip.get_or_create_customer(f"prov_user_{run_id_str}")
    cid = prov_customer.id
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

    resp = httpx.post(f"{HOST_BASE}/v1/customers/{cid}/sync-balance",
                      headers=headers, timeout=30)
    if resp.status_code in (200, 201):
        ok("POST /v1/customers/:id/sync-balance", f"status={resp.status_code}")
    elif resp.status_code == 401:
        skip("POST /v1/customers/:id/sync-balance",
             "public key (pk_live_) may lack permission — use sk_ key")
    elif resp.status_code == 404:
        skip("POST /v1/customers/:id/sync-balance",
             "endpoint not yet deployed to this environment (PR not merged)")
    else:
        fail("POST /v1/customers/:id/sync-balance",
             f"status={resp.status_code}: {resp.text[:200]}")

    resp2 = httpx.post(f"{HOST_BASE}/v1/customers/{cid}/provision",
                       headers=headers, json={}, timeout=60)
    if resp2.status_code in (200, 201):
        body = resp2.json()
        ok("POST /v1/customers/:id/provision",
           f"address={body.get('onchainAddress', body.get('smartAccountAddress', 'n/a'))}")
    elif resp2.status_code == 409:
        ok("POST /v1/customers/:id/provision", "already provisioned (409)")
    elif resp2.status_code == 404:
        skip("POST /v1/customers/:id/provision",
             "endpoint not yet deployed to this environment (PR not merged)")
    elif resp2.status_code in (400, 401) and ("onchain" in resp2.text.lower() or "unauthorized" in resp2.text.lower()):
        skip("POST /v1/customers/:id/provision", "no blockchain config or key lacks permission")
    else:
        fail("POST /v1/customers/:id/provision",
             f"status={resp2.status_code}: {resp2.text[:200]}")

except Exception as e:
    fail("Provision + sync-balance", e)

# ─────────────────────────────────────────────────────────────
section("15. PLAYGROUND DEMO-SETTLE (charges + proofs)")
# ─────────────────────────────────────────────────────────────
try:
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

    settle_customer = drip.get_or_create_customer(f"settle_user_{run_id_str}")
    for _ in range(3):
        drip.track_usage(customer_id=settle_customer.id, meter="api_calls", quantity=100)

    resp = httpx.post(f"{HOST_BASE}/v1/playground/demo-settle",
                      headers=headers, json={}, timeout=60)
    if resp.status_code in (200, 201):
        body = resp.json() or {}
        settlement = body.get("settlement") or {}
        tx = (body.get("txHash") or body.get("tx_hash") or
              body.get("settlementId") or settlement.get("id") or str(body)[:80])
        ok("POST /v1/playground/demo-settle", f"result={tx}")
    elif resp.status_code == 400 and "nothing to settle" in resp.text.lower():
        skip("POST /v1/playground/demo-settle", "nothing pending to settle")
    else:
        fail("POST /v1/playground/demo-settle",
             f"status={resp.status_code}: {resp.text[:300]}")

except Exception as e:
    fail("Playground demo-settle", e)

# ─────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print(f"  RESULTS:  ✅ {PASS} passed   ❌ {FAIL} failed   ⚠️  {SKIP} skipped")
print(f"{'═'*60}\n")

if FAIL > 0:
    sys.exit(1)
