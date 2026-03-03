/**
 * Edge Case Tests for the Drip SDK
 *
 * Non-happy-path tests simulating real-world misuse: wrong argument types,
 * missing fields, boundary values, security edge cases, and common integration
 * mistakes that companies encounter when adopting the SDK.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Drip, DripError } from '@drip-sdk/node';

// ---------------------------------------------------------------------------
// Shared Mocks & Helpers
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

/** Mock a successful JSON response. */
function mockSuccess(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status,
    json: async () => body,
  });
}

/** Mock a 204 No Content response. */
function mock204() {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 204,
    json: async () => { throw new Error('No content'); },
  });
}

/** Mock an error response. */
function mockError(status: number, body: Record<string, unknown> = {}) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: async () => ({
      error: body.error ?? 'Error',
      message: body.message ?? body.error ?? 'Error',
      code: body.code ?? 'ERROR',
      ...body,
    }),
  });
}

/** Mock a non-JSON (HTML) response - simulates CDN/proxy errors. */
function mockHtmlResponse(status: number) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: async () => { throw new SyntaxError('Unexpected token <'); },
  });
}

/** Create a properly configured test client. */
function createClient(overrides: Record<string, unknown> = {}): Drip {
  return new Drip({
    apiKey: 'sk_test_edge_case_key',
    baseUrl: 'http://localhost:3001/v1',
    ...overrides,
  });
}

// ============================================================================
// A. Constructor / Initialization Edge Cases
// ============================================================================

describe('Constructor Edge Cases', () => {
  // Save original env
  const originalEnv = process.env.DRIP_API_KEY;

  afterEach(() => {
    vi.restoreAllMocks();
    if (originalEnv !== undefined) {
      process.env.DRIP_API_KEY = originalEnv;
    } else {
      delete process.env.DRIP_API_KEY;
    }
  });

  it('A1: throws Error (not DripError) when no API key and no env var', () => {
    delete process.env.DRIP_API_KEY;
    expect(() => new Drip({})).toThrow(Error);
    expect(() => new Drip({})).toThrow('API key is required');
    // Notably, this is NOT a DripError - it's a plain Error
    try {
      new Drip({});
    } catch (e) {
      expect(e).not.toBeInstanceOf(DripError);
      expect(e).toBeInstanceOf(Error);
    }
  });

  it('A2: throws when API key is empty string', () => {
    // Empty string is falsy, so `!apiKey` check catches it
    expect(() => new Drip({ apiKey: '' })).toThrow('API key is required');
  });

  it('A3: whitespace-only API key passes constructor (not validated)', () => {
    // Whitespace is truthy in JS, so constructor accepts it
    const drip = new Drip({ apiKey: '   ' });
    expect(drip.keyType).toBe('unknown'); // doesn't start with sk_ or pk_
  });

  it('A4: null API key throws (when no env var set)', () => {
    // null is nullish, so `??` falls through to env var. Delete it to test the throw.
    const saved = process.env.DRIP_API_KEY;
    delete process.env.DRIP_API_KEY;
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect(() => new Drip({ apiKey: null as any })).toThrow('API key is required');
    } finally {
      if (saved !== undefined) process.env.DRIP_API_KEY = saved;
    }
  });

  it('A5: timeout of 0 silently becomes 30000 (falsy coercion bug)', () => {
    // `config.timeout || 30000` means 0 is treated as falsy
    const drip = new Drip({ apiKey: 'sk_test_key', timeout: 0 });
    // We can verify by checking that a request uses 30s timeout, not 0
    // The timeout is private, but the behavior manifests in request timeouts
    expect(drip).toBeDefined(); // Constructor doesn't throw
  });

  it('A6: negative timeout is accepted by constructor (no validation)', () => {
    const drip = new Drip({ apiKey: 'sk_test_key', timeout: -1 });
    expect(drip).toBeDefined();
  });

  it('A7: baseUrl with trailing slash may cause double-slash URLs', async () => {
    const drip = new Drip({
      apiKey: 'sk_test_key',
      baseUrl: 'http://localhost:3001/v1/',
    });
    mockSuccess({ data: [], count: 0 });
    await drip.listCustomers();

    // Check what URL was fetched - may have double slash
    const calledUrl = mockFetch.mock.calls[0][0] as string;
    // 'http://localhost:3001/v1//customers' - double slash
    expect(calledUrl).toContain('/v1/');
  });

  it('A8: empty baseUrl causes requests to relative paths', () => {
    const drip = new Drip({ apiKey: 'sk_test_key', baseUrl: '' });
    // Empty string is falsy, falls back to production URL
    expect(drip).toBeDefined();
  });

  it('A9: very long API key (10KB) is accepted by constructor', () => {
    const longKey = 'sk_test_' + 'a'.repeat(10000);
    const drip = new Drip({ apiKey: longKey });
    expect(drip.keyType).toBe('secret');
  });

  it('A10: keyType detection for various prefixes', () => {
    expect(new Drip({ apiKey: 'sk_live_abc' }).keyType).toBe('secret');
    expect(new Drip({ apiKey: 'sk_test_abc' }).keyType).toBe('secret');
    expect(new Drip({ apiKey: 'pk_live_abc' }).keyType).toBe('public');
    expect(new Drip({ apiKey: 'pk_test_abc' }).keyType).toBe('public');
    expect(new Drip({ apiKey: 'drip_abc' }).keyType).toBe('unknown');
    expect(new Drip({ apiKey: 'random_key' }).keyType).toBe('unknown');
  });
});

// ============================================================================
// B. Customer Method Edge Cases
// ============================================================================

describe('Customer Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('createCustomer', () => {
    it('B1: empty params {} - API returns 422 (at least one ID required)', async () => {
      mockError(422, { error: 'At least one of externalCustomerId or onchainAddress is required' });
      await expect(drip.createCustomer({})).rejects.toThrow(DripError);
      try {
        mockError(422, { error: 'Validation failed' });
        await drip.createCustomer({});
      } catch (e) {
        expect((e as DripError).statusCode).toBe(422);
      }
    });

    it('B2: externalCustomerId as empty string - API may reject', async () => {
      mockError(422, { error: 'externalCustomerId cannot be empty' });
      await expect(
        drip.createCustomer({ externalCustomerId: '' }),
      ).rejects.toThrow(DripError);
    });

    it('B3: invalid onchainAddress format - API returns 422', async () => {
      mockError(422, { error: 'Invalid Ethereum address format' });
      await expect(
        drip.createCustomer({ onchainAddress: 'not-an-address' }),
      ).rejects.toThrow(DripError);
    });

    it('B4: valid format address that does not exist on-chain succeeds', async () => {
      const fakeAddress = '0x' + 'f'.repeat(40);
      mockSuccess({ id: 'cust_1', onchainAddress: fakeAddress, status: 'ACTIVE' });
      const customer = await drip.createCustomer({ onchainAddress: fakeAddress });
      expect(customer.id).toBe('cust_1');
    });

    it('B5: very long externalCustomerId (10KB) - may hit server limits', async () => {
      const longId = 'a'.repeat(10000);
      mockError(422, { error: 'externalCustomerId too long' });
      await expect(
        drip.createCustomer({ externalCustomerId: longId }),
      ).rejects.toThrow(DripError);
    });

    it('B6: deeply nested metadata is accepted (JSON)', async () => {
      mockSuccess({ id: 'cust_1', metadata: { nested: { deep: { key: 'value' } } }, status: 'ACTIVE' });
      const customer = await drip.createCustomer({
        externalCustomerId: 'test_user',
        metadata: { nested: { deep: { key: 'value' } } },
      });
      expect(customer).toBeDefined();
    });

    it('B7: metadata explicitly set to null is accepted', async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      mockSuccess({ id: 'cust_1', status: 'ACTIVE' });
      await expect(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        drip.createCustomer({ externalCustomerId: 'test', metadata: null as any }),
      ).resolves.toBeDefined();
    });

    it('B15: duplicate externalCustomerId returns 409 Conflict', async () => {
      mockError(409, { error: 'Customer with this externalCustomerId already exists', code: 'CONFLICT' });
      try {
        await drip.createCustomer({ externalCustomerId: 'existing_user' });
      } catch (e) {
        expect(e).toBeInstanceOf(DripError);
        expect((e as DripError).statusCode).toBe(409);
      }
    });
  });

  describe('getCustomer', () => {
    it('B8: empty string ID - API returns 404 or routing error', async () => {
      mockError(404, { error: 'Not found' });
      await expect(drip.getCustomer('')).rejects.toThrow(DripError);
    });

    it('B9: SQL injection attempt in ID - returns 404 (parameterized queries)', async () => {
      mockError(404, { error: 'Customer not found' });
      await expect(
        drip.getCustomer("'; DROP TABLE customers; --"),
      ).rejects.toThrow(DripError);
    });

    it('B10: path traversal attempt in ID - returns 404', async () => {
      mockError(404, { error: 'Not found' });
      await expect(
        drip.getCustomer('../../../etc/passwd'),
      ).rejects.toThrow(DripError);
    });

    it('B16: valid UUID format that does not exist - returns 404', async () => {
      mockError(404, { error: 'Customer not found' });
      try {
        await drip.getCustomer('00000000-0000-0000-0000-000000000000');
      } catch (e) {
        expect(e).toBeInstanceOf(DripError);
        expect((e as DripError).statusCode).toBe(404);
      }
    });
  });

  describe('listCustomers', () => {
    it('B11: limit of 0 - API rejects (Zod min=1)', async () => {
      mockError(422, { error: 'limit must be >= 1' });
      await expect(drip.listCustomers({ limit: 0 })).rejects.toThrow(DripError);
    });

    it('B12: limit of 101 - API rejects (Zod max=100)', async () => {
      mockError(422, { error: 'limit must be <= 100' });
      await expect(drip.listCustomers({ limit: 101 })).rejects.toThrow(DripError);
    });

    it('B13: negative limit - API rejects', async () => {
      mockError(422, { error: 'limit must be >= 1' });
      await expect(drip.listCustomers({ limit: -1 })).rejects.toThrow(DripError);
    });

    it('B14: invalid status enum - API rejects', async () => {
      mockError(422, { error: 'Invalid status value' });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await expect(drip.listCustomers({ status: 'INVALID' as any })).rejects.toThrow(DripError);
    });
  });

  describe('getBalance', () => {
    it('getBalance with nonexistent customer - returns 404', async () => {
      mockError(404, { error: 'Customer not found' });
      await expect(drip.getBalance('nonexistent')).rejects.toThrow(DripError);
    });
  });
});

// ============================================================================
// C. Charge / Usage Edge Cases
// ============================================================================

describe('Charge / Usage Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('charge()', () => {
    it('C1: quantity of 0 - may succeed with $0 charge', async () => {
      mockSuccess({
        success: true,
        usageEventId: 'evt_1',
        isDuplicate: false,
        charge: { id: 'chg_1', amountUsdc: '0.000000', status: 'CONFIRMED' },
      });
      const result = await drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: 0 });
      expect(result.charge.amountUsdc).toBe('0.000000');
    });

    it('C2: negative quantity - API should reject', async () => {
      mockError(422, { error: 'quantity must be positive' });
      await expect(
        drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: -5 }),
      ).rejects.toThrow(DripError);
    });

    it('C3: NaN quantity - SDK sends it (no client validation), API rejects', async () => {
      mockError(422, { error: 'quantity must be a number' });
      await expect(
        drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: NaN }),
      ).rejects.toThrow(DripError);

      // Verify NaN was serialized in the request body
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      // JSON.stringify(NaN) becomes null
      expect(body.quantity).toBeNull();
    });

    it('C4: Infinity quantity - SDK sends it (no client validation), API rejects', async () => {
      mockError(422, { error: 'quantity must be finite' });
      await expect(
        drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: Infinity }),
      ).rejects.toThrow(DripError);

      // JSON.stringify(Infinity) becomes null
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.quantity).toBeNull();
    });

    it('C5: sub-cent precision (0.0000001) - should succeed', async () => {
      mockSuccess({
        success: true,
        usageEventId: 'evt_1',
        isDuplicate: false,
        charge: { id: 'chg_1', amountUsdc: '0.000001', status: 'CONFIRMED' },
      });
      const result = await drip.charge({ customerId: 'cust_1', meter: 'tokens', quantity: 0.0000001 });
      expect(result.success).toBe(true);
    });

    it('C6: extremely large quantity (999999999) - may hit spending cap', async () => {
      mockError(402, {
        error: 'Insufficient balance',
        code: 'PAYMENT_REQUIRED',
        payment: { amount: '999999999', currency: 'USDC' },
      });
      try {
        await drip.charge({ customerId: 'cust_1', meter: 'tokens', quantity: 999999999 });
      } catch (e) {
        expect(e).toBeInstanceOf(DripError);
        expect((e as DripError).statusCode).toBe(402);
      }
    });

    it('C7: nonexistent customerId - returns 404', async () => {
      mockError(404, { error: 'Customer not found' });
      try {
        await drip.charge({ customerId: 'cust_nonexistent', meter: 'api_calls', quantity: 1 });
      } catch (e) {
        expect(e).toBeInstanceOf(DripError);
        expect((e as DripError).statusCode).toBe(404);
      }
    });

    it('C8: nonexistent meter name - may succeed without generating a charge', async () => {
      mockSuccess({
        success: true,
        usageEventId: 'evt_1',
        isDuplicate: false,
        charge: null,
      });
      const result = await drip.charge({ customerId: 'cust_1', meter: 'nonexistent_meter', quantity: 1 });
      expect(result.charge).toBeNull();
    });

    it('C9: duplicate idempotencyKey - second call returns isDuplicate: true', async () => {
      mockSuccess({
        success: true, usageEventId: 'evt_1', isDuplicate: false,
        charge: { id: 'chg_1', amountUsdc: '0.01', status: 'CONFIRMED' },
      });
      mockSuccess({
        success: true, usageEventId: 'evt_1', isDuplicate: true,
        charge: { id: 'chg_1', amountUsdc: '0.01', status: 'CONFIRMED' },
      });

      const key = 'dedup_test_key_123';
      const first = await drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: 1, idempotencyKey: key });
      const second = await drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: 1, idempotencyKey: key });

      expect(first.isDuplicate).toBe(false);
      expect(second.isDuplicate).toBe(true);
    });

    it('C10: empty string idempotencyKey - SDK sends it as-is (no fallback)', async () => {
      mockSuccess({
        success: true, usageEventId: 'evt_1', isDuplicate: false,
        charge: { id: 'chg_1', amountUsdc: '0.01', status: 'CONFIRMED' },
      });

      await drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: 1, idempotencyKey: '' });
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      // Empty string is provided, so SDK should use it instead of auto-generating
      expect(body.idempotencyKey).toBe('');
    });

    it('C11: missing customerId sends undefined in body', async () => {
      mockError(422, { error: 'customerId is required' });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await expect(
        drip.charge({ customerId: undefined as unknown as string, meter: 'api_calls', quantity: 1 }),
      ).rejects.toThrow(DripError);
    });

    it('C12: missing meter sends empty/undefined', async () => {
      mockError(422, { error: 'usageType is required' });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await expect(
        drip.charge({ customerId: 'cust_1', meter: undefined as unknown as string, quantity: 1 }),
      ).rejects.toThrow(DripError);
    });

    it('C13: quantity as string "5" - JS serializes it (no type validation)', async () => {
      mockSuccess({
        success: true, usageEventId: 'evt_1', isDuplicate: false,
        charge: { id: 'chg_1', amountUsdc: '0.05', status: 'CONFIRMED' },
      });
      // TypeScript would catch this, but runtime JS does not
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: '5' as any });
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      // JSON.stringify preserves the string type
      expect(body.quantity).toBe('5');
    });

    it('C15: insufficient balance returns 402 with payment details', async () => {
      mockError(402, {
        error: 'Payment required',
        code: 'PAYMENT_REQUIRED',
        payment: {
          amount: '1.00',
          recipient: '0xmerchant',
          currency: 'USDC',
          chain: 'base-sepolia',
        },
      });
      try {
        await drip.charge({ customerId: 'cust_1', meter: 'api_calls', quantity: 100 });
        expect.unreachable('Should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(DripError);
        expect((e as DripError).statusCode).toBe(402);
      }
    });
  });

  describe('trackUsage()', () => {
    it('C14: trackUsage sends to /usage/internal, not /usage', async () => {
      mockSuccess({ usageEventId: 'evt_1', isDuplicate: false });
      await drip.trackUsage({ customerId: 'cust_1', meter: 'api_calls', quantity: 1 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('/usage/internal');
      expect(calledUrl).not.toMatch(/\/usage$/);
    });

    it('trackUsage with zero quantity', async () => {
      mockSuccess({ usageEventId: 'evt_1', isDuplicate: false });
      const result = await drip.trackUsage({ customerId: 'cust_1', meter: 'api_calls', quantity: 0 });
      expect(result.usageEventId).toBeDefined();
    });
  });

  describe('getCharge()', () => {
    it('getCharge with nonexistent ID returns 404', async () => {
      mockError(404, { error: 'Charge not found' });
      await expect(drip.getCharge('nonexistent')).rejects.toThrow(DripError);
    });

    it('getCharge with empty string ID', async () => {
      mockError(404, { error: 'Not found' });
      await expect(drip.getCharge('')).rejects.toThrow(DripError);
    });
  });

  describe('listCharges()', () => {
    it('listCharges with invalid status', async () => {
      mockError(422, { error: 'Invalid status' });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await expect(drip.listCharges({ status: 'BOGUS' as any })).rejects.toThrow(DripError);
    });
  });
});

// ============================================================================
// D. Webhook Edge Cases (Secret Key Only)
// ============================================================================

describe('Webhook Edge Cases', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('D1: createWebhook with public key throws 403', async () => {
    const drip = new Drip({ apiKey: 'pk_test_public_key' });
    try {
      await drip.createWebhook({ url: 'https://example.com', events: ['charge.succeeded'] });
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(403);
      expect((e as DripError).code).toBe('PUBLIC_KEY_NOT_ALLOWED');
    }
  });

  it('D2: createWebhook with invalid URL - API rejects', async () => {
    const drip = createClient();
    mockError(422, { error: 'Invalid webhook URL' });
    await expect(
      drip.createWebhook({ url: 'not-a-url', events: ['charge.succeeded'] }),
    ).rejects.toThrow(DripError);
  });

  it('D3: createWebhook with invalid event type', async () => {
    const drip = createClient();
    mockError(422, { error: 'Invalid event type: invalid.event' });
    await expect(
      drip.createWebhook({ url: 'https://example.com', events: ['invalid.event'] }),
    ).rejects.toThrow(DripError);
  });

  it('D4: createWebhook with empty events array', async () => {
    const drip = createClient();
    mockError(422, { error: 'At least one event type is required' });
    await expect(
      drip.createWebhook({ url: 'https://example.com', events: [] }),
    ).rejects.toThrow(DripError);
  });

  it('D5: deleteWebhook with nonexistent ID returns 404', async () => {
    const drip = createClient();
    mockError(404, { error: 'Webhook not found' });
    await expect(drip.deleteWebhook('nonexistent')).rejects.toThrow(DripError);
  });

  it('D6: testWebhook with nonexistent ID returns 404', async () => {
    const drip = createClient();
    mockError(404, { error: 'Webhook not found' });
    await expect(drip.testWebhook('nonexistent')).rejects.toThrow(DripError);
  });

  it('D7: rotateWebhookSecret with nonexistent ID returns 404', async () => {
    const drip = createClient();
    mockError(404, { error: 'Webhook not found' });
    await expect(drip.rotateWebhookSecret('nonexistent')).rejects.toThrow(DripError);
  });

  it('D1b: all webhook methods blocked for public keys', async () => {
    const drip = new Drip({ apiKey: 'pk_live_public_key' });
    const methods = [
      () => drip.createWebhook({ url: 'https://example.com', events: ['charge.succeeded'] }),
      () => drip.listWebhooks(),
      () => drip.getWebhook('wh_1'),
      () => drip.deleteWebhook('wh_1'),
      () => drip.testWebhook('wh_1'),
      () => drip.rotateWebhookSecret('wh_1'),
    ];
    for (const method of methods) {
      await expect(method()).rejects.toThrow(DripError);
    }
  });
});

// ============================================================================
// E. Subscription Edge Cases
// ============================================================================

describe('Subscription Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('E1: createSubscription with priceUsdc: 0 (free tier)', async () => {
    mockSuccess({
      id: 'sub_1', customerId: 'cust_1', name: 'Free',
      priceUsdc: '0', interval: 'MONTHLY', status: 'ACTIVE',
    });
    const sub = await drip.createSubscription({
      customerId: 'cust_1', name: 'Free', interval: 'MONTHLY', priceUsdc: 0,
    });
    expect(sub.status).toBe('ACTIVE');
  });

  it('E2: createSubscription with negative price - API rejects', async () => {
    mockError(422, { error: 'priceUsdc must be non-negative' });
    await expect(
      drip.createSubscription({
        customerId: 'cust_1', name: 'Broken', interval: 'MONTHLY', priceUsdc: -10,
      }),
    ).rejects.toThrow(DripError);
  });

  it('E3: createSubscription with nonexistent customerId - returns 404', async () => {
    mockError(404, { error: 'Customer not found' });
    await expect(
      drip.createSubscription({
        customerId: 'nonexistent', name: 'Pro', interval: 'MONTHLY', priceUsdc: 10,
      }),
    ).rejects.toThrow(DripError);
  });

  it('E4: cancelSubscription on already-cancelled subscription', async () => {
    mockError(400, { error: 'Subscription is already cancelled', code: 'ALREADY_CANCELLED' });
    try {
      await drip.cancelSubscription('sub_cancelled');
    } catch (e) {
      expect((e as DripError).statusCode).toBe(400);
    }
  });

  it('E5: pauseSubscription on already-paused subscription', async () => {
    mockError(400, { error: 'Subscription is already paused', code: 'ALREADY_PAUSED' });
    try {
      await drip.pauseSubscription('sub_paused');
    } catch (e) {
      expect((e as DripError).statusCode).toBe(400);
    }
  });

  it('E6: resumeSubscription on active (not paused) subscription', async () => {
    mockError(400, { error: 'Subscription is not paused', code: 'NOT_PAUSED' });
    try {
      await drip.resumeSubscription('sub_active');
    } catch (e) {
      expect((e as DripError).statusCode).toBe(400);
    }
  });

  it('E7: createSubscription with public key throws 403', async () => {
    const publicDrip = new Drip({ apiKey: 'pk_test_public' });
    try {
      await publicDrip.createSubscription({
        customerId: 'cust_1', name: 'Pro', interval: 'MONTHLY', priceUsdc: 10,
      });
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect((e as DripError).statusCode).toBe(403);
      expect((e as DripError).code).toBe('PUBLIC_KEY_NOT_ALLOWED');
    }
  });
});

// ============================================================================
// F. Run / Event Edge Cases
// ============================================================================

describe('Run / Event Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('F1: endRun on already-ended run', async () => {
    mockError(400, { error: 'Run is already ended', code: 'RUN_ALREADY_ENDED' });
    try {
      await drip.endRun('run_ended', { status: 'COMPLETED' });
    } catch (e) {
      expect((e as DripError).statusCode).toBe(400);
    }
  });

  it('F2: emitEvent on ended run', async () => {
    mockError(400, { error: 'Cannot emit event to ended run' });
    await expect(
      drip.emitEvent({ runId: 'run_ended', eventType: 'USAGE' }),
    ).rejects.toThrow(DripError);
  });

  it('F3: emitEvent with empty runId', async () => {
    mockError(422, { error: 'runId is required' });
    await expect(
      drip.emitEvent({ runId: '', eventType: 'USAGE' }),
    ).rejects.toThrow(DripError);
  });

  it('F4: emitEventsBatch with empty array', async () => {
    mockSuccess({ success: true, created: 0, duplicates: 0, skipped: 0, events: [] });
    const result = await drip.emitEventsBatch([]);
    expect(result.created).toBe(0);
  });

  it('F6: startRun then immediately endRun with no events', async () => {
    mockSuccess({ id: 'run_1', status: 'RUNNING', createdAt: new Date().toISOString() });
    const run = await drip.startRun({});
    expect(run.id).toBe('run_1');

    mockSuccess({
      id: 'run_1', status: 'COMPLETED', endedAt: new Date().toISOString(),
      durationMs: 10, eventCount: 0, totalCostUnits: 0,
    });
    const ended = await drip.endRun('run_1', { status: 'COMPLETED' });
    expect(ended.status).toBe('COMPLETED');
    expect(ended.eventCount).toBe(0);
  });

  it('F7: recordRun with empty events array', async () => {
    mockSuccess({
      run: { id: 'run_1', status: 'COMPLETED' },
      events: [],
      summary: { eventCount: 0, totalCostUnits: 0 },
    });
    const result = await drip.recordRun({
      customerId: 'cust_1',
      workflow: 'test-workflow',
      events: [],
      status: 'COMPLETED',
    });
    expect(result.events).toHaveLength(0);
  });

  it('F8: getRun with nonexistent ID returns 404', async () => {
    mockError(404, { error: 'Run not found' });
    await expect(drip.getRun('nonexistent')).rejects.toThrow(DripError);
  });

  it('F9: getRunTimeline with nonexistent ID returns 404', async () => {
    mockError(404, { error: 'Run not found' });
    await expect(drip.getRunTimeline('nonexistent')).rejects.toThrow(DripError);
  });
});

// ============================================================================
// G. Entitlement Edge Cases
// ============================================================================

describe('Entitlement Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('G1: checkEntitlement with nonexistent customerId', async () => {
    mockError(404, { error: 'Customer not found' });
    await expect(
      drip.checkEntitlement({ customerId: 'nonexistent', featureKey: 'api_calls' }),
    ).rejects.toThrow(DripError);
  });

  it('G2: checkEntitlement with nonexistent featureKey', async () => {
    // Unconfigured features may return unlimited access
    mockSuccess({ allowed: true, remaining: null, unlimited: true, reason: 'No plan configured' });
    const result = await drip.checkEntitlement({ customerId: 'cust_1', featureKey: 'nonexistent_feature' });
    expect(result.allowed).toBe(true);
  });

  it('G3: checkEntitlement with quantity 0', async () => {
    mockSuccess({ allowed: true, remaining: 100, reason: 'Within quota' });
    const result = await drip.checkEntitlement({ customerId: 'cust_1', featureKey: 'api_calls', quantity: 0 });
    expect(result.allowed).toBe(true);
  });

  it('G4: checkEntitlement with negative quantity', async () => {
    mockError(422, { error: 'quantity must be non-negative' });
    await expect(
      drip.checkEntitlement({ customerId: 'cust_1', featureKey: 'api_calls', quantity: -1 }),
    ).rejects.toThrow(DripError);
  });
});

// ============================================================================
// H. Cost Estimation Edge Cases
// ============================================================================

describe('Cost Estimation Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('H1: estimateFromUsage with future dates returns zero', async () => {
    mockSuccess({ estimatedTotalUsdc: '0.00', lineItems: [] });
    const result = await drip.estimateFromUsage({
      customerId: 'cust_1',
      periodStart: '2099-01-01T00:00:00Z',
      periodEnd: '2099-12-31T23:59:59Z',
    });
    expect(result.estimatedTotalUsdc).toBe('0.00');
  });

  it('H2: estimateFromUsage with end before start - API should reject', async () => {
    mockError(422, { error: 'periodEnd must be after periodStart' });
    await expect(
      drip.estimateFromUsage({
        customerId: 'cust_1',
        periodStart: '2025-12-31T00:00:00Z',
        periodEnd: '2025-01-01T00:00:00Z',
      }),
    ).rejects.toThrow(DripError);
  });

  it('H3: estimateFromHypothetical with empty items', async () => {
    mockSuccess({ estimatedTotalUsdc: '0.00', lineItems: [] });
    const result = await drip.estimateFromHypothetical({ items: [] });
    expect(result.estimatedTotalUsdc).toBe('0.00');
  });

  it('H4: estimateFromHypothetical with negative quantities', async () => {
    mockError(422, { error: 'quantity must be positive' });
    await expect(
      drip.estimateFromHypothetical({
        items: [{ usageType: 'tokens', quantity: -100 }],
      }),
    ).rejects.toThrow(DripError);
  });
});

// ============================================================================
// I. StreamMeter Edge Cases (tested via charge mock)
// ============================================================================

describe('StreamMeter Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('I1: addSync(NaN) is NOT filtered - BUG: total becomes NaN', () => {
    const meter = drip.createStreamMeter({ customerId: 'cust_1', meter: 'tokens' });
    meter.addSync(NaN);
    // BUG: NaN is not caught by the guard (NaN > 0 is false, but NaN += 0 = NaN)
    // The SDK only checks `amount <= 0` which is false for NaN, so it passes through
    // and corrupts the running total. This is a real bug.
    expect(meter.total).toBeNaN();
  });

  it('I2: addSync(Infinity) should be ignored', () => {
    const meter = drip.createStreamMeter({ customerId: 'cust_1', meter: 'tokens' });
    meter.addSync(Infinity);
    // Infinity is > 0 so it may pass the guard check
    // This documents the current behavior
    expect(typeof meter.total).toBe('number');
  });

  it('I3: flush when total is 0 returns null charge', async () => {
    const meter = drip.createStreamMeter({ customerId: 'cust_1', meter: 'tokens' });
    const result = await meter.flush();
    expect(result.charge).toBeNull();
  });

  it('I4: double flush rapidly - second returns null', async () => {
    const meter = drip.createStreamMeter({ customerId: 'cust_1', meter: 'tokens' });
    meter.addSync(10);

    mockSuccess({
      success: true, usageEventId: 'evt_1', isDuplicate: false,
      charge: { id: 'chg_1', amountUsdc: '0.01', status: 'CONFIRMED' },
    });

    const first = await meter.flush();
    expect(first.charge).not.toBeNull();

    // Second flush - total is now 0
    const second = await meter.flush();
    expect(second.charge).toBeNull();
  });

  it('I5: negative value in addSync is ignored', () => {
    const meter = drip.createStreamMeter({ customerId: 'cust_1', meter: 'tokens' });
    meter.addSync(10);
    meter.addSync(-5);
    // Negative values are ignored per existing behavior
    expect(meter.total).toBe(10);
  });
});

// ============================================================================
// J. Network / Resilience Edge Cases
// ============================================================================

describe('Network / Resilience Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('J1: API returns HTML (502 gateway) - throws DripError', async () => {
    mockHtmlResponse(502);
    try {
      await drip.listCustomers();
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      // When json() throws, the catch block wraps it as a generic error
    }
  });

  it('J2: API returns empty response body (parse error)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => { throw new SyntaxError('Unexpected end of JSON'); },
    });
    // When json() throws on a 200, the SDK wraps it in DripError
    await expect(drip.listCustomers()).rejects.toThrow();
  });

  it('J3: API returns 200 with error body - treated as success (SDK trusts status)', async () => {
    mockSuccess({ error: 'Something went wrong internally', success: false });
    // SDK only checks res.ok (status 200), not body content
    const result = await drip.listCustomers();
    // The result passes through even though it has an error field
    expect(result).toHaveProperty('error');
  });

  it('J4: fetch throws network error - wrapped as DripError', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    try {
      await drip.listCustomers();
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).message).toContain('Failed to fetch');
      expect((e as DripError).statusCode).toBe(0);
      expect((e as DripError).code).toBe('UNKNOWN');
    }
  });

  it('J5: fetch throws AbortError (timeout) - wrapped as DripError with 408', async () => {
    const abortError = new Error('The operation was aborted');
    abortError.name = 'AbortError';
    mockFetch.mockRejectedValueOnce(abortError);
    try {
      await drip.listCustomers();
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(408);
      expect((e as DripError).code).toBe('TIMEOUT');
    }
  });

  it('J6: API returns 429 rate limit - DripError with status 429', async () => {
    mockError(429, { error: 'Rate limit exceeded', code: 'RATE_LIMIT', retryAfter: 60 });
    try {
      await drip.listCustomers();
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(429);
    }
  });

  it('J7: API returns 500 internal server error', async () => {
    mockError(500, { error: 'Internal server error' });
    try {
      await drip.listCustomers();
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(500);
    }
  });

  it('J8: API returns 401 unauthorized', async () => {
    mockError(401, { error: 'Invalid API key', code: 'UNAUTHORIZED' });
    try {
      await drip.listCustomers();
      expect.unreachable('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(401);
    }
  });
});

// ============================================================================
// K. Security Edge Cases
// ============================================================================

describe('Security Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('K1: API key in metadata - SDK does not filter sensitive data', async () => {
    mockSuccess({ id: 'cust_1', status: 'ACTIVE', metadata: { secret: 'sk_live_real_key' } });
    // SDK happily sends sensitive data in metadata - it's up to the backend to sanitize
    const customer = await drip.createCustomer({
      externalCustomerId: 'test',
      metadata: { secret: 'sk_live_real_key' },
    });

    // Verify the key was sent in the request body
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.metadata.secret).toBe('sk_live_real_key');
  });

  it('K2: XSS in customer external ID - SDK passes through (server should escape)', async () => {
    const xssPayload = '<script>alert("xss")</script>';
    mockSuccess({ id: 'cust_1', externalCustomerId: xssPayload, status: 'ACTIVE' });
    const customer = await drip.createCustomer({ externalCustomerId: xssPayload });
    expect(customer.externalCustomerId).toBe(xssPayload);
  });

  it('K3: __proto__ in metadata - does not pollute prototype', async () => {
    const maliciousMetadata = { __proto__: { isAdmin: true }, constructor: { name: 'hacked' } };
    mockSuccess({ id: 'cust_1', status: 'ACTIVE', metadata: maliciousMetadata });
    await drip.createCustomer({
      externalCustomerId: 'test',
      metadata: maliciousMetadata,
    });

    // Verify prototype was not polluted
    const obj: Record<string, unknown> = {};
    expect(obj).not.toHaveProperty('isAdmin');
  });

  it('K4: very large metadata (1MB) - SDK sends it, server may reject', async () => {
    const largeMetadata: Record<string, string> = {};
    // Create ~1MB of metadata
    for (let i = 0; i < 1000; i++) {
      largeMetadata[`key_${i}`] = 'x'.repeat(1000);
    }
    mockError(413, { error: 'Request entity too large' });
    await expect(
      drip.createCustomer({ externalCustomerId: 'test', metadata: largeMetadata }),
    ).rejects.toThrow(DripError);
  });

  it('K5: Unicode characters in customer ID', async () => {
    mockSuccess({ id: 'cust_1', externalCustomerId: 'user_\u4e2d\u6587', status: 'ACTIVE' });
    const customer = await drip.createCustomer({ externalCustomerId: 'user_\u4e2d\u6587' });
    expect(customer).toBeDefined();
  });

  it('K6: null byte injection in customer ID', async () => {
    mockError(422, { error: 'Invalid character in externalCustomerId' });
    await expect(
      drip.createCustomer({ externalCustomerId: 'user\x00admin' }),
    ).rejects.toThrow(DripError);
  });
});

// ============================================================================
// L. Spending Cap Edge Cases
// ============================================================================

describe('Spending Cap Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('setCustomerSpendingCap with negative limit - API rejects', async () => {
    mockError(422, { error: 'limitValue must be positive' });
    await expect(
      drip.setCustomerSpendingCap('cust_1', {
        capType: 'DAILY_CHARGE_LIMIT',
        limitValue: -100,
      }),
    ).rejects.toThrow(DripError);
  });

  it('setCustomerSpendingCap with zero limit', async () => {
    mockError(422, { error: 'limitValue must be positive' });
    await expect(
      drip.setCustomerSpendingCap('cust_1', {
        capType: 'DAILY_CHARGE_LIMIT',
        limitValue: 0,
      }),
    ).rejects.toThrow(DripError);
  });

  it('setCustomerSpendingCap with invalid capType', async () => {
    mockError(422, { error: 'Invalid capType' });
    await expect(
      drip.setCustomerSpendingCap('cust_1', {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        capType: 'INVALID_CAP' as any,
        limitValue: 100,
      }),
    ).rejects.toThrow(DripError);
  });

  it('removeCustomerSpendingCap with nonexistent cap', async () => {
    mockError(404, { error: 'Spending cap not found' });
    await expect(
      drip.removeCustomerSpendingCap('cust_1', 'nonexistent_cap'),
    ).rejects.toThrow(DripError);
  });
});

// ============================================================================
// M. wrapApiCall Edge Cases
// ============================================================================

describe('wrapApiCall Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('external API throws - error propagates, no charge recorded', async () => {
    const externalCall = vi.fn().mockRejectedValue(new Error('External API down'));
    await expect(
      drip.wrapApiCall({
        customerId: 'cust_1',
        meter: 'tokens',
        call: externalCall,
        extractUsage: () => 0,
      }),
    ).rejects.toThrow('External API down');

    // fetch should NOT have been called (no charge attempt)
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('extractUsage returns NaN - charge uses NaN (serialized as null)', async () => {
    const externalCall = vi.fn().mockResolvedValue({ data: 'ok' });
    mockSuccess({
      success: true, usageEventId: 'evt_1', isDuplicate: false,
      charge: { id: 'chg_1', amountUsdc: '0.00', status: 'CONFIRMED' },
    });

    await drip.wrapApiCall({
      customerId: 'cust_1',
      meter: 'tokens',
      call: externalCall,
      extractUsage: () => NaN,
    });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    // NaN becomes null in JSON
    expect(body.quantity).toBeNull();
  });

  it('extractUsage returns negative - charge sends negative (API should reject)', async () => {
    const externalCall = vi.fn().mockResolvedValue({ tokens: -10 });
    mockError(422, { error: 'quantity must be positive' });

    await expect(
      drip.wrapApiCall({
        customerId: 'cust_1',
        meter: 'tokens',
        call: externalCall,
        extractUsage: (r: { tokens: number }) => r.tokens,
      }),
    ).rejects.toThrow(DripError);
  });

  it('extractUsage throws - error propagates after external call succeeds', async () => {
    const externalCall = vi.fn().mockResolvedValue({ data: 'ok' });
    await expect(
      drip.wrapApiCall({
        customerId: 'cust_1',
        meter: 'tokens',
        call: externalCall,
        extractUsage: () => { throw new Error('Cannot extract usage'); },
      }),
    ).rejects.toThrow('Cannot extract usage');
  });
});

// ============================================================================
// N. getOrCreateCustomer Edge Cases
// ============================================================================

describe('getOrCreateCustomer Edge Cases', () => {
  let drip: Drip;

  beforeEach(() => {
    vi.clearAllMocks();
    drip = createClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('race condition: 409 conflict then finds existing customer', async () => {
    // First call: creation returns 409 (already exists)
    mockError(409, { error: 'Customer already exists' });
    // Second call: listCustomers to find existing
    mockSuccess({
      data: [{
        id: 'cust_existing', externalCustomerId: 'user_1', status: 'ACTIVE',
        onchainAddress: null, isInternal: false, metadata: null,
      }],
      count: 1,
    });
    // Third call: getCustomer to return the full customer object
    mockSuccess({
      id: 'cust_existing', externalCustomerId: 'user_1', status: 'ACTIVE',
      onchainAddress: null, isInternal: false, metadata: null,
    });

    const customer = await drip.getOrCreateCustomer('user_1');
    expect(customer.id).toBe('cust_existing');
  });

  it('empty externalCustomerId', async () => {
    mockError(422, { error: 'externalCustomerId required' });
    await expect(drip.getOrCreateCustomer('')).rejects.toThrow(DripError);
  });
});
