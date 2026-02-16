/**
 * Unit Tests: DripError construction, status code mapping, instanceof checks.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Drip, DripError } from '@drip-sdk/node';
import {
  installMockFetch,
  mockJsonResponse,
  mockErrorResponse,
  createTestDrip,
  BASE_URL,
} from '../helpers/mock-fetch.js';

describe('DripError', () => {
  it('is instanceof Error', () => {
    const err = new DripError('test', 400);
    expect(err).toBeInstanceOf(Error);
  });

  it('is instanceof DripError', () => {
    const err = new DripError('test', 400);
    expect(err).toBeInstanceOf(DripError);
  });

  it('has name "DripError"', () => {
    const err = new DripError('test', 400);
    expect(err.name).toBe('DripError');
  });

  it('has statusCode property', () => {
    const err = new DripError('test', 422);
    expect(err.statusCode).toBe(422);
  });

  it('has optional code property', () => {
    const err = new DripError('test', 400, 'VALIDATION_ERROR');
    expect(err.code).toBe('VALIDATION_ERROR');
  });

  it('code is undefined when not provided', () => {
    const err = new DripError('test', 400);
    expect(err.code).toBeUndefined();
  });

  it('message is human-readable', () => {
    const err = new DripError('Customer not found', 404);
    expect(err.message).toBe('Customer not found');
  });
});

describe('Error propagation from mocked API', () => {
  let mockFetch: ReturnType<typeof installMockFetch>;
  let drip: Drip;

  beforeEach(() => {
    mockFetch = installMockFetch();
    drip = createTestDrip();
  });

  afterEach(() => {
    globalThis.fetch = undefined as unknown as typeof globalThis.fetch;
  });

  it('400 response creates DripError with statusCode 400', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Bad request', 400, 'BAD_REQUEST'),
    );
    await expect(drip.getCustomer('bad')).rejects.toThrow(DripError);
    try {
      await drip.getCustomer('bad');
    } catch (e) {
      // Already rejected above, re-setup
    }
    // Re-setup and test again
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Bad request', 400, 'BAD_REQUEST'),
    );
    try {
      await drip.getCustomer('bad');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(400);
      expect((e as DripError).code).toBe('BAD_REQUEST');
    }
  });

  it('401 response creates DripError with statusCode 401', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Unauthorized', 401, 'UNAUTHORIZED'),
    );
    try {
      await drip.getCustomer('x');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(401);
    }
  });

  it('402 response creates DripError with statusCode 402', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Payment required', 402, 'PAYMENT_REQUIRED'),
    );
    try {
      await drip.charge({ customerId: 'c', meter: 'm', quantity: 1 });
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(402);
    }
  });

  it('404 response creates DripError with statusCode 404', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Not found', 404, 'NOT_FOUND'),
    );
    try {
      await drip.getCustomer('nonexistent');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(404);
    }
  });

  it('422 response creates DripError with statusCode 422', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Validation failed', 422, 'VALIDATION_ERROR'),
    );
    try {
      await drip.createCustomer({});
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(422);
    }
  });

  it('429 response creates DripError with statusCode 429', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Rate limited', 429, 'RATE_LIMITED'),
    );
    try {
      await drip.getCustomer('x');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(429);
    }
  });

  it('500 response creates DripError with statusCode 500', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Internal error', 500, 'INTERNAL_ERROR'),
    );
    try {
      await drip.getCustomer('x');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(500);
    }
  });

  it('timeout creates DripError with statusCode 408 and code TIMEOUT', async () => {
    mockFetch.mockImplementationOnce(() => {
      const error = new Error('AbortError');
      error.name = 'AbortError';
      return Promise.reject(error);
    });
    const fastDrip = new Drip({ apiKey: 'sk_test_x', baseUrl: BASE_URL, timeout: 1 });
    try {
      await fastDrip.getCustomer('x');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(408);
      expect((e as DripError).code).toBe('TIMEOUT');
    }
  });

  it('network error creates DripError with statusCode 0', async () => {
    mockFetch.mockRejectedValueOnce(new Error('fetch failed'));
    try {
      await drip.getCustomer('x');
    } catch (e) {
      expect(e).toBeInstanceOf(DripError);
      expect((e as DripError).statusCode).toBe(0);
      expect((e as DripError).code).toBe('UNKNOWN');
    }
  });

  it('error includes code from response body', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Custom error', 400, 'CUSTOM_CODE'),
    );
    try {
      await drip.getCustomer('x');
    } catch (e) {
      expect((e as DripError).code).toBe('CUSTOM_CODE');
    }
  });

  it('error includes message from response body', async () => {
    mockFetch.mockResolvedValueOnce(
      mockErrorResponse('Specific error message', 400),
    );
    try {
      await drip.getCustomer('x');
    } catch (e) {
      expect((e as DripError).message).toBe('Specific error message');
    }
  });
});
