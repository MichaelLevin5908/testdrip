import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const getMetricsCheck: Check = {
  name: 'SDK Metrics',
  description: 'Get SDK metrics (requires resilience enabled)',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const sdk = (client as unknown as {
        sdk: {
          getMetrics?: () => Promise<{
            requests: { total: number; successful: number; failed: number };
            latency: { average: number; p95: number; p99: number };
          }>;
        };
      }).sdk;

      if (!sdk.getMetrics) {
        const duration = performance.now() - start;
        return {
          name: 'SDK Metrics',
          success: true,
          duration,
          message: 'Skipped (getMetrics not available)',
          details: 'The getMetrics method is not available in the SDK. May require resilience to be enabled.',
        };
      }

      const result = await sdk.getMetrics();
      const duration = performance.now() - start;

      return {
        name: 'SDK Metrics',
        success: true,
        duration,
        message: `Requests: ${result.requests.total} (${result.requests.successful} ok)`,
        details: `Avg latency: ${result.latency.average}ms, P95: ${result.latency.p95}ms`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'SDK Metrics',
          success: true,
          duration,
          message: 'Skipped (resilience not enabled)',
          details: 'Enable resilience in SDK config to access metrics',
        };
      }

      return {
        name: 'SDK Metrics',
        success: false,
        duration,
        message: err.message || 'Failed to get metrics',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const getHealthCheck: Check = {
  name: 'Resilience Health',
  description: 'Get resilience health status',
  quick: true,
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const sdk = (client as unknown as {
        sdk: {
          getHealth?: () => Promise<{
            status: 'healthy' | 'degraded' | 'unhealthy';
            circuitBreaker: { state: string; failures: number };
            rateLimit: { remaining: number; resetAt: string };
          }>;
        };
      }).sdk;

      if (!sdk.getHealth) {
        const duration = performance.now() - start;
        return {
          name: 'Resilience Health',
          success: true,
          duration,
          message: 'Skipped (getHealth not available)',
          details: 'The getHealth method is not available in the SDK. May require resilience to be enabled.',
        };
      }

      const result = await sdk.getHealth();
      const duration = performance.now() - start;

      return {
        name: 'Resilience Health',
        success: true,
        duration,
        message: `Status: ${result.status}`,
        details: `Circuit: ${result.circuitBreaker.state}, Rate limit remaining: ${result.rateLimit.remaining}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Resilience Health',
          success: true,
          duration,
          message: 'Skipped (resilience not enabled)',
          details: 'Enable resilience in SDK config to access health status',
        };
      }

      return {
        name: 'Resilience Health',
        success: false,
        duration,
        message: err.message || 'Failed to get health status',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
