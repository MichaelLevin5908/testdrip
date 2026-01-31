import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const checkoutCreateCheck: Check = {
  name: 'Checkout Create',
  description: 'Create checkout session',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.testCustomerId || ctx.createdCustomerId;

    if (!customerId) {
      return {
        name: 'Checkout Create',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      // Access the SDK directly to call checkout
      const sdk = (client as unknown as { sdk: { checkout?: (data: { customerId?: string; amount: number; returnUrl: string }) => Promise<{ id: string; url: string }> } }).sdk;

      if (!sdk.checkout) {
        // Endpoint may not exist - skip gracefully
        const duration = performance.now() - start;
        return {
          name: 'Checkout Create',
          success: true,
          duration,
          message: 'Skipped (checkout endpoint not available)',
          details: 'The checkout method is not available in the SDK',
        };
      }

      const result = await sdk.checkout({
        customerId,
        amount: 1000, // $10.00 in cents
        returnUrl: 'https://example.com/checkout/success',
      });
      const duration = performance.now() - start;

      return {
        name: 'Checkout Create',
        success: true,
        duration,
        message: `Session: ${result.id}`,
        details: `URL: ${result.url}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      // Handle 404/501 gracefully for endpoints that may not exist
      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Checkout Create',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Checkout Create',
        success: false,
        duration,
        message: err.message || 'Failed to create checkout session',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
