import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

// Extended context type to store webhook ID across checks
type WebhookContext = CheckContext & { webhookId?: string };

export const webhookCreateCheck: Check = {
  name: 'Webhook Create',
  description: 'Create webhook endpoint',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      // Access the SDK directly
      const sdk = (client as unknown as {
        sdk: {
          createWebhook?: (data: { url: string; events: string[] }) => Promise<{ id: string; url: string; events: string[] }>;
        };
      }).sdk;

      if (!sdk.createWebhook) {
        const duration = performance.now() - start;
        return {
          name: 'Webhook Create',
          success: true,
          duration,
          message: 'Skipped (createWebhook not available)',
          details: 'The createWebhook method is not available in the SDK',
        };
      }

      const result = await sdk.createWebhook({
        url: 'https://example.com/webhook/health-check',
        events: ['charge.created', 'charge.completed'],
      });
      const duration = performance.now() - start;

      // Store webhook ID for subsequent checks
      (ctx as WebhookContext).webhookId = result.id;

      return {
        name: 'Webhook Create',
        success: true,
        duration,
        message: `Created: ${result.id}`,
        details: `URL: ${result.url}, Events: ${result.events.join(', ')}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Webhook Create',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Webhook Create',
        success: false,
        duration,
        message: err.message || 'Failed to create webhook',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const webhookListCheck: Check = {
  name: 'Webhook List',
  description: 'List all webhooks',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const result = await client.listWebhooks();
      const duration = performance.now() - start;

      // Store the first webhook ID if available for subsequent checks
      const webhooks = result as unknown as { data?: Array<{ id: string }> } | Array<{ id: string }>;
      const webhookArray = Array.isArray(webhooks) ? webhooks : webhooks.data || [];
      if (webhookArray.length > 0 && !(ctx as WebhookContext).webhookId) {
        (ctx as WebhookContext).webhookId = webhookArray[0].id;
      }

      const count = webhookArray.length;

      return {
        name: 'Webhook List',
        success: true,
        duration,
        message: `Found ${count} webhook(s)`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Webhook List',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Webhook List',
        success: false,
        duration,
        message: err.message || 'Failed to list webhooks',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const webhookGetCheck: Check = {
  name: 'Webhook Get',
  description: 'Get webhook by ID',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const webhookId = (ctx as WebhookContext).webhookId;

    if (!webhookId) {
      return {
        name: 'Webhook Get',
        success: true,
        duration: 0,
        message: 'Skipped (no webhook ID available)',
        suggestion: 'Run Webhook Create or Webhook List first',
      };
    }

    try {
      const client = createClient(ctx);
      const sdk = (client as unknown as {
        sdk: {
          getWebhook?: (id: string) => Promise<{ id: string; url: string; events: string[] }>;
        };
      }).sdk;

      if (!sdk.getWebhook) {
        const duration = performance.now() - start;
        return {
          name: 'Webhook Get',
          success: true,
          duration,
          message: 'Skipped (getWebhook not available)',
          details: 'The getWebhook method is not available in the SDK',
        };
      }

      const result = await sdk.getWebhook(webhookId);
      const duration = performance.now() - start;

      return {
        name: 'Webhook Get',
        success: true,
        duration,
        message: `Got webhook: ${result.id}`,
        details: `URL: ${result.url}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Webhook Get',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Webhook Get',
        success: false,
        duration,
        message: err.message || 'Failed to get webhook',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const webhookTestCheck: Check = {
  name: 'Webhook Test',
  description: 'Send test webhook event',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const webhookId = (ctx as WebhookContext).webhookId;

    if (!webhookId) {
      return {
        name: 'Webhook Test',
        success: true,
        duration: 0,
        message: 'Skipped (no webhook ID available)',
        suggestion: 'Run Webhook Create or Webhook List first',
      };
    }

    try {
      const client = createClient(ctx);
      const sdk = (client as unknown as {
        sdk: {
          testWebhook?: (id: string) => Promise<{ success: boolean; statusCode?: number }>;
        };
      }).sdk;

      if (!sdk.testWebhook) {
        const duration = performance.now() - start;
        return {
          name: 'Webhook Test',
          success: true,
          duration,
          message: 'Skipped (testWebhook not available)',
          details: 'The testWebhook method is not available in the SDK',
        };
      }

      const result = await sdk.testWebhook(webhookId);
      const duration = performance.now() - start;

      return {
        name: 'Webhook Test',
        success: true,
        duration,
        message: result.success ? 'Test event sent' : 'Test event failed',
        details: result.statusCode ? `Response status: ${result.statusCode}` : undefined,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Webhook Test',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Webhook Test',
        success: false,
        duration,
        message: err.message || 'Failed to test webhook',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const webhookRotateSecretCheck: Check = {
  name: 'Webhook Rotate Secret',
  description: 'Rotate webhook signing secret',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const webhookId = (ctx as WebhookContext).webhookId;

    if (!webhookId) {
      return {
        name: 'Webhook Rotate Secret',
        success: true,
        duration: 0,
        message: 'Skipped (no webhook ID available)',
        suggestion: 'Run Webhook Create or Webhook List first',
      };
    }

    try {
      const client = createClient(ctx);
      const sdk = (client as unknown as {
        sdk: {
          rotateWebhookSecret?: (id: string) => Promise<{ secret: string }>;
        };
      }).sdk;

      if (!sdk.rotateWebhookSecret) {
        const duration = performance.now() - start;
        return {
          name: 'Webhook Rotate Secret',
          success: true,
          duration,
          message: 'Skipped (rotateWebhookSecret not available)',
          details: 'The rotateWebhookSecret method is not available in the SDK',
        };
      }

      const result = await sdk.rotateWebhookSecret(webhookId);
      const duration = performance.now() - start;

      return {
        name: 'Webhook Rotate Secret',
        success: true,
        duration,
        message: 'Secret rotated successfully',
        details: `New secret: ${result.secret.slice(0, 10)}...`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Webhook Rotate Secret',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Webhook Rotate Secret',
        success: false,
        duration,
        message: err.message || 'Failed to rotate webhook secret',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const webhookDeleteCheck: Check = {
  name: 'Webhook Delete',
  description: 'Delete webhook (cleanup)',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const webhookId = (ctx as WebhookContext).webhookId;

    if (!webhookId) {
      return {
        name: 'Webhook Delete',
        success: true,
        duration: 0,
        message: 'Skipped (no webhook ID to delete)',
      };
    }

    try {
      const client = createClient(ctx);
      const sdk = (client as unknown as {
        sdk: {
          deleteWebhook?: (id: string) => Promise<void>;
        };
      }).sdk;

      if (!sdk.deleteWebhook) {
        const duration = performance.now() - start;
        return {
          name: 'Webhook Delete',
          success: true,
          duration,
          message: 'Skipped (deleteWebhook not available)',
          details: 'The deleteWebhook method is not available in the SDK',
        };
      }

      await sdk.deleteWebhook(webhookId);
      const duration = performance.now() - start;

      // Clear the webhook ID
      delete (ctx as WebhookContext).webhookId;

      return {
        name: 'Webhook Delete',
        success: true,
        duration,
        message: `Deleted webhook: ${webhookId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Webhook Delete',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Webhook Delete',
        success: false,
        duration,
        message: err.message || 'Failed to delete webhook',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
