import { Check, CheckContext, CheckResult } from '../types.js';

export const connectivityCheck: Check = {
  name: 'Connectivity',
  description: 'Verify API is reachable',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();

    // Health endpoint is at /health (root level, not under /v1)
    // Strip /v1 suffix if present to get base URL
    let baseUrl = ctx.apiUrl;
    if (baseUrl.endsWith('/v1')) {
      baseUrl = baseUrl.slice(0, -3);
    } else if (baseUrl.endsWith('/v1/')) {
      baseUrl = baseUrl.slice(0, -4);
    }
    baseUrl = baseUrl.replace(/\/+$/, '');

    try {
      const response = await fetch(`${baseUrl}/health`);
      const duration = performance.now() - start;

      if (response.ok) {
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
          suggestion: `Check if the Drip backend is running at ${baseUrl}`,
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
      // Use /customers endpoint with limit=1 to verify API key
      // The /auth/verify endpoint is for Privy tokens (dashboard), not API keys
      const response = await fetch(`${ctx.apiUrl}/customers?limit=1`, {
        headers: { 'Authorization': `Bearer ${ctx.apiKey}` },
      });
      const duration = performance.now() - start;

      if (response.ok) {
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
        // Other errors (500, etc.) - key may still be valid
        return {
          name: 'Authentication',
          success: true,
          duration,
          message: 'API key accepted',
          details: `Server returned ${response.status}`,
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
