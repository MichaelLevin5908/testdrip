import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

const TEST_CUSTOMER_PREFIX = 'health-check-';

export const customerCreateCheck: Check = {
  name: 'Customer Create',
  description: 'Create test customer',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const externalId = `${TEST_CUSTOMER_PREFIX}${Date.now()}`;

    try {
      const result = await client.createCustomer({
        externalCustomerId: externalId,
        name: 'Health Check Test Customer',
      });
      const duration = performance.now() - start;

      // Store the created customer ID for subsequent checks
      ctx.createdCustomerId = result.customerId;

      return {
        name: 'Customer Create',
        success: true,
        duration,
        message: result.customerId,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Customer Create',
        success: false,
        duration,
        message: err.message || 'Failed to create customer',
        details: err.code,
        suggestion: 'Check API permissions and backend connectivity',
      };
    }
  },
};

export const customerGetCheck: Check = {
  name: 'Customer Get',
  description: 'Retrieve customer by ID',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Customer Get',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.getCustomer(customerId);
      const duration = performance.now() - start;

      return {
        name: 'Customer Get',
        success: true,
        duration,
        message: 'Retrieved successfully',
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Customer Get',
        success: false,
        duration,
        message: err.message || 'Failed to get customer',
        details: `Customer ID: ${customerId}`,
        suggestion: 'Verify the customer exists',
      };
    }
  },
};

export const customerListCheck: Check = {
  name: 'Customer List',
  description: 'List customers with filter',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const result = await client.listCustomers({ limit: 10 });
      const duration = performance.now() - start;

      return {
        name: 'Customer List',
        success: true,
        duration,
        message: `Found ${result.customers.length} customer(s)`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Customer List',
        success: false,
        duration,
        message: err.message || 'Failed to list customers',
        details: err.code,
      };
    }
  },
};

export const customerCleanupCheck: Check = {
  name: 'Customer Cleanup',
  description: 'Delete test customer',
  async run(ctx: CheckContext): Promise<CheckResult> {
    if (ctx.skipCleanup) {
      return {
        name: 'Customer Cleanup',
        success: true,
        duration: 0,
        message: 'Skipped (SKIP_CLEANUP=true)',
      };
    }

    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'Customer Cleanup',
        success: true,
        duration: 0,
        message: 'No test customer to clean up',
      };
    }

    try {
      await client.deleteCustomer(customerId);
      const duration = performance.now() - start;

      return {
        name: 'Customer Cleanup',
        success: true,
        duration,
        message: 'Cleaned up',
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Customer Cleanup',
        success: false,
        duration,
        message: err.message || 'Failed to cleanup',
        details: `Customer ID: ${customerId}`,
      };
    }
  },
};
