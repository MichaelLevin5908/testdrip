/**
 * Module Tests: ESM dynamic import for all 6 entry points.
 * This file MUST have .mjs extension to force ESM resolution path.
 * Validates the package.json exports "import" condition.
 */
import { describe, it, expect } from 'vitest';

describe('ESM imports', () => {
  it('imports main entry point', async () => {
    const mod = await import('@drip-sdk/node');
    expect(typeof mod.Drip).toBe('function');
    expect(typeof mod.DripError).toBe('function');
    expect(typeof mod.StreamMeter).toBe('function');
    expect(typeof mod.default).toBe('function');
  });

  it('imports core entry point', async () => {
    const mod = await import('@drip-sdk/node/core');
    expect(typeof mod.Drip).toBe('function');
    expect(typeof mod.DripError).toBe('function');
  });

  it('imports next entry point', async () => {
    const mod = await import('@drip-sdk/node/next');
    expect(typeof mod.withDrip).toBe('function');
    expect(typeof mod.createWithDrip).toBe('function');
  });

  it('imports express entry point', async () => {
    const mod = await import('@drip-sdk/node/express');
    expect(typeof mod.dripMiddleware).toBe('function');
    expect(typeof mod.createDripMiddleware).toBe('function');
  });

  it('imports middleware entry point', async () => {
    const mod = await import('@drip-sdk/node/middleware');
    expect(typeof mod.processRequest).toBe('function');
    expect(typeof mod.hasPaymentProof).toBe('function');
    expect(typeof mod.parsePaymentProof).toBe('function');
    expect(typeof mod.generatePaymentRequest).toBe('function');
  });

  it('imports langchain entry point', async () => {
    const mod = await import('@drip-sdk/node/langchain');
    expect(typeof mod.DripCallbackHandler).toBe('function');
    expect(typeof mod.getModelPricing).toBe('function');
    expect(typeof mod.calculateCost).toBe('function');
    expect(mod.OPENAI_PRICING).toBeDefined();
    expect(mod.ANTHROPIC_PRICING).toBeDefined();
  });
});
