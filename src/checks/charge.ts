import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const chargeCreateCheck: Check = {
  name: 'Usage Record',
  description: 'Record usage event for test customer',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    // Prefer testCustomerId (funded) for billing tests, fall back to created customer
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

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
      const result = await client.charge({
        customerId,
        meter: 'api_call',
        quantity: 1,
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

      // Store the first charge ID for subsequent checks
      if (result.data && result.data.length > 0) {
        (ctx as CheckContext & { chargeId?: string }).chargeId = result.data[0].id;
      }

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

export const getChargeCheck: Check = {
  name: 'Charge Get',
  description: 'Get a specific charge by ID',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const chargeId = (ctx as CheckContext & { chargeId?: string }).chargeId;

    if (!chargeId) {
      return {
        name: 'Charge Get',
        success: false,
        duration: 0,
        message: 'No charge ID available',
        suggestion: 'Run Charge List check first to get a charge ID',
      };
    }

    try {
      const result = await client.getCharge(chargeId);
      const duration = performance.now() - start;

      return {
        name: 'Charge Get',
        success: true,
        duration,
        message: `Charge ${result.id} (${result.status})`,
        details: `Amount: ${result.amountUsdc || 'N/A'} USDC`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      // Handle 404 gracefully
      if (err.statusCode === 404) {
        return {
          name: 'Charge Get',
          success: false,
          duration,
          message: 'Charge not found',
          suggestion: 'The charge may have been deleted or the ID is invalid',
        };
      }

      return {
        name: 'Charge Get',
        success: false,
        duration,
        message: err.message || 'Failed to get charge',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const listChargesFilteredCheck: Check = {
  name: 'Charge List Filtered',
  description: 'List charges with customer filtering',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'Charge List Filtered',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.listCharges({ customerId, limit: 10 });
      const duration = performance.now() - start;

      return {
        name: 'Charge List Filtered',
        success: true,
        duration,
        message: `Found ${result.count} charge(s) for customer`,
        details: `Customer: ${customerId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Charge List Filtered',
        success: false,
        duration,
        message: err.message || 'Failed to list charges',
        details: err.code,
      };
    }
  },
};
