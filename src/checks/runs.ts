import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

export const runCreateCheck: Check = {
  name: 'Run Create',
  description: 'Create execution run',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Run Create',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.recordRun({
        customerId,
        workflow: 'health-check-workflow',
        events: [
          { eventType: 'task.start', description: 'Starting health check task' },
          { eventType: 'task.process', quantity: 1, units: 'tasks' },
          { eventType: 'task.complete', description: 'Health check completed' },
        ],
        status: 'COMPLETED',
      });

      const duration = performance.now() - start;

      return {
        name: 'Run Create',
        success: true,
        duration,
        message: result.runId,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Run Create',
        success: false,
        duration,
        message: err.message || 'Failed to create run',
        details: err.code,
      };
    }
  },
};

export const runTimelineCheck: Check = {
  name: 'Run Timeline',
  description: 'Verify run events recorded',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Run Timeline',
        success: false,
        duration: 0,
        message: 'No customer ID available',
      };
    }

    try {
      // Create a run and then retrieve it
      const createResult = await client.recordRun({
        customerId,
        workflow: 'health-check-timeline',
        events: [
          { eventType: 'event1', description: 'First event' },
          { eventType: 'event2', description: 'Second event' },
          { eventType: 'event3', description: 'Third event' },
        ],
        status: 'COMPLETED',
      });

      const runResult = await client.getRun(createResult.runId);
      const duration = performance.now() - start;

      const eventCount = runResult.events?.length || 0;

      return {
        name: 'Run Timeline',
        success: true,
        duration,
        message: `${eventCount} events recorded`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        name: 'Run Timeline',
        success: false,
        duration,
        message: err.message || 'Failed to get run timeline',
        details: err.code,
      };
    }
  },
};
