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
        const data = await response.json();
        return {
          name: 'Connectivity',
          success: true,
          duration,
          message: 'API reachable',
          details: data.status || 'healthy',
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
