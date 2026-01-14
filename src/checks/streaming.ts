import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const streamMeterAddCheck: Check = {
  name: 'StreamMeter Add',
  description: 'Test StreamMeter accumulation',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'StreamMeter Add',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const meter = client.createStreamMeter({
        customerId,
        meter: 'health_check_stream',
      });

      // Add quantities synchronously
      meter.addSync(25);
      meter.addSync(25);
      meter.addSync(50);

      const total = meter.getTotal();
      const duration = performance.now() - start;

      if (total === 100) {
        return {
          name: 'StreamMeter Add',
          success: true,
          duration,
          message: `Accumulated ${total} units`,
        };
      } else {
        return {
          name: 'StreamMeter Add',
          success: false,
          duration,
          message: `Expected 100 units, got ${total}`,
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as Error;
      return {
        name: 'StreamMeter Add',
        success: false,
        duration,
        message: err.message || 'Failed to add to StreamMeter',
      };
    }
  },
};

export const streamMeterFlushCheck: Check = {
  name: 'StreamMeter Flush',
  description: 'Test StreamMeter flush and charge',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'StreamMeter Flush',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const meter = client.createStreamMeter({
        customerId,
        meter: 'api_calls',
      });

      meter.addSync(50);
      const result = await meter.flush();
      const duration = performance.now() - start;

      if (result.charge) {
        return {
          name: 'StreamMeter Flush',
          success: true,
          duration,
          message: 'Charged successfully',
          details: `Charge: $${result.charge.amountUsdc}`,
        };
      } else {
        return {
          name: 'StreamMeter Flush',
          success: false,
          duration,
          message: 'No charge created',
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'StreamMeter Flush',
        success: false,
        duration,
        message: err.message || 'Failed to flush StreamMeter',
        details: err.code,
      };
    }
  },
};
