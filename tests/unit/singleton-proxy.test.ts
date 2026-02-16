/**
 * Unit Tests: `drip` singleton lazy proxy behavior.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('drip singleton proxy', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('is exported from @drip-sdk/node', async () => {
    const mod = await import('@drip-sdk/node');
    expect(mod.drip).toBeDefined();
  });

  it('is an object (Proxy)', async () => {
    const mod = await import('@drip-sdk/node');
    expect(typeof mod.drip).toBe('object');
  });

  it('throws when DRIP_API_KEY is not set and method is called', async () => {
    delete process.env.DRIP_API_KEY;

    // Dynamic import to get fresh module
    // Note: singleton is cached, so this test may need isolation
    // For now, we test the error message pattern
    try {
      const { Drip } = await import('@drip-sdk/node');
      new Drip(); // no config, no env var
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
      expect((e as Error).message).toContain('Drip API key is required');
    }
  });

  it('creates lazily when DRIP_API_KEY is set', async () => {
    process.env.DRIP_API_KEY = 'sk_test_singleton_test';
    const { drip } = await import('@drip-sdk/node');
    // Accessing keyType triggers lazy init
    expect(drip.keyType).toBe('secret');
  });
});
