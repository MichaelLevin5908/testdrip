import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient } from '../drip-client.js';

export const connectivityCheck: Check = {
  name: 'Connectivity',
  description: 'Verify API is reachable',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const result = await client.ping();
      const duration = performance.now() - start;

      if (result.ok) {
        return {
          name: 'Connectivity',
          success: true,
          duration,
          message: 'API reachable',
        };
      } else {
        return {
          name: 'Connectivity',
          success: false,
          duration,
          message: 'API not responding',
          suggestion: `Check if the Drip backend is running at ${ctx.apiUrl}`,
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as Error;
      return {
        name: 'Connectivity',
        success: false,
        duration,
        message: 'Connection failed',
        details: err.message,
        suggestion: `Verify DRIP_API_URL (${ctx.apiUrl}) is correct and the server is running`,
      };
    }
  },
};

export const authenticationCheck: Check = {
  name: 'Authentication',
  description: 'Check API key validity',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    try {
      const response = await fetch(`${ctx.apiUrl}/auth/verify`, {
        headers: { 'Authorization': `Bearer ${ctx.apiKey}` },
      });
      const duration = performance.now() - start;

      if (response.ok || response.status === 404) {
        // 404 means endpoint doesn't exist but auth header was accepted
        return {
          name: 'Authentication',
          success: true,
          duration,
          message: 'API key valid',
        };
      } else if (response.status === 401 || response.status === 403) {
        return {
          name: 'Authentication',
          success: false,
          duration,
          message: 'Invalid API key',
          suggestion: 'Check your DRIP_API_KEY environment variable',
        };
      } else {
        return {
          name: 'Authentication',
          success: true,
          duration,
          message: 'API key accepted',
        };
      }
    } catch (error) {
      const duration = performance.now() - start;
      return {
        name: 'Authentication',
        success: false,
        duration,
        message: 'Auth check failed',
        details: (error as Error).message,
      };
    }
  },
};
