/**
 * x402 Payment Protocol Contract Tests
 *
 * Verifies the middleware exports that power the x402 payment flow:
 * - generatePaymentRequest() produces correct 402 response headers
 * - parsePaymentProof() validates and extracts proof from request headers
 * - hasPaymentProof() detects presence/absence of proof headers
 *
 * These tests ensure the SDK middleware and backend stay in sync on
 * the exact header names, formats, and validation rules.
 */
import { describe, it, expect } from 'vitest';
import {
  generatePaymentRequest,
  parsePaymentProof,
  hasPaymentProof,
  getHeader,
} from '@drip-sdk/node/middleware';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RECIPIENT = '0x' + 'ab'.repeat(20); // 42-char address

/** All 8 required x402 proof headers. */
const REQUIRED_PROOF_HEADERS = [
  'x-payment-signature',
  'x-payment-session-key',
  'x-payment-smart-account',
  'x-payment-timestamp',
  'x-payment-amount',
  'x-payment-recipient',
  'x-payment-usage-id',
  'x-payment-nonce',
] as const;

/** Build a complete, valid set of x402 proof headers. */
function validProofHeaders(overrides: Record<string, string> = {}): Record<string, string> {
  const timestamp = String(Math.floor(Date.now() / 1000));
  return {
    'x-payment-signature': '0x' + 'ab'.repeat(65),    // 130 hex chars (65 bytes)
    'x-payment-session-key': '0x' + 'cd'.repeat(32),  // 64 hex chars (32 bytes)
    'x-payment-smart-account': '0x' + 'ef'.repeat(20), // 40 hex chars (20 bytes)
    'x-payment-timestamp': timestamp,
    'x-payment-amount': '0.01',
    'x-payment-recipient': '0x' + 'aa'.repeat(20),
    'x-payment-usage-id': '0x' + 'bb'.repeat(16),
    'x-payment-nonce': `${timestamp}-${('ff').repeat(16)}`,
    ...overrides,
  };
}

// ===========================================================================
// generatePaymentRequest
// ===========================================================================

describe('generatePaymentRequest()', () => {
  it('produces all required X-Payment-* headers', () => {
    const { headers } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-usage-123',
      description: 'api_calls usage charge',
    });

    expect(headers['X-Payment-Required']).toBeDefined();
    expect(headers['X-Payment-Amount']).toBeDefined();
    expect(headers['X-Payment-Recipient']).toBeDefined();
    expect(headers['X-Payment-Usage-Id']).toBeDefined();
    expect(headers['X-Payment-Description']).toBeDefined();
    expect(headers['X-Payment-Expires']).toBeDefined();
    expect(headers['X-Payment-Nonce']).toBeDefined();
    expect(headers['X-Payment-Timestamp']).toBeDefined();
  });

  it('X-Payment-Required is the literal string "true"', () => {
    const { headers } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-usage-123',
    });

    expect(headers['X-Payment-Required']).toBe('true');
  });

  it('X-Payment-Expires is a future timestamp', () => {
    const before = Math.floor(Date.now() / 1000);

    const { headers } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-usage-123',
    });

    const expires = Number(headers['X-Payment-Expires']);
    expect(expires).toBeGreaterThan(before);
  });

  it('X-Payment-Nonce is unique per call', () => {
    const { headers: h1 } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-1',
    });
    const { headers: h2 } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-2',
    });

    expect(h1['X-Payment-Nonce']).not.toBe(h2['X-Payment-Nonce']);
  });

  it('preserves the amount and recipient values', () => {
    const { headers } = generatePaymentRequest({
      amount: '1.50',
      recipient: RECIPIENT,
      usageId: 'test-usage-456',
      description: 'My charge',
    });

    expect(headers['X-Payment-Amount']).toBe('1.50');
    expect(headers['X-Payment-Recipient']).toBe(RECIPIENT);
    expect(headers['X-Payment-Description']).toBe('My charge');
  });

  it('returns a paymentRequest object matching the headers', () => {
    const { headers, paymentRequest } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-usage-789',
      description: 'Test charge',
    });

    expect(paymentRequest.amount).toBe(headers['X-Payment-Amount']);
    expect(paymentRequest.recipient).toBe(headers['X-Payment-Recipient']);
    expect(paymentRequest.description).toBe(headers['X-Payment-Description']);
    expect(String(paymentRequest.expiresAt)).toBe(headers['X-Payment-Expires']);
    expect(paymentRequest.nonce).toBe(headers['X-Payment-Nonce']);
    expect(String(paymentRequest.timestamp)).toBe(headers['X-Payment-Timestamp']);
  });

  it('defaults description to "API usage charge" when not provided', () => {
    const { headers } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'test-usage-default',
    });

    expect(headers['X-Payment-Description']).toBe('API usage charge');
  });

  it('converts non-hex usageId to a hex hash', () => {
    const { headers } = generatePaymentRequest({
      amount: '0.01',
      recipient: RECIPIENT,
      usageId: 'plain-text-id',
    });

    // Non-hex usageId gets hashed to 0x... format
    expect(headers['X-Payment-Usage-Id']).toMatch(/^0x[a-f0-9]+$/);
  });
});

// ===========================================================================
// parsePaymentProof
// ===========================================================================

describe('parsePaymentProof()', () => {
  it('returns complete proof when all headers are valid', () => {
    const headers = validProofHeaders();
    const proof = parsePaymentProof(headers);

    expect(proof).not.toBeNull();
    expect(proof!.signature).toBe(headers['x-payment-signature']);
    expect(proof!.sessionKeyId).toBe(headers['x-payment-session-key']);
    expect(proof!.smartAccount).toBe(headers['x-payment-smart-account']);
    expect(proof!.timestamp).toBe(Number(headers['x-payment-timestamp']));
    expect(proof!.amount).toBe(headers['x-payment-amount']);
    expect(proof!.recipient).toBe(headers['x-payment-recipient']);
    expect(proof!.usageId).toBe(headers['x-payment-usage-id']);
    expect(proof!.nonce).toBe(headers['x-payment-nonce']);
  });

  it('returns null when signature header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-signature'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when session key header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-session-key'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when smart account header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-smart-account'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when timestamp header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-timestamp'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when amount header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-amount'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when recipient header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-recipient'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when usage-id header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-usage-id'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null when nonce header is missing', () => {
    const headers = validProofHeaders();
    delete headers['x-payment-nonce'];
    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null for expired timestamp (>5 min old)', () => {
    const sixMinutesAgo = Math.floor(Date.now() / 1000) - 360;
    const headers = validProofHeaders({
      'x-payment-timestamp': String(sixMinutesAgo),
    });

    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null for invalid hex signature (no 0x prefix)', () => {
    const headers = validProofHeaders({
      'x-payment-signature': 'ab'.repeat(65), // Missing 0x prefix
    });

    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null for signature that is too short', () => {
    const headers = validProofHeaders({
      'x-payment-signature': '0x' + 'ab'.repeat(10), // Only 20 hex chars, need 130
    });

    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null for invalid hex session key', () => {
    const headers = validProofHeaders({
      'x-payment-session-key': 'not-hex-at-all',
    });

    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('returns null for invalid hex smart account', () => {
    const headers = validProofHeaders({
      'x-payment-smart-account': 'invalid',
    });

    expect(parsePaymentProof(headers)).toBeNull();
  });

  it('accepts valid proof with a recent (non-expired) timestamp', () => {
    const justNow = Math.floor(Date.now() / 1000) - 10; // 10 seconds ago
    const headers = validProofHeaders({
      'x-payment-timestamp': String(justNow),
    });

    const proof = parsePaymentProof(headers);
    expect(proof).not.toBeNull();
    expect(proof!.timestamp).toBe(justNow);
  });
});

// ===========================================================================
// hasPaymentProof
// ===========================================================================

describe('hasPaymentProof()', () => {
  it('returns false with no headers (empty object)', () => {
    expect(hasPaymentProof({})).toBe(false);
  });

  it('returns false with partial headers (only signature)', () => {
    expect(
      hasPaymentProof({
        'x-payment-signature': '0x' + 'ab'.repeat(65),
      }),
    ).toBe(false);
  });

  it('returns false with partial headers (missing one required header)', () => {
    for (const headerToRemove of REQUIRED_PROOF_HEADERS) {
      const headers = validProofHeaders();
      delete headers[headerToRemove];
      expect(hasPaymentProof(headers)).toBe(false);
    }
  });

  it('returns true with all 8 required headers present', () => {
    const headers = validProofHeaders();
    expect(hasPaymentProof(headers)).toBe(true);
  });

  it('returns true regardless of header value validity (only checks presence)', () => {
    // hasPaymentProof only checks if headers exist, not their content
    const headers: Record<string, string> = {};
    for (const h of REQUIRED_PROOF_HEADERS) {
      headers[h] = 'any-value';
    }
    expect(hasPaymentProof(headers)).toBe(true);
  });
});

// ===========================================================================
// getHeader
// ===========================================================================

describe('getHeader()', () => {
  it('retrieves a header value (case-insensitive)', () => {
    const headers = { 'X-Payment-Amount': '0.01' };
    expect(getHeader(headers, 'x-payment-amount')).toBe('0.01');
    expect(getHeader(headers, 'X-Payment-Amount')).toBe('0.01');
  });

  it('returns undefined for missing headers', () => {
    const headers = { 'x-payment-amount': '0.01' };
    expect(getHeader(headers, 'x-payment-signature')).toBeUndefined();
  });

  it('handles array header values (returns first element)', () => {
    const headers: Record<string, string | string[]> = {
      'x-payment-amount': ['0.01', '0.02'],
    };
    expect(getHeader(headers, 'x-payment-amount')).toBe('0.01');
  });
});

// ===========================================================================
// Full round-trip: generate then parse
// ===========================================================================

describe('Round-trip: generate request -> create proof -> parse proof', () => {
  it('generated payment request headers can be used to construct a parseable proof', () => {
    // Step 1: Server generates payment request headers (402 response)
    const { headers: paymentHeaders, paymentRequest } = generatePaymentRequest({
      amount: '0.05',
      recipient: RECIPIENT,
      usageId: 'round-trip-test',
      description: 'Round trip test charge',
    });

    // Step 2: Client constructs proof headers (retry request)
    const timestamp = String(Math.floor(Date.now() / 1000));
    const proofHeaders: Record<string, string> = {
      'x-payment-signature': '0x' + 'ab'.repeat(65),
      'x-payment-session-key': '0x' + 'cd'.repeat(32),
      'x-payment-smart-account': '0x' + 'ef'.repeat(20),
      'x-payment-timestamp': timestamp,
      'x-payment-amount': paymentRequest.amount,
      'x-payment-recipient': paymentRequest.recipient,
      'x-payment-usage-id': paymentRequest.usageId,
      'x-payment-nonce': paymentRequest.nonce,
    };

    // Step 3: Server parses proof from retry request
    expect(hasPaymentProof(proofHeaders)).toBe(true);

    const proof = parsePaymentProof(proofHeaders);
    expect(proof).not.toBeNull();
    expect(proof!.amount).toBe('0.05');
    expect(proof!.recipient).toBe(RECIPIENT);
    expect(proof!.usageId).toBe(paymentRequest.usageId);
  });
});
