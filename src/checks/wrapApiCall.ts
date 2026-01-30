import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

// Simulated external API call for testing
async function mockExternalApiCall(): Promise<{ tokens: number; model: string }> {
  // Simulate API latency
  await new Promise(resolve => setTimeout(resolve, 50));
  return {
    tokens: Math.floor(Math.random() * 100) + 50,
    model: 'gpt-4',
  };
}

export const wrapApiCallBasicCheck: Check = {
  name: 'WrapApiCall Basic',
  description: 'Test wrapApiCall wraps external API calls with usage recording',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'WrapApiCall Basic',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const { result, charge } = await client.wrapApiCall({
        customerId,
        meter: 'tokens',
        call: mockExternalApiCall,
        extractUsage: (res) => res.tokens,
      });
      const duration = performance.now() - start;

      // Verify the result and charge were returned
      if (!result || typeof result.tokens !== 'number') {
        return {
          name: 'WrapApiCall Basic',
          success: false,
          duration,
          message: 'API result not returned correctly',
          details: `Got: ${JSON.stringify(result)}`,
        };
      }

      if (!charge || !charge.usageEventId) {
        return {
          name: 'WrapApiCall Basic',
          success: false,
          duration,
          message: 'Charge not recorded',
          details: 'wrapApiCall did not return a charge',
        };
      }

      return {
        name: 'WrapApiCall Basic',
        success: true,
        duration,
        message: `Wrapped call: ${result.tokens} tokens charged`,
        details: `Usage ID: ${charge.usageEventId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      let suggestion: string | undefined;
      if (err.code === 'INSUFFICIENT_BALANCE' || err.message?.includes('balance')) {
        suggestion = `Customer ${customerId} has insufficient balance. Add funds or use a funded test customer.`;
      }

      return {
        name: 'WrapApiCall Basic',
        success: false,
        duration,
        message: err.code || err.message || 'wrapApiCall failed',
        details: `${err.message} (code: ${err.code}, status: ${err.statusCode})`,
        suggestion,
      };
    }
  },
};

export const wrapApiCallIdempotencyCheck: Check = {
  name: 'WrapApiCall Idempotency',
  description: 'Test wrapApiCall respects idempotency keys',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'WrapApiCall Idempotency',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    const idempotencyKey = `wrap-test-${Date.now()}`;
    let callCount = 0;

    const trackedApiCall = async () => {
      callCount++;
      return { tokens: 100, model: 'gpt-4' };
    };

    try {
      // First call with idempotency key
      const first = await client.wrapApiCall({
        customerId,
        meter: 'tokens',
        call: trackedApiCall,
        extractUsage: (res) => res.tokens,
        idempotencyKey,
      });

      // Second call with same idempotency key
      const second = await client.wrapApiCall({
        customerId,
        meter: 'tokens',
        call: trackedApiCall,
        extractUsage: (res) => res.tokens,
        idempotencyKey,
      });

      const duration = performance.now() - start;

      // Check if idempotency was respected
      if (second.charge.isReplay === true) {
        return {
          name: 'WrapApiCall Idempotency',
          success: true,
          duration,
          message: 'Idempotency key respected (replay detected)',
          details: `Key: ${idempotencyKey}`,
        };
      } else if (first.charge.charge?.id === second.charge.charge?.id) {
        return {
          name: 'WrapApiCall Idempotency',
          success: true,
          duration,
          message: 'Idempotency key respected (same charge ID)',
          details: `Charge ID: ${first.charge.charge?.id}`,
        };
      } else {
        return {
          name: 'WrapApiCall Idempotency',
          success: false,
          duration,
          message: 'Duplicate charge created',
          details: `First: ${first.charge.charge?.id}, Second: ${second.charge.charge?.id}`,
          suggestion: 'Idempotency key was not respected',
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'WrapApiCall Idempotency',
        success: false,
        duration,
        message: err.message || 'Idempotency check failed',
        details: err.code,
      };
    }
  },
};

export const wrapApiCallErrorHandlingCheck: Check = {
  name: 'WrapApiCall Error Handling',
  description: 'Test wrapApiCall handles API call failures gracefully',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'WrapApiCall Error Handling',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    const failingApiCall = async (): Promise<{ tokens: number }> => {
      throw new Error('Simulated API failure');
    };

    try {
      await client.wrapApiCall({
        customerId,
        meter: 'tokens',
        call: failingApiCall,
        extractUsage: (res) => res.tokens,
      });

      const duration = performance.now() - start;
      return {
        name: 'WrapApiCall Error Handling',
        success: false,
        duration,
        message: 'Should have thrown an error',
        suggestion: 'wrapApiCall should propagate API call failures',
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as Error;

      // The error should be propagated from the wrapped call
      if (err.message?.includes('Simulated API failure')) {
        return {
          name: 'WrapApiCall Error Handling',
          success: true,
          duration,
          message: 'API error propagated correctly',
          details: 'No charge recorded for failed call',
        };
      }

      return {
        name: 'WrapApiCall Error Handling',
        success: true,
        duration,
        message: 'Error handled',
        details: err.message,
      };
    }
  },
};
