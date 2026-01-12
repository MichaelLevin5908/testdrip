import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const balanceGetCheck: Check = {
  name: 'Balance Get',
  description: 'Get customer balance',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Balance Get',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.getBalance(customerId);
      const duration = performance.now() - start;

      return {
        name: 'Balance Get',
        success: true,
        duration,
        message: `$${result.balanceUsdc} USDC`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Balance Get',
        success: false,
        duration,
        message: err.message || 'Failed to get balance',
        details: `Customer ID: ${customerId}`,
      };
    }
  },
};
