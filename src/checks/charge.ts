import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const chargeCreateCheck: Check = {
  name: 'Usage Record',
  description: 'Record usage event for test customer',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Usage Record',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.recordUsage({
        customerId,
        usageType: 'api_call',
        quantity: 1,
        units: 'calls',
      });
      const duration = performance.now() - start;

      return {
        name: 'Usage Record',
        success: true,
        duration,
        message: `${result.usageEventId}${result.charge?.amountUsdc ? ` ($${result.charge.amountUsdc})` : ''}`,
        details: `Usage ID: ${result.usageEventId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      let suggestion: string | undefined;
      if (err.code === 'INSUFFICIENT_BALANCE' || err.message?.includes('balance')) {
        suggestion = `Customer ${customerId} has insufficient balance. Add funds or use a funded test customer.`;
      }

      return {
        name: 'Usage Record',
        success: false,
        duration,
        message: err.code || err.message || 'Failed to record usage',
        details: `${err.message} (code: ${err.code}, status: ${err.statusCode})`,
        suggestion,
      };
    }
  },
};

export const chargeStatusCheck: Check = {
  name: 'Charge List',
  description: 'List charges',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const result = await client.listCharges({ limit: 5 });
      const duration = performance.now() - start;

      return {
        name: 'Charge List',
        success: true,
        duration,
        message: `Found ${result.count} charge(s)`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Charge List',
        success: false,
        duration,
        message: err.message || 'Failed to list charges',
        details: err.code,
      };
    }
  },
};
