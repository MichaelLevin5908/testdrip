import { Check, CheckContext, CheckResult } from '../types.js';
import { Drip, createClient } from '../drip-client.js';

export const generateIdempotencyKeyCheck: Check = {
  name: 'Idempotency Key Gen',
  description: 'Test static idempotency key generation',
  quick: true,
  async run(_ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    try {
      // Check if the static method exists on the Drip class
      const DripClass = Drip as unknown as {
        generateIdempotencyKey?: (data: { customerId: string; meter: string; sequence: number }) => string;
      };

      if (!DripClass.generateIdempotencyKey) {
        const duration = performance.now() - start;
        return {
          name: 'Idempotency Key Gen',
          success: true,
          duration,
          message: 'Skipped (generateIdempotencyKey not available)',
          details: 'The static generateIdempotencyKey method is not available',
        };
      }

      // Test that same inputs produce same key
      const key1 = DripClass.generateIdempotencyKey({
        customerId: 'test-customer',
        meter: 'tokens',
        sequence: 1,
      });

      const key2 = DripClass.generateIdempotencyKey({
        customerId: 'test-customer',
        meter: 'tokens',
        sequence: 1,
      });

      // Test that different inputs produce different keys
      const key3 = DripClass.generateIdempotencyKey({
        customerId: 'test-customer',
        meter: 'tokens',
        sequence: 2,
      });

      const duration = performance.now() - start;

      if (key1 !== key2) {
        return {
          name: 'Idempotency Key Gen',
          success: false,
          duration,
          message: 'Same inputs produced different keys',
          suggestion: 'Idempotency key generation is not deterministic',
        };
      }

      if (key1 === key3) {
        return {
          name: 'Idempotency Key Gen',
          success: false,
          duration,
          message: 'Different inputs produced same key',
          suggestion: 'Idempotency key generation may have a collision issue',
        };
      }

      return {
        name: 'Idempotency Key Gen',
        success: true,
        duration,
        message: 'Keys generated correctly',
        details: `Sample key: ${key1.slice(0, 20)}...`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as Error;
      return {
        name: 'Idempotency Key Gen',
        success: false,
        duration,
        message: err.message || 'Failed to generate idempotency key',
      };
    }
  },
};

export const createStreamMeterCheck: Check = {
  name: 'Stream Meter Create',
  description: 'Create stream meter instance',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'Stream Meter Create',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const client = createClient(ctx);

      // Test creating a stream meter
      const streamMeter = client.createStreamMeter({
        customerId,
        meter: 'tokens',
      });

      // Verify basic operations work
      streamMeter.addSync(50);
      streamMeter.addSync(50);

      const total = streamMeter.getTotal();
      const duration = performance.now() - start;

      if (total !== 100) {
        return {
          name: 'Stream Meter Create',
          success: false,
          duration,
          message: `Expected total 100, got ${total}`,
          suggestion: 'Stream meter accumulation is not working correctly',
        };
      }

      return {
        name: 'Stream Meter Create',
        success: true,
        duration,
        message: 'Stream meter created and tested',
        details: `Accumulated: ${total} tokens`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as Error;
      return {
        name: 'Stream Meter Create',
        success: false,
        duration,
        message: err.message || 'Failed to create stream meter',
      };
    }
  },
};
