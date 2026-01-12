import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const chargeCreateCheck: Check = {
  name: 'Charge Create',
  description: 'Create charge for test customer',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Charge Create',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.charge({
        customerId,
        meter: 'health_check',
        quantity: 1,
      });
      const duration = performance.now() - start;

      return {
        name: 'Charge Create',
        success: true,
        duration,
        message: `${result.charge.chargeId} ($${result.charge.amountUsdc})`,
        details: `Charge ID: ${result.charge.chargeId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      let suggestion: string | undefined;
      if (err.code === 'INSUFFICIENT_BALANCE') {
        suggestion = `Customer ${customerId} has insufficient balance. Add funds or use a funded test customer.`;
      }

      return {
        name: 'Charge Create',
        success: false,
        duration,
        message: err.code || err.message || 'Failed to create charge',
        details: err.message,
        suggestion,
      };
    }
  },
};

export const chargeStatusCheck: Check = {
  name: 'Charge Status',
  description: 'Check charge status',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Charge Status',
        success: false,
        duration: 0,
        message: 'No customer ID available',
      };
    }

    try {
      // Create a charge to get its status
      const chargeResult = await client.charge({
        customerId,
        meter: 'health_check_status',
        quantity: 1,
      });

      const statusResult = await client.getCharge(chargeResult.charge.chargeId);
      const duration = performance.now() - start;

      return {
        name: 'Charge Status',
        success: true,
        duration,
        message: statusResult.status,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Charge Status',
        success: false,
        duration,
        message: err.message || 'Failed to get charge status',
        details: err.code,
      };
    }
  },
};
