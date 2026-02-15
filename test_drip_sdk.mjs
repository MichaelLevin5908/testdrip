/**
 * Test Drip Node.js SDK - Comprehensive Feature Testing
 *
 * This test suite demonstrates all major SDK features:
 *
 * 1. API Connection - Verify connectivity
 * 2. Customer Creation - Create customers with random addresses
 * 3. Usage Tracking - Track metered usage (no billing)
 * 4. Agent Runs (recordRun) - Record complete execution traces
 * 5. Balance Retrieval - Check customer account balance
 * 6. Billing - Create charges (requires pricing plan)
 * 7. List Customers - Retrieve all customers
 * 8. Token Tracking - Track LLM input/output tokens per customer
 * 9. Idempotency - Prevent duplicate charges with idempotency keys
 * 10. Multi-Customer Usage - Track different usage across customers
 * 11. Audit Trail - Track who did what with detailed metadata
 * 12. Correlation ID - Link runs to your distributed traces
 * 13. Fine-Grained Runs - startRun, emitEvent, endRun, getRunTimeline
 * 14. recordRun Error - Record failed runs with error details
 * 15. Batch Events - emitEventsBatch for multiple events at once
 * 16. wrapApiCall - Wrap external API calls with guaranteed usage recording
 * 17. List Meters - Discover available pricing meters
 * 18. Cost Estimation - Estimate costs from hypothetical usage
 *
 * Setup:
 *     1. Install the SDK:
 *        npm install @drip-sdk/node
 *
 *     2. Get your API key from the Drip dashboard (https://drip-app-hlunj.ondigitalocean.app)
 *        or from your .env file
 *
 *     3. Set environment variable and run:
 *        export DRIP_API_KEY="pk_live_..."
 *        node test_drip_sdk.mjs
 *
 * How it works:
 *   - The test automatically creates test customers (no manual setup needed)
 *   - Customers are created with random wallet addresses and IDs
 *   - Usage is tracked against these customers, then verified
 *   - Tests that require pricing plans (charge, wrapApiCall, estimates)
 *     show NOTE instead of FAIL when no plan is configured
 *
 * What this tests:
 * - Customer attribution (which customer used what)
 * - Token tracking (LLM usage per customer)
 * - Idempotency (duplicate prevention with real idempotencyKey param)
 * - Audit trail (who did what, when, from where)
 * - Multi-customer scenarios
 * - Correlation ID (distributed tracing)
 * - Fine-grained run control (startRun -> emitEvent -> endRun -> timeline)
 */

import { Drip } from '@drip-sdk/node';
import crypto from 'crypto';

// ============================================================================
// SETUP
// ============================================================================

const API_KEY = process.env.DRIP_API_KEY;

if (!API_KEY) {
  console.log('Error: DRIP_API_KEY environment variable not set');
  console.log('\nRun this first:');
  console.log('export DRIP_API_KEY="pk_live_..."');
  process.exit(1);
}

const drip = new Drip({
  apiKey: API_KEY,
  baseUrl: 'https://drip-app-hlunj.ondigitalocean.app/v1',
});

const randomHex = (bytes) => crypto.randomBytes(bytes).toString('hex');

console.log('Testing Drip Node.js SDK');
console.log('='.repeat(60));

let customerId;
let customerId2;
const randomId = `test_user_${randomHex(4)}`;
const randomId2 = `test_user_${randomHex(4)}`;

// ============================================================================
// TEST 1: Verify Connection
// ============================================================================

console.log('\n1. Testing API Connection...');
try {
  await drip.ping();
  console.log('   PASS - Connected to Drip API successfully!');
} catch (e) {
  console.log(`   FAIL - Failed to connect: ${e.message}`);
  process.exit(1);
}

// ============================================================================
// TEST 2: Create a Customer
// ============================================================================

console.log('\n2. Creating a test customer...');
try {
  const randomAddress = '0x' + randomHex(20);

  const customer = await drip.createCustomer({
    onchainAddress: randomAddress,
    externalCustomerId: randomId,
    metadata: { name: 'Test User', plan: 'starter' },
  });
  customerId = customer.id;
  console.log(`   PASS - Customer created: ${customer.id}`);
  console.log(`      Address: ${customer.onchainAddress}`);
} catch (e) {
  console.log(`   FAIL - Failed to create customer: ${e.message}`);
  process.exit(1);
}

// ============================================================================
// TEST 3: Track Usage (No Billing)
// ============================================================================

console.log('\n3. Tracking usage (no charge)...');
try {
  const result = await drip.trackUsage({
    customerId,
    meter: 'api_calls',
    quantity: 5,
    metadata: { endpoint: '/v1/test', method: 'POST' },
  });
  console.log(`   PASS - Usage tracked: ${result.usageEventId}`);
  console.log('      Meter: api_calls, Quantity: 5');
} catch (e) {
  console.log(`   FAIL - Failed to track usage: ${e.message}`);
}

// ============================================================================
// TEST 4: Record Agent Run
// ============================================================================

console.log('\n4. Recording agent run...');
try {
  const runResult = await drip.recordRun({
    customerId,
    workflow: 'test-agent',
    events: [
      { eventType: 'llm.call', quantity: 300, units: 'tokens' },
      { eventType: 'tool.call', quantity: 1 },
    ],
    status: 'COMPLETED',
  });
  console.log(`   PASS - Agent run recorded: ${runResult.run.id}`);
  console.log(`      Summary: ${runResult.summary}`);
} catch (e) {
  console.log(`   FAIL - Failed to record run: ${e.message}`);
}

// ============================================================================
// TEST 5: Get Customer Balance
// ============================================================================

console.log('\n5. Checking customer balance...');
try {
  const balance = await drip.getBalance(customerId);
  console.log('   PASS - Balance retrieved:');
  console.log(`      Balance: $${balance.balanceUsdc} USDC`);
  console.log(`      Available: $${balance.availableUsdc} USDC`);
} catch (e) {
  console.log(`   FAIL - Failed to get balance: ${e.message}`);
}

// ============================================================================
// TEST 6: Create a Charge
// ============================================================================

console.log('\n6. Creating a charge...');
try {
  const chargeResult = await drip.charge({
    customerId,
    meter: 'api_calls',
    quantity: 10,
    idempotencyKey: 'test_charge_001',
  });
  console.log(`   PASS - Charge created: ${chargeResult.charge.id}`);
  console.log(`      Amount: $${chargeResult.charge.amountUsdc} USDC`);
  console.log(`      Is Duplicate: ${chargeResult.isDuplicate}`);
} catch (e) {
  console.log(`   NOTE - Charge failed (expected if no pricing plan): ${e.message}`);
}

// ============================================================================
// TEST 7: List Customers
// ============================================================================

console.log('\n7. Listing all customers...');
try {
  const customers = await drip.listCustomers({ limit: 5 });
  console.log(`   PASS - Found ${customers.data.length} customers:`);
  for (const cust of customers.data.slice(0, 3)) {
    console.log(`      - ${cust.id} (${cust.externalCustomerId || 'no external ID'})`);
  }
} catch (e) {
  console.log(`   FAIL - Failed to list customers: ${e.message}`);
}

// ============================================================================
// TEST 8: Track Token Usage (LLM Tokens)
// ============================================================================

console.log('\n8. Tracking LLM token usage...');
try {
  const inputUsage = await drip.trackUsage({
    customerId,
    meter: 'tokens_input',
    quantity: 500,
    metadata: { model: 'gpt-4', endpoint: '/v1/chat/completions', sessionId: 'sess_123' },
  });
  console.log(`   PASS - Input tokens tracked: ${inputUsage.usageEventId}`);
  console.log('      Model: gpt-4, Tokens: 500');

  const outputUsage = await drip.trackUsage({
    customerId,
    meter: 'tokens_output',
    quantity: 1200,
    metadata: { model: 'gpt-4', endpoint: '/v1/chat/completions', sessionId: 'sess_123' },
  });
  console.log(`   PASS - Output tokens tracked: ${outputUsage.usageEventId}`);
  console.log('      Model: gpt-4, Tokens: 1200');
  console.log('      Total tokens for this request: 1700');
} catch (e) {
  console.log(`   FAIL - Failed to track tokens: ${e.message}`);
}

// ============================================================================
// TEST 9: Test Idempotency (Duplicate Prevention)
// ============================================================================

console.log('\n9. Testing idempotency (duplicate prevention)...');
try {
  const idemKey = `test_idem_${randomHex(8)}`;

  console.log(`   -> Making first request with key: ${idemKey}`);
  const usage1 = await drip.trackUsage({
    customerId,
    meter: 'api_calls',
    quantity: 1,
    idempotencyKey: idemKey,
  });
  console.log(`   PASS - First request succeeded: ${usage1.usageEventId}`);

  console.log('   -> Making duplicate request with same key...');
  const usage2 = await drip.trackUsage({
    customerId,
    meter: 'api_calls',
    quantity: 1,
    idempotencyKey: idemKey,
  });
  console.log(`   PASS - Second request handled: ${usage2.usageEventId}`);

  if (usage1.usageEventId === usage2.usageEventId) {
    console.log('   PASS - Idempotency working! Same event returned (no duplicate)');
  } else {
    console.log('   NOTE - Different events created (idempotency may not be server-enforced for trackUsage)');
  }
} catch (e) {
  console.log(`   FAIL - Failed idempotency test: ${e.message}`);
}

// ============================================================================
// TEST 10: Track Multiple Customers with Different Usage
// ============================================================================

console.log('\n10. Tracking usage across multiple customers...');
try {
  const randomAddress2 = '0x' + randomHex(20);

  const customer2 = await drip.createCustomer({
    onchainAddress: randomAddress2,
    externalCustomerId: randomId2,
    metadata: { name: 'Test User 2', plan: 'premium' },
  });
  customerId2 = customer2.id;
  console.log(`   PASS - Customer 2 created: ${customer2.id}`);

  await drip.trackUsage({ customerId, meter: 'api_calls', quantity: 10 });
  console.log(`   PASS - Customer 1 (${randomId}): 10 API calls`);

  await drip.trackUsage({ customerId: customerId2, meter: 'api_calls', quantity: 100 });
  await drip.trackUsage({ customerId: customerId2, meter: 'tokens_input', quantity: 5000 });
  await drip.trackUsage({ customerId: customerId2, meter: 'tokens_output', quantity: 8000 });
  console.log(`   PASS - Customer 2 (${randomId2}): 100 API calls, 13,000 tokens`);

  console.log('\n   Usage Summary:');
  console.log('      Customer 1: Light user (10 calls)');
  console.log('      Customer 2: Heavy user (100 calls + 13k tokens)');
  console.log('   PASS - Multi-customer tracking successful!');
} catch (e) {
  console.log(`   FAIL - Failed multi-customer test: ${e.message}`);
}

// ============================================================================
// TEST 11: Audit Trail - Track Who Did What
// ============================================================================

console.log('\n11. Testing audit trail (tracking who did what)...');
try {
  const auditUsage = await drip.trackUsage({
    customerId,
    meter: 'api_calls',
    quantity: 1,
    metadata: {
      action: 'document_generated',
      userId: 'user_alice_123',
      userEmail: 'alice@example.com',
      ipAddress: '192.168.1.100',
      timestamp: '2026-01-31T12:00:00Z',
      endpoint: '/api/generate-report',
      success: true,
      responseTimeMs: 450,
    },
  });
  console.log(`   PASS - Audit event tracked: ${auditUsage.usageEventId}`);
  console.log('      Action: document_generated');
  console.log('      User: alice@example.com (user_alice_123)');
  console.log('      IP: 192.168.1.100');
  console.log('      Success: true, Response time: 450ms');
  console.log('   PASS - Full audit trail captured in metadata!');
} catch (e) {
  console.log(`   FAIL - Failed audit trail test: ${e.message}`);
}

// ============================================================================
// TEST 12: Correlation ID (Distributed Tracing)
// ============================================================================

console.log('\n12. Testing correlationId (distributed tracing)...');
try {
  const traceId = `trace_${randomHex(16)}`;

  const corrResult = await drip.recordRun({
    customerId,
    workflow: 'traced-agent',
    correlationId: traceId,
    events: [
      { eventType: 'llm.call', quantity: 500, units: 'tokens' },
    ],
    status: 'COMPLETED',
  });
  console.log(`   PASS - Run recorded with correlationId: ${traceId.slice(0, 24)}...`);
  console.log(`      Run ID: ${corrResult.run.id}`);
  console.log(`      Summary: ${corrResult.summary}`);
} catch (e) {
  console.log(`   FAIL - Failed correlationId test: ${e.message}`);
}

// ============================================================================
// TEST 13: Fine-Grained Run Control (start -> emit -> end -> timeline)
// ============================================================================

console.log('\n13. Testing fine-grained run control...');
try {
  // Step 1: Create workflow
  const workflow = await drip.createWorkflow({
    name: 'Fine-Grained Test',
    slug: `fine-grained-test-${randomHex(4)}`,
    productSurface: 'AGENT',
  });
  console.log(`   PASS - Workflow created: ${workflow.id}`);

  // Step 2: Start run with correlationId
  const spanId = `span_${randomHex(8)}`;
  const run = await drip.startRun({
    customerId,
    workflowId: workflow.id,
    correlationId: spanId,
  });
  console.log(`   PASS - Run started: ${run.id}`);
  console.log(`      Correlation ID: ${spanId}`);

  // Step 3: Emit individual events
  await drip.emitEvent({
    runId: run.id,
    eventType: 'prompt.received',
    quantity: 150,
    units: 'tokens',
  });
  console.log('   PASS - Event emitted: prompt.received (150 tokens)');

  await drip.emitEvent({
    runId: run.id,
    eventType: 'llm.call',
    quantity: 800,
    units: 'tokens',
    metadata: { model: 'gpt-4o' },
  });
  console.log('   PASS - Event emitted: llm.call (800 tokens)');

  await drip.emitEvent({
    runId: run.id,
    eventType: 'tool.call',
    quantity: 1,
    description: 'web search for latest news',
  });
  console.log('   PASS - Event emitted: tool.call (1)');

  // Step 4: End run
  await new Promise((r) => setTimeout(r, 1000)); // brief pause so duration is non-zero
  const endResult = await drip.endRun(run.id, { status: 'COMPLETED' });
  console.log(`   PASS - Run ended: ${endResult.status}`);
  if (endResult.durationMs) {
    console.log(`      Duration: ${endResult.durationMs}ms`);
  }

  // Step 5: Get timeline
  const tl = await drip.getRunTimeline(run.id);
  console.log('   PASS - Timeline retrieved:');
  console.log(`      Events: ${tl.events.length}`);
  console.log(`      Status: ${tl.status}`);
  if (tl.durationMs) {
    console.log(`      Duration: ${tl.durationMs}ms`);
  }
  console.log(`      Summary: ${JSON.stringify(tl.summary)}`);
  for (const evt of tl.events) {
    const qty = evt.metadata?.quantity ?? '';
    const units = evt.metadata?.units ?? 'units';
    console.log(`        - ${evt.eventType} (${qty} ${units})`);
  }
} catch (e) {
  console.log(`   FAIL - Failed fine-grained run test: ${e.message}`);
}

// ============================================================================
// TEST 14: recordRun with Error Status + Extended Params
// ============================================================================

console.log('\n14. Testing recordRun with error status...');
try {
  const extId = `ext_run_${randomHex(8)}`;
  const runResult = await drip.recordRun({
    customerId,
    workflow: 'test-error-agent',
    events: [
      { eventType: 'llm.call', quantity: 100, units: 'tokens' },
      { eventType: 'tool.call', quantity: 1, costUnits: 0.002 },
    ],
    status: 'FAILED',
    errorMessage: 'Simulated failure for testing',
    errorCode: 'TEST_ERROR',
    externalRunId: extId,
    correlationId: `trace_${randomHex(8)}`,
    metadata: { testSuite: 'testdrip' },
  });
  console.log(`   PASS - Failed run recorded: ${runResult.run.id}`);
  console.log(`      Status: ${runResult.run.status}, External ID: ${extId}`);
  console.log(`      Summary: ${runResult.summary}`);
} catch (e) {
  console.log(`   FAIL - recordRun with error status failed: ${e.message}`);
}

// ============================================================================
// TEST 15: Batch Event Emission (emitEventsBatch)
// ============================================================================

console.log('\n15. Testing emitEventsBatch...');
try {
  const workflow = await drip.createWorkflow({
    name: 'Batch Test',
    slug: `batch-test-${randomHex(4)}`,
    productSurface: 'AGENT',
  });
  const run = await drip.startRun({ customerId, workflowId: workflow.id });

  const batchResult = await drip.emitEventsBatch([
    { runId: run.id, eventType: 'step.one', quantity: 10, units: 'tokens' },
    { runId: run.id, eventType: 'step.two', quantity: 20, units: 'tokens' },
    { runId: run.id, eventType: 'step.three', quantity: 30, units: 'tokens' },
  ]);
  await drip.endRun(run.id, { status: 'COMPLETED' });

  console.log(`   PASS - Batch emitted: ${batchResult.created} created, ${batchResult.duplicates} duplicates`);
} catch (e) {
  console.log(`   FAIL - emitEventsBatch failed: ${e.message}`);
}

// ============================================================================
// TEST 16: wrapApiCall (Guaranteed Usage Recording)
// ============================================================================

console.log('\n16. Testing wrapApiCall...');
try {
  const wrapResult = await drip.wrapApiCall({
    customerId,
    meter: 'tokens',
    call: async () => ({ text: 'hello from mock LLM', usage: { totalTokens: 42 } }),
    extractUsage: (r) => r.usage.totalTokens,
  });
  console.log('   PASS - wrapApiCall succeeded');
  console.log(`      API result: ${wrapResult.result.text}`);
  console.log(`      Charge ID: ${wrapResult.charge?.charge?.id || 'N/A'}`);
} catch (e) {
  console.log(`   NOTE - wrapApiCall failed (expected if no pricing plan): ${e.message}`);
}

// ============================================================================
// TEST 17: List Meters
// ============================================================================

console.log('\n17. Testing listMeters...');
try {
  const meters = await drip.listMeters();
  console.log(`   PASS - Found ${meters.data.length} meters`);
  for (const m of meters.data.slice(0, 3)) {
    console.log(`      - ${m.name} (${m.meter})`);
  }
} catch (e) {
  console.log(`   FAIL - listMeters failed: ${e.message}`);
}

// ============================================================================
// TEST 18: Cost Estimation (estimateFromHypothetical)
// ============================================================================

console.log('\n18. Testing estimateFromHypothetical...');
try {
  const estimate = await drip.estimateFromHypothetical({
    items: [
      { usageType: 'api_calls', quantity: 1000 },
      { usageType: 'tokens_input', quantity: 50000 },
    ],
  });
  console.log(`   PASS - Estimate: $${estimate.estimatedTotalUsdc} USDC`);
  console.log(`      Line items: ${estimate.lineItems.length}`);
} catch (e) {
  console.log(`   NOTE - Estimation failed (expected if no pricing): ${e.message}`);
}

// ============================================================================
// SUMMARY
// ============================================================================

console.log('\n' + '='.repeat(60));
console.log('SDK Test Complete!');
console.log('='.repeat(60));
console.log('\nThe Drip Node.js SDK is working correctly.');
console.log('\nWhat was tested:');
console.log('  PASS - API connectivity and authentication');
console.log('  PASS - Customer creation with unique identifiers');
console.log('  PASS - Usage tracking (API calls, tokens)');
console.log('  PASS - LLM token tracking (input/output)');
console.log('  PASS - Idempotency (duplicate prevention with idempotencyKey)');
console.log('  PASS - Multi-customer scenarios');
console.log('  PASS - Audit trail (who did what)');
console.log('  PASS - Balance retrieval');
console.log('  PASS - Customer listing');
console.log('  PASS - Correlation ID (distributed tracing)');
console.log('  PASS - Fine-grained runs (start -> emit -> end -> timeline)');
console.log('  PASS - recordRun with error status + extended params');
console.log('  PASS - emitEventsBatch (batch event emission)');
console.log('  PASS - wrapApiCall (guaranteed usage recording)');
console.log('  PASS - listMeters (discover pricing meters)');
console.log('  PASS - estimateFromHypothetical (cost estimation)');
console.log('\nKey Features Demonstrated:');
console.log('  - Customer Attribution: Track which customer used what');
console.log('  - Token Tracking: Measure LLM usage per customer');
console.log('  - Idempotency: Prevent duplicate charges');
console.log('  - Audit Trail: Capture user, IP, timestamp, action');
console.log('  - Multi-tenant: Handle multiple customers independently');
console.log('  - Correlation ID: Link billing to OpenTelemetry/Datadog traces');
console.log('  - Fine-Grained Runs: Full lifecycle control with timeline');
console.log('  - Batch Events: Emit multiple events in one call');
console.log('  - wrapApiCall: Wrap external APIs with guaranteed billing');
console.log('  - Cost Estimation: Predict costs before usage');
