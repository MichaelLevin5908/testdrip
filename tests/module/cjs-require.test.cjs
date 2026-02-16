/**
 * Module Tests: CJS require for all 6 entry points.
 * This file MUST have .cjs extension to force CJS resolution path.
 * Validates the package.json exports "require" condition.
 *
 * Note: Vitest runs this through its transform pipeline,
 * so we use dynamic require() to actually test CJS resolution.
 */
const { describe, it, expect } = require('vitest');

describe('CJS requires', () => {
  it('requires main entry point', () => {
    const mod = require('@drip-sdk/node');
    expect(typeof mod.Drip).toBe('function');
    expect(typeof mod.DripError).toBe('function');
    expect(typeof mod.StreamMeter).toBe('function');
  });

  it('requires core entry point', () => {
    const mod = require('@drip-sdk/node/core');
    expect(typeof mod.Drip).toBe('function');
    expect(typeof mod.DripError).toBe('function');
  });

  it('requires next entry point', () => {
    const mod = require('@drip-sdk/node/next');
    expect(typeof mod.withDrip).toBe('function');
  });

  it('requires express entry point', () => {
    const mod = require('@drip-sdk/node/express');
    expect(typeof mod.dripMiddleware).toBe('function');
  });

  it('requires middleware entry point', () => {
    const mod = require('@drip-sdk/node/middleware');
    expect(typeof mod.processRequest).toBe('function');
    expect(typeof mod.hasPaymentProof).toBe('function');
  });

  it('requires langchain entry point', () => {
    const mod = require('@drip-sdk/node/langchain');
    expect(typeof mod.DripCallbackHandler).toBe('function');
    expect(typeof mod.getModelPricing).toBe('function');
  });
});
