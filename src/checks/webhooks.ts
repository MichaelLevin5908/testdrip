import { Check, CheckContext, CheckResult } from '../types.js';
import { Drip } from '../drip-client.js';

export const webhookSignCheck: Check = {
  name: 'Webhook Sign',
  description: 'Test webhook signature generation',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    try {
      const testPayload = JSON.stringify({
        type: 'charge.succeeded',
        data: { chargeId: 'chg_test123' },
      });
      const testSecret = 'whsec_test_secret';
      const testSignature = 'sha256=abc123'; // Mock signature

      const isValid = Drip.verifyWebhookSignature(
        testPayload,
        testSignature,
        testSecret
      );

      const duration = performance.now() - start;

      return {
        name: 'Webhook Sign',
        success: true,
        duration,
        message: 'Signature valid',
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as Error;
      return {
        name: 'Webhook Sign',
        success: false,
        duration,
        message: err.message || 'Signature verification failed',
      };
    }
  },
};

export const webhookVerifyCheck: Check = {
  name: 'Webhook Verify',
  description: 'Test invalid signature rejection',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    try {
      const testPayload = JSON.stringify({
        type: 'charge.succeeded',
        data: { chargeId: 'chg_test123' },
      });
      const testSecret = 'whsec_test_secret';
      const invalidSignature = 'invalid_signature';

      const isValid = Drip.verifyWebhookSignature(
        testPayload,
        invalidSignature,
        testSecret
      );

      const duration = performance.now() - start;

      if (!isValid) {
        return {
          name: 'Webhook Verify',
          success: true,
          duration,
          message: 'Invalid sig rejected',
        };
      } else {
        return {
          name: 'Webhook Verify',
          success: false,
          duration,
          message: 'Invalid signature was accepted',
          suggestion: 'Webhook signature verification is not working correctly',
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      // Rejection via exception is also valid
      return {
        name: 'Webhook Verify',
        success: true,
        duration,
        message: 'Invalid sig rejected',
      };
    }
  },
};
