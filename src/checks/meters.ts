import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const listMetersCheck: Check = {
  name: 'Meters List',
  description: 'List available meters',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const sdk = (client as unknown as {
        sdk: {
          listMeters?: () => Promise<{ data: Array<{ id: string; name: string; unit: string }> } | Array<{ id: string; name: string; unit: string }>>;
        };
      }).sdk;

      if (!sdk.listMeters) {
        const duration = performance.now() - start;
        return {
          name: 'Meters List',
          success: true,
          duration,
          message: 'Skipped (listMeters not available)',
          details: 'The listMeters method is not available in the SDK',
        };
      }

      const result = await sdk.listMeters();
      const duration = performance.now() - start;

      const meters = Array.isArray(result) ? result : result.data || [];
      const count = meters.length;
      const meterNames = meters.slice(0, 3).map((m: { name: string }) => m.name).join(', ');

      return {
        name: 'Meters List',
        success: true,
        duration,
        message: `Found ${count} meter(s)`,
        details: count > 0 ? `Meters: ${meterNames}${count > 3 ? '...' : ''}` : undefined,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Meters List',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Meters List',
        success: false,
        duration,
        message: err.message || 'Failed to list meters',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
