/**
 * Unit Tests: Every public method of the Drip class with mocked fetch.
 *
 * Tests cover: customers, charges, checkout, webhooks, runs, workflows,
 * meters, cost estimation, static methods, error handling, and ping.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Drip, DripError } from '@drip-sdk/node';
import {
  installMockFetch,
  mockJsonResponse,
  mockErrorResponse,
  mockCustomer,
  mockChargeResult,
  mockTrackUsageResult,
  mockBalanceResult,
  mockWebhook,
  mockWorkflow,
  mockRunResult,
  mockEventResult,
  mockRecordRunResult,
  createTestDrip,
  BASE_URL,
} from '../helpers/mock-fetch.js';

let mockFetch: ReturnType<typeof installMockFetch>;
let drip: Drip;

beforeEach(() => {
  mockFetch = installMockFetch();
  drip = createTestDrip('secret');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ============================================================================
// Helper to extract fetch call info
// ============================================================================

function getLastCallUrl(): string {
  const call = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
  return call[0] as string;
}

function getLastCallInit(): RequestInit {
  const call = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
  return call[1] as RequestInit;
}

function getLastCallBody(): Record<string, unknown> {
  const init = getLastCallInit();
  return JSON.parse(init.body as string);
}

// ============================================================================
// Customer Methods
// ============================================================================

describe('Customer methods', () => {
  describe('createCustomer', () => {
    it('sends POST to /customers with params', async () => {
      const customer = mockCustomer();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(customer));

      const result = await drip.createCustomer({
        externalCustomerId: 'ext_user_789',
        onchainAddress: '0x1234567890abcdef1234567890abcdef12345678',
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/customers`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.externalCustomerId).toBe('ext_user_789');
      expect(body.onchainAddress).toBe('0x1234567890abcdef1234567890abcdef12345678');
      expect(result.id).toBe('cust_test_123');
      expect(result.status).toBe('ACTIVE');
    });

    it('returns correct customer shape', async () => {
      const customer = mockCustomer({ metadata: { plan: 'pro' } });
      mockFetch.mockResolvedValueOnce(mockJsonResponse(customer));

      const result = await drip.createCustomer({
        externalCustomerId: 'ext_user_789',
      });

      expect(result).toHaveProperty('id');
      expect(result).toHaveProperty('externalCustomerId');
      expect(result).toHaveProperty('onchainAddress');
      expect(result).toHaveProperty('createdAt');
      expect(result.metadata).toEqual({ plan: 'pro' });
    });
  });

  describe('getCustomer', () => {
    it('sends GET to /customers/{id}', async () => {
      const customer = mockCustomer();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(customer));

      const result = await drip.getCustomer('cust_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/customers/cust_test_123`);
      expect(getLastCallInit().method).toBeUndefined(); // GET is default, no method set
      expect(result.id).toBe('cust_test_123');
    });
  });

  describe('listCustomers', () => {
    it('sends GET to /customers with no params', async () => {
      const response = { data: [mockCustomer()], count: 1 };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      const result = await drip.listCustomers();

      expect(getLastCallUrl()).toBe(`${BASE_URL}/customers`);
      expect(result.data).toHaveLength(1);
      expect(result.count).toBe(1);
    });

    it('sends GET to /customers with query params', async () => {
      const response = { data: [mockCustomer()], count: 1 };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      await drip.listCustomers({ limit: 10, status: 'ACTIVE' });

      const url = getLastCallUrl();
      expect(url).toContain('/customers?');
      expect(url).toContain('limit=10');
      expect(url).toContain('status=ACTIVE');
    });
  });

  describe('getBalance', () => {
    it('sends GET to /customers/{id}/balance', async () => {
      const balance = mockBalanceResult();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(balance));

      const result = await drip.getBalance('cust_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/customers/cust_test_123/balance`);
      expect(result.customerId).toBe('cust_test_123');
      expect(result.balanceUsdc).toBe('100.000000');
      expect(result.availableUsdc).toBe('95.000000');
    });
  });
});

// ============================================================================
// Charge Methods
// ============================================================================

describe('Charge methods', () => {
  describe('charge', () => {
    it('sends POST to /usage with meter mapped to usageType', async () => {
      const chargeResult = mockChargeResult();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(chargeResult));

      const result = await drip.charge({
        customerId: 'cust_test_123',
        meter: 'api_calls',
        quantity: 100,
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/usage`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.customerId).toBe('cust_test_123');
      expect(body.usageType).toBe('api_calls');
      expect(body.quantity).toBe(100);
      expect(body.idempotencyKey).toBeDefined();
      expect(result.success).toBe(true);
      expect(result.charge.amountUsdc).toBe('0.005000');
    });

    it('uses provided idempotencyKey', async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse(mockChargeResult()));

      await drip.charge({
        customerId: 'cust_test_123',
        meter: 'api_calls',
        quantity: 1,
        idempotencyKey: 'my_custom_key',
      });

      const body = getLastCallBody();
      expect(body.idempotencyKey).toBe('my_custom_key');
    });

    it('includes metadata when provided', async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse(mockChargeResult()));

      await drip.charge({
        customerId: 'cust_test_123',
        meter: 'api_calls',
        quantity: 1,
        metadata: { source: 'test' },
      });

      const body = getLastCallBody();
      expect(body.metadata).toEqual({ source: 'test' });
    });
  });

  describe('trackUsage', () => {
    it('sends POST to /usage/internal with fields mapped', async () => {
      const trackResult = mockTrackUsageResult();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(trackResult));

      const result = await drip.trackUsage({
        customerId: 'cust_test_123',
        meter: 'api_calls',
        quantity: 1,
        units: 'requests',
        description: 'Test API call',
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/usage/internal`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.customerId).toBe('cust_test_123');
      expect(body.usageType).toBe('api_calls');
      expect(body.quantity).toBe(1);
      expect(body.units).toBe('requests');
      expect(body.description).toBe('Test API call');
      expect(body.idempotencyKey).toBeDefined();
      expect(result.success).toBe(true);
      expect(result.usageEventId).toBe('evt_test_track');
    });
  });

  describe('getCharge', () => {
    it('sends GET to /charges/{id}', async () => {
      const charge = {
        id: 'chg_test_def',
        usageId: 'evt_test_abc',
        customerId: 'cust_test_123',
        amountUsdc: '0.005000',
        status: 'CONFIRMED',
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(charge));

      const result = await drip.getCharge('chg_test_def');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/charges/chg_test_def`);
      expect(result.id).toBe('chg_test_def');
    });
  });

  describe('listCharges', () => {
    it('sends GET to /charges with query params', async () => {
      const response = { data: [], count: 0 };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      await drip.listCharges({ customerId: 'cust_test_123', status: 'PENDING' });

      const url = getLastCallUrl();
      expect(url).toContain('/charges?');
      expect(url).toContain('customerId=cust_test_123');
      expect(url).toContain('status=PENDING');
    });

    it('sends GET to /charges with no params', async () => {
      const response = { data: [], count: 0 };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      await drip.listCharges();

      expect(getLastCallUrl()).toBe(`${BASE_URL}/charges`);
    });
  });

  describe('getChargeStatus', () => {
    it('sends GET to /charges/{id}/status', async () => {
      const status = {
        id: 'chg_test_def',
        status: 'CONFIRMED',
        txHash: '0xabc',
        confirmedAt: '2024-01-01T00:00:00.000Z',
        failureReason: null,
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(status));

      const result = await drip.getChargeStatus('chg_test_def');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/charges/chg_test_def/status`);
      expect(result.status).toBe('CONFIRMED');
      expect(result.txHash).toBe('0xabc');
    });
  });
});

// ============================================================================
// Checkout
// ============================================================================

describe('Checkout', () => {
  describe('checkout', () => {
    it('sends POST to /checkout with camelCase -> snake_case mapping', async () => {
      const serverResponse = {
        id: 'cs_test_123',
        url: 'https://checkout.drip.test/cs_test_123',
        expires_at: '2024-01-01T00:30:00.000Z',
        amount_usd: 50,
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(serverResponse));

      const result = await drip.checkout({
        customerId: 'cust_test_123',
        amount: 5000,
        returnUrl: 'https://myapp.com/dashboard',
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/checkout`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.customer_id).toBe('cust_test_123');
      expect(body.amount).toBe(5000);
      expect(body.return_url).toBe('https://myapp.com/dashboard');

      // Response maps snake_case -> camelCase
      expect(result.id).toBe('cs_test_123');
      expect(result.url).toBe('https://checkout.drip.test/cs_test_123');
      expect(result.expiresAt).toBe('2024-01-01T00:30:00.000Z');
      expect(result.amountUsd).toBe(50);
    });

    it('includes optional cancelUrl and metadata', async () => {
      const serverResponse = {
        id: 'cs_test_456',
        url: 'https://checkout.drip.test/cs_test_456',
        expires_at: '2024-01-01T00:30:00.000Z',
        amount_usd: 100,
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(serverResponse));

      await drip.checkout({
        customerId: 'cust_test_123',
        amount: 10000,
        returnUrl: 'https://myapp.com/dashboard',
        cancelUrl: 'https://myapp.com/cancel',
        metadata: { plan: 'pro' },
      });

      const body = getLastCallBody();
      expect(body.cancel_url).toBe('https://myapp.com/cancel');
      expect(body.metadata).toEqual({ plan: 'pro' });
    });
  });
});

// ============================================================================
// Webhook Methods
// ============================================================================

describe('Webhook methods', () => {
  describe('createWebhook', () => {
    it('sends POST to /webhooks', async () => {
      const webhook = { ...mockWebhook(), secret: 'whsec_test_secret', message: 'Webhook created' };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(webhook));

      const result = await drip.createWebhook({
        url: 'https://example.com/webhooks',
        events: ['charge.succeeded', 'charge.failed'],
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/webhooks`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.url).toBe('https://example.com/webhooks');
      expect(body.events).toEqual(['charge.succeeded', 'charge.failed']);
      expect(result.secret).toBe('whsec_test_secret');
      expect(result.id).toBe('wh_test_123');
    });
  });

  describe('listWebhooks', () => {
    it('sends GET to /webhooks', async () => {
      const response = { data: [mockWebhook()], count: 1 };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      const result = await drip.listWebhooks();

      expect(getLastCallUrl()).toBe(`${BASE_URL}/webhooks`);
      expect(result.data).toHaveLength(1);
    });
  });

  describe('getWebhook', () => {
    it('sends GET to /webhooks/{id}', async () => {
      const webhook = mockWebhook();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(webhook));

      const result = await drip.getWebhook('wh_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/webhooks/wh_test_123`);
      expect(result.id).toBe('wh_test_123');
    });
  });

  describe('deleteWebhook', () => {
    it('sends DELETE to /webhooks/{id}', async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ success: true }));

      const result = await drip.deleteWebhook('wh_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/webhooks/wh_test_123`);
      expect(getLastCallInit().method).toBe('DELETE');
      expect(result.success).toBe(true);
    });
  });

  describe('testWebhook', () => {
    it('sends POST to /webhooks/{id}/test', async () => {
      const response = { message: 'Test event sent', deliveryId: 'del_123', status: 'sent' };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      const result = await drip.testWebhook('wh_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/webhooks/wh_test_123/test`);
      expect(getLastCallInit().method).toBe('POST');
      expect(result.status).toBe('sent');
    });
  });

  describe('rotateWebhookSecret', () => {
    it('sends POST to /webhooks/{id}/rotate-secret', async () => {
      const response = { secret: 'whsec_new_secret', message: 'Secret rotated' };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      const result = await drip.rotateWebhookSecret('wh_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/webhooks/wh_test_123/rotate-secret`);
      expect(getLastCallInit().method).toBe('POST');
      expect(result.secret).toBe('whsec_new_secret');
    });
  });

  describe('webhook methods throw with public key', () => {
    it('createWebhook throws DripError 403 with pk_ key', async () => {
      const publicDrip = createTestDrip('public');

      await expect(
        publicDrip.createWebhook({ url: 'https://example.com', events: ['charge.succeeded'] }),
      ).rejects.toThrow(DripError);

      try {
        await publicDrip.createWebhook({ url: 'https://example.com', events: ['charge.succeeded'] });
      } catch (err) {
        expect(err).toBeInstanceOf(DripError);
        expect((err as DripError).statusCode).toBe(403);
      }
    });

    it('listWebhooks throws DripError 403 with pk_ key', async () => {
      const publicDrip = createTestDrip('public');

      await expect(publicDrip.listWebhooks()).rejects.toThrow(DripError);

      try {
        await publicDrip.listWebhooks();
      } catch (err) {
        expect((err as DripError).statusCode).toBe(403);
      }
    });

    it('getWebhook throws DripError 403 with pk_ key', async () => {
      const publicDrip = createTestDrip('public');

      await expect(publicDrip.getWebhook('wh_123')).rejects.toThrow(DripError);

      try {
        await publicDrip.getWebhook('wh_123');
      } catch (err) {
        expect((err as DripError).statusCode).toBe(403);
      }
    });

    it('deleteWebhook throws DripError 403 with pk_ key', async () => {
      const publicDrip = createTestDrip('public');

      await expect(publicDrip.deleteWebhook('wh_123')).rejects.toThrow(DripError);

      try {
        await publicDrip.deleteWebhook('wh_123');
      } catch (err) {
        expect((err as DripError).statusCode).toBe(403);
      }
    });

    it('testWebhook throws DripError 403 with pk_ key', async () => {
      const publicDrip = createTestDrip('public');

      await expect(publicDrip.testWebhook('wh_123')).rejects.toThrow(DripError);

      try {
        await publicDrip.testWebhook('wh_123');
      } catch (err) {
        expect((err as DripError).statusCode).toBe(403);
      }
    });

    it('rotateWebhookSecret throws DripError 403 with pk_ key', async () => {
      const publicDrip = createTestDrip('public');

      await expect(publicDrip.rotateWebhookSecret('wh_123')).rejects.toThrow(DripError);

      try {
        await publicDrip.rotateWebhookSecret('wh_123');
      } catch (err) {
        expect((err as DripError).statusCode).toBe(403);
      }
    });
  });
});

// ============================================================================
// Run Methods
// ============================================================================

describe('Run methods', () => {
  describe('createWorkflow', () => {
    it('sends POST to /workflows', async () => {
      const workflow = mockWorkflow();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(workflow));

      const result = await drip.createWorkflow({ name: 'Test Workflow', slug: 'test_workflow' });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/workflows`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.name).toBe('Test Workflow');
      expect(body.slug).toBe('test_workflow');
      expect(result.id).toBe('wf_test_123');
    });
  });

  describe('listWorkflows', () => {
    it('sends GET to /workflows', async () => {
      const response = { data: [mockWorkflow()], count: 1 };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

      const result = await drip.listWorkflows();

      expect(getLastCallUrl()).toBe(`${BASE_URL}/workflows`);
      expect(result.data).toHaveLength(1);
    });
  });

  describe('startRun', () => {
    it('sends POST to /runs', async () => {
      const run = mockRunResult();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(run));

      const result = await drip.startRun({
        customerId: 'cust_test_123',
        workflowId: 'wf_test_123',
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/runs`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.customerId).toBe('cust_test_123');
      expect(body.workflowId).toBe('wf_test_123');
      expect(result.id).toBe('run_test_123');
      expect(result.status).toBe('RUNNING');
    });
  });

  describe('endRun', () => {
    it('sends PATCH to /runs/{id}', async () => {
      const endResult = {
        id: 'run_test_123',
        status: 'COMPLETED',
        endedAt: '2024-01-01T00:05:00.000Z',
        durationMs: 300000,
        eventCount: 5,
        totalCostUnits: '0.50',
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(endResult));

      const result = await drip.endRun('run_test_123', { status: 'COMPLETED' });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/runs/run_test_123`);
      expect(getLastCallInit().method).toBe('PATCH');
      const body = getLastCallBody();
      expect(body.status).toBe('COMPLETED');
      expect(result.id).toBe('run_test_123');
      expect(result.status).toBe('COMPLETED');
    });
  });

  describe('getRun', () => {
    it('sends GET to /runs/{id}', async () => {
      const runDetails = {
        id: 'run_test_123',
        customerId: 'cust_test_123',
        customerName: null,
        workflowId: 'wf_test_123',
        workflowName: 'Test Workflow',
        status: 'COMPLETED',
        startedAt: '2024-01-01T00:00:00.000Z',
        endedAt: '2024-01-01T00:05:00.000Z',
        durationMs: 300000,
        errorMessage: null,
        errorCode: null,
        correlationId: null,
        metadata: null,
        totals: { eventCount: 5, totalQuantity: '100', totalCostUnits: '0.50' },
        _links: { timeline: '/runs/run_test_123/timeline' },
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(runDetails));

      const result = await drip.getRun('run_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/runs/run_test_123`);
      expect(result.id).toBe('run_test_123');
      expect(result.totals.eventCount).toBe(5);
    });
  });

  describe('getRunTimeline', () => {
    it('sends GET to /runs/{id}/timeline', async () => {
      const timeline = {
        runId: 'run_test_123',
        workflowId: 'wf_test_123',
        workflowName: 'Test Workflow',
        customerId: 'cust_test_123',
        status: 'COMPLETED',
        startedAt: '2024-01-01T00:00:00.000Z',
        endedAt: '2024-01-01T00:05:00.000Z',
        durationMs: 300000,
        events: [],
        anomalies: [],
        summary: {
          totalEvents: 0,
          byType: {},
          byOutcome: {},
          retriedEvents: 0,
          failedEvents: 0,
          totalCostUsdc: null,
        },
        hasMore: false,
        nextCursor: null,
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(timeline));

      const result = await drip.getRunTimeline('run_test_123');

      expect(getLastCallUrl()).toBe(`${BASE_URL}/runs/run_test_123/timeline`);
      expect(result.runId).toBe('run_test_123');
      expect(result.summary.totalEvents).toBe(0);
    });
  });

  describe('emitEvent', () => {
    it('sends POST to /run-events', async () => {
      const event = mockEventResult();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(event));

      const result = await drip.emitEvent({
        runId: 'run_test_123',
        eventType: 'agent.step',
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/run-events`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.runId).toBe('run_test_123');
      expect(body.eventType).toBe('agent.step');
      expect(body.idempotencyKey).toBeDefined();
      expect(result.id).toBe('revt_test_123');
    });
  });

  describe('emitEventsBatch', () => {
    it('sends POST to /run-events/batch with events array', async () => {
      const batchResult = {
        success: true,
        created: 2,
        duplicates: 0,
        skipped: 0,
        events: [
          { id: 'revt_1', eventType: 'agent.step', isDuplicate: false },
          { id: 'revt_2', eventType: 'agent.complete', isDuplicate: false },
        ],
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(batchResult));

      const result = await drip.emitEventsBatch([
        { runId: 'run_test_123', eventType: 'agent.step', quantity: 1 },
        { runId: 'run_test_123', eventType: 'agent.complete' },
      ]);

      expect(getLastCallUrl()).toBe(`${BASE_URL}/run-events/batch`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.events).toHaveLength(2);
      expect(result.created).toBe(2);
      expect(result.duplicates).toBe(0);
    });
  });

  describe('recordRun', () => {
    it('sends POST to /runs/record', async () => {
      const recordResult = mockRecordRunResult();
      mockFetch.mockResolvedValueOnce(mockJsonResponse(recordResult));

      const result = await drip.recordRun({
        customerId: 'cust_test_123',
        workflow: 'test_workflow',
        events: [
          { eventType: 'agent.start' },
          { eventType: 'agent.step', quantity: 100, units: 'tokens' },
          { eventType: 'agent.complete' },
        ],
        status: 'COMPLETED',
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/runs/record`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.customerId).toBe('cust_test_123');
      expect(body.workflow).toBe('test_workflow');
      expect(body.events).toHaveLength(3);
      expect(body.status).toBe('COMPLETED');
      expect(result.run.id).toBe('run_test_123');
      expect(result.events.created).toBe(3);
      expect(result.summary).toContain('Test Workflow');
    });
  });
});

// ============================================================================
// Other Methods
// ============================================================================

describe('Other methods', () => {
  describe('listMeters', () => {
    it('sends GET to /pricing-plans and maps unitType to meter', async () => {
      const serverResponse = {
        data: [
          {
            id: 'pp_test_1',
            name: 'API Calls',
            unitType: 'api_calls',
            unitPriceUsd: '0.005',
            isActive: true,
          },
          {
            id: 'pp_test_2',
            name: 'Tokens',
            unitType: 'tokens',
            unitPriceUsd: '0.0001',
            isActive: true,
          },
        ],
        count: 2,
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(serverResponse));

      const result = await drip.listMeters();

      expect(getLastCallUrl()).toBe(`${BASE_URL}/pricing-plans`);
      expect(result.data).toHaveLength(2);
      expect(result.data[0].meter).toBe('api_calls');
      expect(result.data[1].meter).toBe('tokens');
      expect(result.data[0].unitPriceUsd).toBe('0.005');
      expect(result.count).toBe(2);
    });
  });

  describe('estimateFromUsage', () => {
    it('sends POST to /dashboard/cost-estimate/from-usage with Date -> ISO string', async () => {
      const estimateResponse = {
        lineItems: [{ usageType: 'api_calls', quantity: '100', unitPrice: '0.005', estimatedCostUsdc: '0.50', hasPricingPlan: true }],
        subtotalUsdc: '0.50',
        estimatedTotalUsdc: '0.50',
        currency: 'USDC',
        isEstimate: true,
        generatedAt: '2024-01-01T00:00:00.000Z',
        notes: [],
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(estimateResponse));

      const periodStart = new Date('2024-01-01');
      const periodEnd = new Date('2024-01-31');

      const result = await drip.estimateFromUsage({ periodStart, periodEnd });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/dashboard/cost-estimate/from-usage`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.periodStart).toBe(periodStart.toISOString());
      expect(body.periodEnd).toBe(periodEnd.toISOString());
      expect(result.estimatedTotalUsdc).toBe('0.50');
    });

    it('accepts string dates too', async () => {
      const estimateResponse = {
        lineItems: [],
        subtotalUsdc: '0.00',
        estimatedTotalUsdc: '0.00',
        currency: 'USDC',
        isEstimate: true,
        generatedAt: '2024-01-01T00:00:00.000Z',
        notes: [],
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(estimateResponse));

      await drip.estimateFromUsage({
        periodStart: '2024-01-01T00:00:00.000Z',
        periodEnd: '2024-01-31T00:00:00.000Z',
      });

      const body = getLastCallBody();
      expect(body.periodStart).toBe('2024-01-01T00:00:00.000Z');
      expect(body.periodEnd).toBe('2024-01-31T00:00:00.000Z');
    });
  });

  describe('estimateFromHypothetical', () => {
    it('sends POST to /dashboard/cost-estimate/hypothetical', async () => {
      const estimateResponse = {
        lineItems: [
          {
            usageType: 'api_calls',
            quantity: '10000',
            unitPrice: '0.005',
            estimatedCostUsdc: '50.00',
            hasPricingPlan: true,
          },
        ],
        subtotalUsdc: '50.00',
        estimatedTotalUsdc: '50.00',
        currency: 'USDC',
        isEstimate: true,
        generatedAt: '2024-01-01T00:00:00.000Z',
        notes: [],
      };
      mockFetch.mockResolvedValueOnce(mockJsonResponse(estimateResponse));

      const result = await drip.estimateFromHypothetical({
        items: [{ usageType: 'api_calls', quantity: 10000 }],
      });

      expect(getLastCallUrl()).toBe(`${BASE_URL}/dashboard/cost-estimate/hypothetical`);
      expect(getLastCallInit().method).toBe('POST');
      const body = getLastCallBody();
      expect(body.items).toEqual([{ usageType: 'api_calls', quantity: 10000 }]);
      expect(result.estimatedTotalUsdc).toBe('50.00');
    });
  });
});

// ============================================================================
// Static Methods
// ============================================================================

describe('Static methods', () => {
  describe('Drip.generateWebhookSignature', () => {
    it('returns format t=...,v1=...', () => {
      const payload = '{"type":"charge.succeeded"}';
      const secret = 'whsec_test_secret';
      const timestamp = 1704067200;

      const sig = Drip.generateWebhookSignature(payload, secret, timestamp);

      expect(sig).toMatch(/^t=\d+,v1=[a-f0-9]+$/);
      expect(sig).toContain(`t=${timestamp}`);
    });
  });

  describe('Drip.verifyWebhookSignature', () => {
    it('roundtrip: generate then verify succeeds', async () => {
      const payload = '{"type":"charge.succeeded","data":{"id":"chg_123"}}';
      const secret = 'whsec_test_secret';

      const sig = Drip.generateWebhookSignature(payload, secret);
      const isValid = await Drip.verifyWebhookSignature(payload, sig, secret);

      expect(isValid).toBe(true);
    });

    it('rejects tampered payload', async () => {
      const payload = '{"type":"charge.succeeded"}';
      const secret = 'whsec_test_secret';

      const sig = Drip.generateWebhookSignature(payload, secret);
      const isValid = await Drip.verifyWebhookSignature('{"type":"tampered"}', sig, secret);

      expect(isValid).toBe(false);
    });

    it('rejects wrong secret', async () => {
      const payload = '{"type":"charge.succeeded"}';
      const sig = Drip.generateWebhookSignature(payload, 'whsec_correct');
      const isValid = await Drip.verifyWebhookSignature(payload, sig, 'whsec_wrong');

      expect(isValid).toBe(false);
    });

    it('returns false for empty inputs', async () => {
      expect(await Drip.verifyWebhookSignature('', 'sig', 'secret')).toBe(false);
      expect(await Drip.verifyWebhookSignature('payload', '', 'secret')).toBe(false);
      expect(await Drip.verifyWebhookSignature('payload', 'sig', '')).toBe(false);
    });
  });

  describe('Drip.verifyWebhookSignatureSync', () => {
    it('roundtrip: generate then verify sync succeeds', () => {
      const payload = '{"type":"charge.succeeded","data":{}}';
      const secret = 'whsec_sync_secret';

      const sig = Drip.generateWebhookSignature(payload, secret);
      const isValid = Drip.verifyWebhookSignatureSync(payload, sig, secret);

      expect(isValid).toBe(true);
    });

    it('rejects tampered payload sync', () => {
      const payload = '{"type":"charge.succeeded"}';
      const secret = 'whsec_sync_secret';

      const sig = Drip.generateWebhookSignature(payload, secret);
      const isValid = Drip.verifyWebhookSignatureSync('{"tampered":true}', sig, secret);

      expect(isValid).toBe(false);
    });
  });

  describe('Drip.generateIdempotencyKey', () => {
    it('generates deterministic key from params', () => {
      const key1 = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'validate',
      });
      const key2 = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'validate',
      });

      expect(key1).toBe(key2);
      expect(key1).toMatch(/^drip_[a-f0-9]+_validate$/);
    });

    it('generates different keys for different params', () => {
      const key1 = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'step_a',
      });
      const key2 = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'step_b',
      });

      expect(key1).not.toBe(key2);
    });

    it('includes runId when provided', () => {
      const withRun = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        runId: 'run_456',
        stepName: 'validate',
      });
      const withoutRun = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'validate',
      });

      expect(withRun).not.toBe(withoutRun);
    });

    it('includes sequence when provided', () => {
      const seq0 = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'validate',
        sequence: 0,
      });
      const seq1 = Drip.generateIdempotencyKey({
        customerId: 'cust_123',
        stepName: 'validate',
        sequence: 1,
      });

      expect(seq0).not.toBe(seq1);
    });
  });
});

// ============================================================================
// Error Handling
// ============================================================================

describe('Error handling', () => {
  it('402 response throws DripError with statusCode 402', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse('Payment required', 402));

    try {
      await drip.charge({
        customerId: 'cust_test_123',
        meter: 'api_calls',
        quantity: 1,
      });
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(DripError);
      expect((err as DripError).statusCode).toBe(402);
      expect((err as DripError).message).toBe('Payment required');
    }
  });

  it('404 response throws DripError with statusCode 404', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse('Customer not found', 404));

    try {
      await drip.getCustomer('nonexistent');
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(DripError);
      expect((err as DripError).statusCode).toBe(404);
      expect((err as DripError).message).toBe('Customer not found');
    }
  });

  it('500 response throws DripError with statusCode 500', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse('Internal server error', 500));

    try {
      await drip.listCustomers();
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(DripError);
      expect((err as DripError).statusCode).toBe(500);
    }
  });

  it('error response includes error code when present', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse('Rate limit exceeded', 429, 'RATE_LIMIT'));

    try {
      await drip.charge({
        customerId: 'cust_test_123',
        meter: 'api_calls',
        quantity: 1,
      });
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(DripError);
      expect((err as DripError).code).toBe('RATE_LIMIT');
    }
  });

  it('DripError is instanceof Error', () => {
    const err = new DripError('test', 400, 'TEST_CODE');
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(DripError);
    expect(err.message).toBe('test');
    expect(err.statusCode).toBe(400);
    expect(err.code).toBe('TEST_CODE');
    expect(err.name).toBe('DripError');
  });
});

// ============================================================================
// Ping Method
// ============================================================================

describe('ping()', () => {
  it('strips /v1 from baseUrl and calls /health', async () => {
    const healthResponse = { status: 'healthy', timestamp: Date.now() };
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(healthResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await drip.ping();

    const calledUrl = getLastCallUrl();
    // baseUrl is https://mock.drip.test/v1, ping should strip /v1 and call /health
    expect(calledUrl).toBe('https://mock.drip.test/health');
    expect(calledUrl).not.toContain('/v1');
    expect(result.ok).toBe(true);
    expect(result.status).toBe('healthy');
    expect(typeof result.latencyMs).toBe('number');
    expect(typeof result.timestamp).toBe('number');
  });

  it('returns ok: false when API is unhealthy', async () => {
    const healthResponse = { status: 'degraded' };
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(healthResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await drip.ping();

    expect(result.ok).toBe(false);
    expect(result.status).toBe('degraded');
  });

  it('returns ok: false for non-200 status', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'unknown' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await drip.ping();

    expect(result.ok).toBe(false);
  });
});

// ============================================================================
// Authorization header
// ============================================================================

describe('Authorization header', () => {
  it('sends Bearer token in Authorization header', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockCustomer()));

    await drip.getCustomer('cust_test_123');

    const init = getLastCallInit();
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer sk_test_mock_key_123');
  });

  it('sends Content-Type application/json', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockCustomer()));

    await drip.getCustomer('cust_test_123');

    const init = getLastCallInit();
    const headers = init.headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
  });
});
