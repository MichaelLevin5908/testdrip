import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const trackUsageCheck: Check = {
  name: 'Track Usage',
  description: 'Track usage without billing (internal visibility)',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    // Prefer testCustomerId (funded) for tests, fall back to created customer
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'Track Usage',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.trackUsage({
        customerId,
        meter: 'api_call',
        quantity: 1,
        description: 'Health check test usage',
        units: 'requests',
      });
      const duration = performance.now() - start;

      return {
        name: 'Track Usage',
        success: result.success,
        duration,
        message: `${result.usageEventId} (${result.message})`,
        details: `Usage ID: ${result.usageEventId}, Type: ${result.usageType}, Quantity: ${result.quantity}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      return {
        name: 'Track Usage',
        success: false,
        duration,
        message: err.code || err.message || 'Failed to track usage',
        details: `${err.message} (code: ${err.code}, status: ${err.statusCode})`,
      };
    }
  },
};
