/**
 * Smoke Tests: Drip constructor configuration, env var fallback, key detection.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Drip, DripError } from '@drip-sdk/node';

describe('Drip constructor', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.DRIP_API_KEY;
    delete process.env.DRIP_BASE_URL;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('accepts explicit apiKey', () => {
    const drip = new Drip({ apiKey: 'sk_test_explicit' });
    expect(drip).toBeInstanceOf(Drip);
  });

  it('falls back to DRIP_API_KEY env var', () => {
    process.env.DRIP_API_KEY = 'sk_test_from_env';
    const drip = new Drip();
    expect(drip).toBeInstanceOf(Drip);
  });

  it('throws descriptive error when no apiKey and no env var', () => {
    expect(() => new Drip()).toThrow('Drip API key is required');
  });

  it('accepts explicit baseUrl', () => {
    const drip = new Drip({ apiKey: 'sk_test_x', baseUrl: 'https://custom.api.com/v1' });
    expect(drip).toBeInstanceOf(Drip);
  });

  it('accepts custom timeout', () => {
    const drip = new Drip({ apiKey: 'sk_test_x', timeout: 5000 });
    expect(drip).toBeInstanceOf(Drip);
  });

  it('detects secret key type from sk_ prefix', () => {
    const drip = new Drip({ apiKey: 'sk_test_abc' });
    expect(drip.keyType).toBe('secret');
  });

  it('detects secret key type from sk_live_ prefix', () => {
    const drip = new Drip({ apiKey: 'sk_live_abc' });
    expect(drip.keyType).toBe('secret');
  });

  it('detects public key type from pk_ prefix', () => {
    const drip = new Drip({ apiKey: 'pk_test_abc' });
    expect(drip.keyType).toBe('public');
  });

  it('reports unknown key type for non-standard prefix', () => {
    const drip = new Drip({ apiKey: 'legacy_key_xyz' });
    expect(drip.keyType).toBe('unknown');
  });
});

describe('Drip constructor with resilience', () => {
  it('creates instance with resilience: true', () => {
    const drip = new Drip({ apiKey: 'sk_test_x', resilience: true });
    expect(drip).toBeInstanceOf(Drip);
  });

  it('creates instance with resilience: "high-throughput"', () => {
    const drip = new Drip({ apiKey: 'sk_test_x', resilience: 'high-throughput' });
    expect(drip).toBeInstanceOf(Drip);
  });

  it('creates instance with custom resilience config', () => {
    const drip = new Drip({
      apiKey: 'sk_test_x',
      resilience: {
        rateLimiter: { requestsPerSecond: 50, burstSize: 100, enabled: true },
      },
    });
    expect(drip).toBeInstanceOf(Drip);
  });

  it('creates instance without resilience by default', () => {
    const drip = new Drip({ apiKey: 'sk_test_x' });
    expect(drip.getMetrics()).toBeNull();
    expect(drip.getHealth()).toBeNull();
  });

  it('getMetrics returns object when resilience enabled', () => {
    const drip = new Drip({ apiKey: 'sk_test_x', resilience: true });
    const metrics = drip.getMetrics();
    expect(metrics).not.toBeNull();
    expect(typeof metrics).toBe('object');
  });

  it('getHealth returns object when resilience enabled', () => {
    const drip = new Drip({ apiKey: 'sk_test_x', resilience: true });
    const health = drip.getHealth();
    expect(health).not.toBeNull();
    expect(typeof health).toBe('object');
  });
});
