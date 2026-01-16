import { createHmac } from 'crypto';
import { Check, CheckContext, CheckResult } from '../types.js';
import { Drip } from '../drip-client.js';

// Local helper to generate webhook signature (avoids ESM/CJS issues with SDK)
function generateTestSignature(payload: string, secret: string): string {
  const timestamp = Math.floor(Date.now() / 1000);
  const signaturePayload = `${timestamp}.${payload}`;
  const signature = createHmac('sha256', secret)
    .update(signaturePayload)
    .digest('hex');
  return `t=${timestamp},v1=${signature}`;
}

export const webhookSignCheck: Check = {
  name: 'Webhook Sign',
  description: 'Test webhook signature generation and verification',
  quick: true,
  async run(_ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    try {
      const testPayload = JSON.stringify({
        type: 'charge.succeeded',
        data: { chargeId: 'chg_test123' },
      });
      const testSecret = 'whsec_test_secret';

      // Generate a valid signature locally
      const validSignature = generateTestSignature(testPayload, testSecret);

      // Verify the signature using the SDK's async method
      const isValid = await Drip.verifyWebhookSignatureAsync(
        testPayload,
        validSignature,
        testSecret
      );

      const duration = performance.now() - start;

      if (isValid) {
        return {
          name: 'Webhook Sign',
          success: true,
          duration,
          message: 'Signature valid',
        };
      } else {
        return {
          name: 'Webhook Sign',
          success: false,
          duration,
          message: 'Valid signature was rejected',
          suggestion: 'Webhook signature generation/verification is broken',
        };
      }
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
  async run(_ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    try {
      const testPayload = JSON.stringify({
        type: 'charge.succeeded',
        data: { chargeId: 'chg_test123' },
      });
      const testSecret = 'whsec_test_secret';
      const invalidSignature = 'invalid_signature';

      const isValid = await Drip.verifyWebhookSignatureAsync(
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
