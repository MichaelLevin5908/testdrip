/**
 * test_full_e2e.mjs — Node.js SDK end-to-end test
 * Covers: createCustomer, provision, sync-balance, charge, recordRun,
 *         emitEventsBatch, wrapApiCall, createStreamMeter, listCharges, getBalance
 */
import { readFileSync } from 'fs';
import { Drip } from '@drip-sdk/node';

// Load .env
try {
  for (const line of readFileSync(new URL('./.env', import.meta.url), 'utf8').split('\n')) {
    const [k, ...v] = line.split('=');
    if (k && v.length && !k.startsWith('#')) process.env[k.trim()] = v.join('=').trim();
  }
} catch {}

const API_KEY = process.env.DRIP_API_KEY;
const API_URL = process.env.DRIP_API_URL || 'https://drip-app-hlunj.ondigitalocean.app/v1';
if (!API_KEY) { console.error('❌  DRIP_API_KEY not set'); process.exit(1); }

const drip = new Drip({ apiKey: API_KEY, baseUrl: API_URL });
const runId = Math.random().toString(36).slice(2, 10);
let passed = 0, failed = 0, skipped = 0;
let customerId = null, smartAccount = null;

const ok = (l, d = '') => { passed++; console.log(`  ✅  ${l}${d ? `  →  ${d}` : ''}`); };
const fail = (l, e) => { failed++; console.log(`  ❌  ${l}\n       ${e?.message ?? e}`); };
const skip = (l, r) => { skipped++; console.log(`  ⚠️   ${l} — ${r}`); };
const section = t => console.log(`\n${'─'.repeat(60)}\n  ${t}\n${'─'.repeat(60)}`);
const api = async (method, path, body) => {
  const r = await fetch(`${API_URL}${path}`, {
    method, headers: { Authorization: `Bearer ${API_KEY}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return [await r.json(), r.status];
};

// ─────────────────────────────────────────────────────────────
section('1. CREATE CUSTOMER');
// ─────────────────────────────────────────────────────────────
try {
  const c = await drip.createCustomer({ externalCustomerId: `node_e2e_${runId}` });
  customerId = c.id;
  ok('createCustomer', `id=${customerId}`);
} catch (e) { fail('createCustomer', e); }

// ─────────────────────────────────────────────────────────────
section('2. PROVISION SMART ACCOUNT');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  try {
    const [data, status] = await api('POST', `/customers/${customerId}/provision`, {});
    if (status === 200) {
      smartAccount = data.smart_account_address;
      ok('provision', `addr=${smartAccount}, $${data.billing_balance_usdc} USDC`);
    } else { fail('provision', new Error(JSON.stringify(data))); }
  } catch (e) { fail('provision', e); }
}

// ─────────────────────────────────────────────────────────────
section('3. SYNC BALANCE');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  try {
    const [data] = await api('POST', `/customers/${customerId}/sync-balance`, {});
    ok('sync-balance', `$${data.newBalance} USDC (changed=${data.changed})`);
  } catch (e) { fail('sync-balance', e); }
}

// ─────────────────────────────────────────────────────────────
section('4. CHARGES');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  for (const [meter, qty] of [['api_calls', 10], ['tokens', 2000], ['compute_seconds', 20]]) {
    try {
      const r = await drip.charge({ customerId, meter, quantity: qty });
      ok(`charge(${meter}, qty=${qty})`, `$${r.charge?.amountUsdc ?? '?'} USDC, status=${r.charge?.status ?? '?'}`);
    } catch (e) {
      e?.code === 'PAYMENT_REQUIRED' ? skip(`charge(${meter})`, 'INSUFFICIENT_BALANCE') : fail(`charge(${meter})`, e);
    }
  }
}

// ─────────────────────────────────────────────────────────────
section('5. recordRun (single-call full snapshot)');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  try {
    const r = await drip.recordRun({
      customerId,
      workflow: `node-pipeline-${runId}`,
      status: 'COMPLETED',
      events: [
        { eventType: 'input.tokens', quantity: 800, units: 'tokens' },
        { eventType: 'tool.call', quantity: 2, units: 'tool_calls' },
        { eventType: 'output.tokens', quantity: 400, units: 'tokens' },
      ],
      metadata: { model: 'gpt-4o', sdk: 'node' },
    });
    ok('recordRun (3 events)', `runId=${r.run?.id}, created=${r.events?.created}`);
  } catch (e) { fail('recordRun', e); }
}

// ─────────────────────────────────────────────────────────────
section('6. EMIT EVENTS BATCH');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  try {
    // recordRun creates a run; use its ID for batch events
    const run = await drip.recordRun({
      customerId,
      workflow: `node-batch-${runId}`,
      status: 'COMPLETED',
      events: [{ eventType: 'init', quantity: 1 }],
    });
    const runId2 = run.run?.id;
    const result = await drip.emitEventsBatch([
      { runId: runId2, eventType: 'step.1', quantity: 1, idempotencyKey: `${runId}_s1` },
      { runId: runId2, eventType: 'step.2', quantity: 1, idempotencyKey: `${runId}_s2` },
      { runId: runId2, eventType: 'tokens.out', quantity: 600, units: 'tokens', idempotencyKey: `${runId}_s3` },
    ]);
    ok('emitEventsBatch (3 events)', `created=${result.created}, dupes=${result.duplicates}`);
  } catch (e) { fail('emitEventsBatch', e); }
}

// ─────────────────────────────────────────────────────────────
section('7. wrapApiCall');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  try {
    const result = await drip.wrapApiCall({
      customerId,
      meter: 'tokens',
      call: async () => ({ inputTokens: 400, outputTokens: 200 }),
      extractUsage: r => r.inputTokens + r.outputTokens,
      metadata: { model: 'mock-llm', sdk: 'node' },
    });
    const tokens = result.result.inputTokens + result.result.outputTokens;
    ok('wrapApiCall (mock LLM)', `tokens=${tokens}, charge=$${result.charge?.charge?.amountUsdc ?? '?'} USDC`);
    ok('idempotencyKey', result.idempotencyKey);
  } catch (e) {
    e?.code === 'PAYMENT_REQUIRED' ? skip('wrapApiCall', 'INSUFFICIENT_BALANCE') : fail('wrapApiCall', e);
  }
}

// ─────────────────────────────────────────────────────────────
section('8. StreamMeter');
// ─────────────────────────────────────────────────────────────
if (customerId) {
  try {
    const meter = drip.createStreamMeter({ customerId, meter: 'tokens' });
    meter.add(200); meter.add(300); meter.add(150);
    ok('StreamMeter accumulated', `total=${meter.total} tokens`);
    const r = await meter.flush();
    ok('StreamMeter flush (650 tokens)', `success=${r.success}, charge=$${r.charge?.amountUsdc ?? '?'} USDC`);
  } catch (e) {
    e?.code === 'PAYMENT_REQUIRED' ? skip('StreamMeter', 'INSUFFICIENT_BALANCE') : fail('StreamMeter', e);
  }
}

// ─────────────────────────────────────────────────────────────
section('9. LIST + BALANCE');
// ─────────────────────────────────────────────────────────────
try {
  const customers = await drip.listCustomers({ limit: 5 });
  ok('listCustomers', `count=${customers.count}`);
} catch (e) { fail('listCustomers', e); }

try {
  const charges = await drip.listCharges();
  ok('listCharges', `count=${charges.count}`);
  if (charges.data?.[0]) {
    const c = charges.data[0];
    ok('Latest charge', `meter=${c.usageType ?? '?'}, $${c.amountUsdc ?? '?'}, status=${c.status ?? '?'}`);
  }
} catch (e) { fail('listCharges', e); }

if (customerId) {
  try {
    const b = await drip.getBalance(customerId);
    ok('getBalance', JSON.stringify(b).slice(0, 120));
  } catch (e) { fail('getBalance', e); }
}

// ─────────────────────────────────────────────────────────────
console.log(`\n${'═'.repeat(60)}`);
console.log(`  RESULTS:  ✅ ${passed} passed   ❌ ${failed} failed   ⚠️  ${skipped} skipped`);
console.log(`${'═'.repeat(60)}\n`);
if (customerId) console.log(`  Customer:      ${customerId}`);
if (smartAccount) console.log(`  Smart Account: ${smartAccount}\n  BaseScan:      https://sepolia.basescan.org/address/${smartAccount}\n`);
process.exit(failed > 0 ? 1 : 0);
