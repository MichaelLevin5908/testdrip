/**
 * API Contract Tests
 *
 * Captures every fetch() call the SDK makes and asserts the exact URL path,
 * HTTP method, headers, and body shape. This is the single highest-value test
 * file: it will break the instant the SDK or backend drifts.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Drip } from '@drip-sdk/node';
import {
  installMockFetch,
  mockJsonResponse,
  mockCustomer,
  mockChargeResult,
  mockTrackUsageResult,
  mockBalanceResult,
  mockWebhook,
  mockWorkflow,
  mockRunResult,
  mockEventResult,
  mockRecordRunResult,
  BASE_URL,
} from '../helpers/mock-fetch.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_KEY = 'sk_test_mock_key_123';

/** Extract [url, init] from the Nth fetch call (0-indexed). */
function fetchCall(mockFetch: ReturnType<typeof installMockFetch>, index = 0) {
  const call = mockFetch.mock.calls[index];
  if (!call) throw new Error(`No fetch call at index ${index}`);
  const [url, init] = call;
  return {
    url: url as string,
    method: (init?.method ?? 'GET') as string,
    headers: (init?.headers ?? {}) as Record<string, string>,
    body: init?.body ? JSON.parse(init.body as string) : undefined,
  };
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

let mockFetch: ReturnType<typeof installMockFetch>;
let drip: Drip;
let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
  mockFetch = installMockFetch();
  drip = new Drip({ apiKey: API_KEY, baseUrl: BASE_URL });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

// ===========================================================================
// Customers
// ===========================================================================

describe('Customers', () => {
  it('createCustomer → POST /customers', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockCustomer()));

    await drip.createCustomer({
      externalCustomerId: 'ext_user_789',
      onchainAddress: '0x1234567890abcdef1234567890abcdef12345678',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/customers`);
    expect(req.method).toBe('POST');
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
    expect(req.headers['Content-Type']).toBe('application/json');
    expect(req.body).toEqual({
      externalCustomerId: 'ext_user_789',
      onchainAddress: '0x1234567890abcdef1234567890abcdef12345678',
    });
  });

  it('getCustomer → GET /customers/{id}', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockCustomer()));

    await drip.getCustomer('cust_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/customers/cust_test_123`);
    expect(req.method).toBe('GET');
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
  });

  it('listCustomers → GET /customers (no params)', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ data: [mockCustomer()], count: 1 }),
    );

    await drip.listCustomers();

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/customers`);
    expect(req.method).toBe('GET');
  });

  it('listCustomers → GET /customers?limit=10&status=ACTIVE', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ data: [mockCustomer()], count: 1 }),
    );

    await drip.listCustomers({ limit: 10, status: 'ACTIVE' });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/customers?limit=10&status=ACTIVE`);
    expect(req.method).toBe('GET');
  });
});

// ===========================================================================
// Balance
// ===========================================================================

describe('Balance', () => {
  it('getBalance → GET /customers/{id}/balance', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockBalanceResult()));

    await drip.getBalance('cust_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/customers/cust_test_123/balance`);
    expect(req.method).toBe('GET');
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
  });
});

// ===========================================================================
// Charges / Usage
// ===========================================================================

describe('Charges & Usage', () => {
  it('charge → POST /usage (meter maps to usageType, auto idempotencyKey)', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockChargeResult()));

    await drip.charge({
      customerId: 'cust_test_123',
      meter: 'api_calls',
      quantity: 100,
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/usage`);
    expect(req.method).toBe('POST');
    expect(req.headers['Content-Type']).toBe('application/json');
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
    // Key mapping: SDK's "meter" becomes "usageType" in the body
    expect(req.body.usageType).toBe('api_calls');
    expect(req.body.customerId).toBe('cust_test_123');
    expect(req.body.quantity).toBe(100);
    // idempotencyKey is auto-generated when not provided
    expect(typeof req.body.idempotencyKey).toBe('string');
    expect(req.body.idempotencyKey.length).toBeGreaterThan(0);
    // "meter" should NOT appear in the body (it was mapped)
    expect(req.body.meter).toBeUndefined();
  });

  it('charge with explicit idempotencyKey → preserved in body', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockChargeResult()));

    await drip.charge({
      customerId: 'cust_test_123',
      meter: 'tokens',
      quantity: 500,
      idempotencyKey: 'my_custom_key_42',
    });

    const req = fetchCall(mockFetch);
    expect(req.body.idempotencyKey).toBe('my_custom_key_42');
  });

  it('trackUsage → POST /usage/internal (meter maps to usageType)', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockTrackUsageResult()));

    await drip.trackUsage({
      customerId: 'cust_test_123',
      meter: 'api_calls',
      quantity: 1,
      description: 'Test tracking',
      units: 'requests',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/usage/internal`);
    expect(req.method).toBe('POST');
    expect(req.body.usageType).toBe('api_calls');
    expect(req.body.customerId).toBe('cust_test_123');
    expect(req.body.quantity).toBe(1);
    expect(req.body.description).toBe('Test tracking');
    expect(req.body.units).toBe('requests');
    expect(typeof req.body.idempotencyKey).toBe('string');
    expect(req.body.meter).toBeUndefined();
  });

  it('getCharge → GET /charges/{id}', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        id: 'chg_test_def',
        usageId: 'evt_test_abc',
        customerId: 'cust_test_123',
        customer: { id: 'cust_test_123', onchainAddress: '0x1234', externalCustomerId: null },
        usageEvent: { id: 'evt_test_abc', type: 'api_calls', quantity: '100', metadata: null },
        amountUsdc: '0.005000',
        amountToken: '5000',
        txHash: null,
        blockNumber: null,
        status: 'PENDING',
        failureReason: null,
        createdAt: '2024-01-01T00:00:00.000Z',
        confirmedAt: null,
      }),
    );

    await drip.getCharge('chg_test_def');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/charges/chg_test_def`);
    expect(req.method).toBe('GET');
  });

  it('listCharges → GET /charges?customerId=...&status=...&limit=...&offset=...', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ data: [], count: 0 }),
    );

    await drip.listCharges({
      customerId: 'cust_test_123',
      status: 'PENDING',
      limit: 25,
      offset: 10,
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(
      `${BASE_URL}/charges?customerId=cust_test_123&status=PENDING&limit=25&offset=10`,
    );
    expect(req.method).toBe('GET');
  });

  it('getChargeStatus → GET /charges/{id}/status', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        id: 'chg_test_def',
        status: 'CONFIRMED',
        txHash: '0xabc',
        confirmedAt: '2024-01-01T00:00:00.000Z',
        failureReason: null,
      }),
    );

    await drip.getChargeStatus('chg_test_def');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/charges/chg_test_def/status`);
    expect(req.method).toBe('GET');
  });
});

// ===========================================================================
// Checkout
// ===========================================================================

describe('Checkout', () => {
  it('checkout → POST /checkout (camelCase params map to snake_case body)', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        id: 'cs_test_123',
        url: 'https://checkout.example.com/cs_test_123',
        expires_at: '2024-01-01T01:00:00.000Z',
        amount_usd: 50,
      }),
    );

    await drip.checkout({
      customerId: 'cust_test_123',
      amount: 5000,
      returnUrl: 'https://myapp.com/dashboard',
      cancelUrl: 'https://myapp.com/cancel',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/checkout`);
    expect(req.method).toBe('POST');
    // SDK maps camelCase to snake_case for the checkout body
    expect(req.body.customer_id).toBe('cust_test_123');
    expect(req.body.amount).toBe(5000);
    expect(req.body.return_url).toBe('https://myapp.com/dashboard');
    expect(req.body.cancel_url).toBe('https://myapp.com/cancel');
    // Verify camelCase keys are NOT in body
    expect(req.body.customerId).toBeUndefined();
    expect(req.body.returnUrl).toBeUndefined();
    expect(req.body.cancelUrl).toBeUndefined();
  });
});

// ===========================================================================
// Webhooks
// ===========================================================================

describe('Webhooks', () => {
  it('createWebhook → POST /webhooks', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        ...mockWebhook(),
        secret: 'whsec_test_secret',
        message: 'Save this secret!',
      }),
    );

    await drip.createWebhook({
      url: 'https://example.com/webhooks',
      events: ['charge.succeeded', 'charge.failed'],
      description: 'Test webhook',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/webhooks`);
    expect(req.method).toBe('POST');
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
    expect(req.body.url).toBe('https://example.com/webhooks');
    expect(req.body.events).toEqual(['charge.succeeded', 'charge.failed']);
    expect(req.body.description).toBe('Test webhook');
  });

  it('listWebhooks → GET /webhooks', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ data: [mockWebhook()], count: 1 }),
    );

    await drip.listWebhooks();

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/webhooks`);
    expect(req.method).toBe('GET');
  });

  it('getWebhook → GET /webhooks/{id}', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockWebhook()));

    await drip.getWebhook('wh_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/webhooks/wh_test_123`);
    expect(req.method).toBe('GET');
  });

  it('deleteWebhook → DELETE /webhooks/{id}', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ success: true }),
    );

    await drip.deleteWebhook('wh_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/webhooks/wh_test_123`);
    expect(req.method).toBe('DELETE');
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
  });

  it('testWebhook → POST /webhooks/{id}/test', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        message: 'Test event sent',
        deliveryId: 'del_test_123',
        status: 'delivered',
      }),
    );

    await drip.testWebhook('wh_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/webhooks/wh_test_123/test`);
    expect(req.method).toBe('POST');
  });

  it('rotateWebhookSecret → POST /webhooks/{id}/rotate-secret', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ secret: 'whsec_new_secret', message: 'Rotated!' }),
    );

    await drip.rotateWebhookSecret('wh_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/webhooks/wh_test_123/rotate-secret`);
    expect(req.method).toBe('POST');
  });
});

// ===========================================================================
// Workflows
// ===========================================================================

describe('Workflows', () => {
  it('createWorkflow → POST /workflows', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockWorkflow()));

    await drip.createWorkflow({
      name: 'Test Workflow',
      slug: 'test_workflow',
      productSurface: 'CUSTOM',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/workflows`);
    expect(req.method).toBe('POST');
    expect(req.body.name).toBe('Test Workflow');
    expect(req.body.slug).toBe('test_workflow');
    expect(req.body.productSurface).toBe('CUSTOM');
  });

  it('listWorkflows → GET /workflows', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ data: [mockWorkflow()], count: 1 }),
    );

    await drip.listWorkflows();

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/workflows`);
    expect(req.method).toBe('GET');
  });
});

// ===========================================================================
// Runs
// ===========================================================================

describe('Runs', () => {
  it('startRun → POST /runs', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockRunResult()));

    await drip.startRun({
      customerId: 'cust_test_123',
      workflowId: 'wf_test_123',
      correlationId: 'corr_456',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/runs`);
    expect(req.method).toBe('POST');
    expect(req.body.customerId).toBe('cust_test_123');
    expect(req.body.workflowId).toBe('wf_test_123');
    expect(req.body.correlationId).toBe('corr_456');
  });

  it('endRun → PATCH /runs/{id}', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        id: 'run_test_123',
        status: 'COMPLETED',
        endedAt: '2024-01-01T00:01:00.000Z',
        durationMs: 1500,
        eventCount: 3,
        totalCostUnits: '0.25',
      }),
    );

    await drip.endRun('run_test_123', { status: 'COMPLETED' });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/runs/run_test_123`);
    expect(req.method).toBe('PATCH');
    expect(req.body.status).toBe('COMPLETED');
  });

  it('getRun → GET /runs/{id}', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        id: 'run_test_123',
        customerId: 'cust_test_123',
        customerName: null,
        workflowId: 'wf_test_123',
        workflowName: 'Test',
        status: 'RUNNING',
        startedAt: null,
        endedAt: null,
        durationMs: null,
        errorMessage: null,
        errorCode: null,
        correlationId: null,
        metadata: null,
        totals: { eventCount: 0, totalQuantity: '0', totalCostUnits: '0' },
        _links: { timeline: '/runs/run_test_123/timeline' },
      }),
    );

    await drip.getRun('run_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/runs/run_test_123`);
    expect(req.method).toBe('GET');
  });

  it('getRunTimeline → GET /runs/{id}/timeline (no params)', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        runId: 'run_test_123',
        workflowId: null,
        workflowName: null,
        customerId: 'cust_test_123',
        status: 'RUNNING',
        correlationId: null,
        metadata: null,
        errorMessage: null,
        errorCode: null,
        startedAt: null,
        endedAt: null,
        durationMs: null,
        events: [],
        anomalies: [],
        summary: { totalEvents: 0, byType: {}, byOutcome: {}, retriedEvents: 0, failedEvents: 0, totalCostUsdc: null },
        hasMore: false,
        nextCursor: null,
      }),
    );

    await drip.getRunTimeline('run_test_123');

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/runs/run_test_123/timeline`);
    expect(req.method).toBe('GET');
  });

  it('getRunTimeline → GET /runs/{id}/timeline?limit=...&cursor=...', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        runId: 'run_test_123',
        workflowId: null,
        workflowName: null,
        customerId: 'cust_test_123',
        status: 'RUNNING',
        correlationId: null,
        metadata: null,
        errorMessage: null,
        errorCode: null,
        startedAt: null,
        endedAt: null,
        durationMs: null,
        events: [],
        anomalies: [],
        summary: { totalEvents: 0, byType: {}, byOutcome: {}, retriedEvents: 0, failedEvents: 0, totalCostUsdc: null },
        hasMore: false,
        nextCursor: null,
      }),
    );

    await drip.getRunTimeline('run_test_123', { limit: 50, cursor: 'abc' });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(
      `${BASE_URL}/runs/run_test_123/timeline?limit=50&cursor=abc`,
    );
  });
});

// ===========================================================================
// Events
// ===========================================================================

describe('Events', () => {
  it('emitEvent → POST /run-events', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEventResult()));

    await drip.emitEvent({
      runId: 'run_test_123',
      eventType: 'agent.step',
      quantity: 1,
      description: 'Test step',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/run-events`);
    expect(req.method).toBe('POST');
    expect(req.body.runId).toBe('run_test_123');
    expect(req.body.eventType).toBe('agent.step');
    expect(req.body.quantity).toBe(1);
    expect(req.body.description).toBe('Test step');
    // Auto-generated idempotency key
    expect(typeof req.body.idempotencyKey).toBe('string');
  });

  it('emitEventsBatch → POST /run-events/batch with { events: [...] }', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        success: true,
        created: 2,
        duplicates: 0,
        skipped: 0,
        events: [
          { id: 'revt_1', eventType: 'step1', isDuplicate: false },
          { id: 'revt_2', eventType: 'step2', isDuplicate: false },
        ],
      }),
    );

    await drip.emitEventsBatch([
      { runId: 'run_test_123', eventType: 'step1', quantity: 1 },
      { runId: 'run_test_123', eventType: 'step2', quantity: 100, units: 'tokens' },
    ]);

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/run-events/batch`);
    expect(req.method).toBe('POST');
    // Body wraps events in an "events" array
    expect(req.body.events).toBeInstanceOf(Array);
    expect(req.body.events).toHaveLength(2);
    expect(req.body.events[0].eventType).toBe('step1');
    expect(req.body.events[1].units).toBe('tokens');
  });
});

// ===========================================================================
// Record Run
// ===========================================================================

describe('Record Run', () => {
  it('recordRun → POST /runs/record', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockRecordRunResult()));

    await drip.recordRun({
      customerId: 'cust_test_123',
      workflow: 'test_workflow',
      events: [
        { eventType: 'agent.start', description: 'Started' },
        { eventType: 'tool.ocr', quantity: 3, units: 'pages' },
      ],
      status: 'COMPLETED',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/runs/record`);
    expect(req.method).toBe('POST');
    expect(req.body.customerId).toBe('cust_test_123');
    expect(req.body.workflow).toBe('test_workflow');
    expect(req.body.events).toHaveLength(2);
    expect(req.body.status).toBe('COMPLETED');
  });
});

// ===========================================================================
// Meters
// ===========================================================================

describe('Meters', () => {
  it('listMeters → GET /pricing-plans (SDK maps endpoint name)', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        data: [
          {
            id: 'pp_test_1',
            name: 'API Calls',
            unitType: 'api_calls',
            unitPriceUsd: '0.005',
            isActive: true,
          },
        ],
        count: 1,
      }),
    );

    const result = await drip.listMeters();

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/pricing-plans`);
    expect(req.method).toBe('GET');
    // SDK maps unitType -> meter in the response
    expect(result.data[0].meter).toBe('api_calls');
  });
});

// ===========================================================================
// Cost Estimation
// ===========================================================================

describe('Cost Estimation', () => {
  it('estimateFromUsage → POST /dashboard/cost-estimate/from-usage (Date -> ISO strings)', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        lineItems: [],
        subtotalUsdc: '0.000000',
        estimatedTotalUsdc: '0.000000',
        currency: 'USDC',
        isEstimate: true,
        generatedAt: '2024-01-01T00:00:00.000Z',
        notes: [],
      }),
    );

    const periodStart = new Date('2024-01-01T00:00:00.000Z');
    const periodEnd = new Date('2024-01-31T23:59:59.000Z');

    await drip.estimateFromUsage({
      customerId: 'cust_test_123',
      periodStart,
      periodEnd,
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/dashboard/cost-estimate/from-usage`);
    expect(req.method).toBe('POST');
    // Date objects are converted to ISO strings in the body
    expect(req.body.periodStart).toBe(periodStart.toISOString());
    expect(req.body.periodEnd).toBe(periodEnd.toISOString());
    expect(req.body.customerId).toBe('cust_test_123');
  });

  it('estimateFromHypothetical → POST /dashboard/cost-estimate/hypothetical', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        lineItems: [
          {
            usageType: 'api_call',
            quantity: '10000',
            unitPrice: '0.005',
            estimatedCostUsdc: '50.000000',
            hasPricingPlan: true,
          },
        ],
        subtotalUsdc: '50.000000',
        estimatedTotalUsdc: '50.000000',
        currency: 'USDC',
        isEstimate: true,
        generatedAt: '2024-01-01T00:00:00.000Z',
        notes: [],
      }),
    );

    await drip.estimateFromHypothetical({
      items: [{ usageType: 'api_call', quantity: 10000 }],
      defaultUnitPrice: '0.005',
    });

    const req = fetchCall(mockFetch);
    expect(req.url).toBe(`${BASE_URL}/dashboard/cost-estimate/hypothetical`);
    expect(req.method).toBe('POST');
    expect(req.body.items).toEqual([{ usageType: 'api_call', quantity: 10000 }]);
    expect(req.body.defaultUnitPrice).toBe('0.005');
  });
});

// ===========================================================================
// Ping / Health
// ===========================================================================

describe('Ping', () => {
  it('ping → GET {baseUrl without /v1}/health (strips /v1)', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ status: 'healthy', timestamp: Date.now() }),
    );

    await drip.ping();

    const req = fetchCall(mockFetch);
    // BASE_URL is https://mock.drip.test/v1 → ping should strip /v1
    const expectedUrl = BASE_URL.replace(/\/v1$/, '') + '/health';
    expect(req.url).toBe(expectedUrl);
    expect(req.method).toBe('GET');
  });
});

// ===========================================================================
// Header assertions (apply to all endpoints)
// ===========================================================================

describe('Common headers', () => {
  it('every POST request includes Content-Type: application/json', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockCustomer()));

    await drip.createCustomer({ onchainAddress: '0x' + 'ab'.repeat(20) });

    const req = fetchCall(mockFetch);
    expect(req.headers['Content-Type']).toBe('application/json');
  });

  it('every request includes Authorization: Bearer <key>', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ data: [], count: 0 }),
    );

    await drip.listCustomers();

    const req = fetchCall(mockFetch);
    expect(req.headers['Authorization']).toBe(`Bearer ${API_KEY}`);
  });
});
