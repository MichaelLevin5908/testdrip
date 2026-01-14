import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const idempotencyCheck: Check = {
  name: 'Idempotency',
  description: 'Test duplicate detection',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Idempotency',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    const idempotencyKey = `health-check-${Date.now()}`;

    try {
      // First charge with idempotency key
      const firstResult = await client.charge({
        customerId,
        meter: 'api_calls',
        quantity: 1,
        idempotencyKey,
      });

      // Second charge with same idempotency key
      const secondResult = await client.charge({
        customerId,
        meter: 'api_calls',
        quantity: 1,
        idempotencyKey,
      });

      const duration = performance.now() - start;

      // Check if second request was detected as replay
      if (secondResult.isReplay === true) {
        return {
          name: 'Idempotency',
          success: true,
          duration,
          message: 'Replay detected correctly',
          details: `Key: ${idempotencyKey}`,
        };
      } else if (firstResult.charge.id === secondResult.charge.id) {
        // Some implementations return same charge ID instead of isReplay flag
        return {
          name: 'Idempotency',
          success: true,
          duration,
          message: 'Duplicate prevented (same charge ID)',
          details: `Charge ID: ${firstResult.charge.id}`,
        };
      } else {
        return {
          name: 'Idempotency',
          success: false,
          duration,
          message: 'Duplicate charge created',
          details: `First: ${firstResult.charge.id}, Second: ${secondResult.charge.id}`,
          suggestion: 'Idempotency key was not respected - duplicate charges were created',
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Idempotency',
        success: false,
        duration,
        message: err.message || 'Idempotency check failed',
        details: err.code,
      };
    }
  },
};
