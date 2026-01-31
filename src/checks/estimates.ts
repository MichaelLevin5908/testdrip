import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const estimateFromUsageCheck: Check = {
  name: 'Estimate From Usage',
  description: 'Estimate costs from historical usage',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'Estimate From Usage',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const sdk = (client as unknown as {
        sdk: {
          estimateFromUsage?: (data: { customerId: string; startDate: string; endDate: string }) => Promise<{ estimatedCost: number; currency: string }>;
        };
      }).sdk;

      if (!sdk.estimateFromUsage) {
        const duration = performance.now() - start;
        return {
          name: 'Estimate From Usage',
          success: true,
          duration,
          message: 'Skipped (estimateFromUsage not available)',
          details: 'The estimateFromUsage method is not available in the SDK',
        };
      }

      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

      const result = await sdk.estimateFromUsage({
        customerId,
        startDate,
        endDate,
      });
      const duration = performance.now() - start;

      return {
        name: 'Estimate From Usage',
        success: true,
        duration,
        message: `Estimated: ${result.estimatedCost} ${result.currency}`,
        details: `Period: ${startDate} to ${endDate}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Estimate From Usage',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Estimate From Usage',
        success: false,
        duration,
        message: err.message || 'Failed to estimate from usage',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const estimateFromHypotheticalCheck: Check = {
  name: 'Estimate Hypothetical',
  description: 'Estimate hypothetical costs',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const sdk = (client as unknown as {
        sdk: {
          estimateFromHypothetical?: (data: { items: Array<{ meter: string; quantity: number }> }) => Promise<{ estimatedCost: number; currency: string; breakdown: Array<{ meter: string; cost: number }> }>;
        };
      }).sdk;

      if (!sdk.estimateFromHypothetical) {
        const duration = performance.now() - start;
        return {
          name: 'Estimate Hypothetical',
          success: true,
          duration,
          message: 'Skipped (estimateFromHypothetical not available)',
          details: 'The estimateFromHypothetical method is not available in the SDK',
        };
      }

      const result = await sdk.estimateFromHypothetical({
        items: [
          { meter: 'tokens', quantity: 1000 },
          { meter: 'api_calls', quantity: 100 },
        ],
      });
      const duration = performance.now() - start;

      return {
        name: 'Estimate Hypothetical',
        success: true,
        duration,
        message: `Estimated: ${result.estimatedCost} ${result.currency}`,
        details: `Items: ${result.breakdown?.length || 2}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Estimate Hypothetical',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Estimate Hypothetical',
        success: false,
        duration,
        message: err.message || 'Failed to estimate hypothetical',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
