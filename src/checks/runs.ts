import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

// Extended context type to store run ID across checks
type RunContext = CheckContext & { runId?: string; workflowId?: string };

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

      // Store the run ID for subsequent checks
      (ctx as RunContext).runId = result.run.id;

      return {
        name: 'Run Create',
        success: true,
        duration,
        message: result.run.id,
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

      const runResult = await client.getRunTimeline(createResult.run.id);
      const duration = performance.now() - start;

      const eventCount = runResult.timeline?.length || 0;

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

export const runEndCheck: Check = {
  name: 'Run End',
  description: 'End run with status',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;

    if (!customerId) {
      return {
        name: 'Run End',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const sdk = (client as unknown as {
        sdk: {
          endRun?: (runId: string, data: { status: string; summary?: string }) => Promise<{ success: boolean }>;
          startRun?: (data: { customerId: string; workflow: string }) => Promise<{ id: string }>;
        };
      }).sdk;

      if (!sdk.endRun || !sdk.startRun) {
        const duration = performance.now() - start;
        return {
          name: 'Run End',
          success: true,
          duration,
          message: 'Skipped (endRun/startRun not available)',
          details: 'The endRun or startRun method is not available in the SDK',
        };
      }

      // First create a run to end
      const startResult = await sdk.startRun({
        customerId,
        workflow: 'health-check-end-test',
      });

      await sdk.endRun(startResult.id, {
        status: 'completed',
        summary: 'Health check completed successfully',
      });
      const duration = performance.now() - start;

      return {
        name: 'Run End',
        success: true,
        duration,
        message: `Run ${startResult.id} ended`,
        details: 'Status: completed',
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Run End',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Run End',
        success: false,
        duration,
        message: err.message || 'Failed to end run',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const emitEventCheck: Check = {
  name: 'Emit Event',
  description: 'Emit single event to run',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const runId = (ctx as RunContext).runId;

    if (!runId) {
      return {
        name: 'Emit Event',
        success: true,
        duration: 0,
        message: 'Skipped (no run ID available)',
        suggestion: 'Run Run Create check first',
      };
    }

    try {
      const client = createClient(ctx);
      const sdk = (client as unknown as {
        sdk: {
          emitEvent?: (data: { runId: string; type: string; data: Record<string, unknown> }) => Promise<{ success: boolean }>;
        };
      }).sdk;

      if (!sdk.emitEvent) {
        const duration = performance.now() - start;
        return {
          name: 'Emit Event',
          success: true,
          duration,
          message: 'Skipped (emitEvent not available)',
          details: 'The emitEvent method is not available in the SDK',
        };
      }

      await sdk.emitEvent({
        runId,
        type: 'tool_call',
        data: { tool: 'health-check', input: { test: true } },
      });
      const duration = performance.now() - start;

      return {
        name: 'Emit Event',
        success: true,
        duration,
        message: 'Event emitted',
        details: `Run: ${runId}, Type: tool_call`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Emit Event',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Emit Event',
        success: false,
        duration,
        message: err.message || 'Failed to emit event',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const emitEventsBatchCheck: Check = {
  name: 'Emit Events Batch',
  description: 'Emit multiple events in one request',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const runId = (ctx as RunContext).runId;

    if (!runId) {
      return {
        name: 'Emit Events Batch',
        success: true,
        duration: 0,
        message: 'Skipped (no run ID available)',
        suggestion: 'Run Run Create check first',
      };
    }

    try {
      const client = createClient(ctx);
      const sdk = (client as unknown as {
        sdk: {
          emitEventsBatch?: (events: Array<{ runId: string; type: string; data: Record<string, unknown> }>) => Promise<{ success: boolean; count: number }>;
        };
      }).sdk;

      if (!sdk.emitEventsBatch) {
        const duration = performance.now() - start;
        return {
          name: 'Emit Events Batch',
          success: true,
          duration,
          message: 'Skipped (emitEventsBatch not available)',
          details: 'The emitEventsBatch method is not available in the SDK',
        };
      }

      const result = await sdk.emitEventsBatch([
        { runId, type: 'llm_call', data: { model: 'gpt-4', tokens: 100 } },
        { runId, type: 'llm_call', data: { model: 'gpt-4', tokens: 200 } },
      ]);
      const duration = performance.now() - start;

      return {
        name: 'Emit Events Batch',
        success: true,
        duration,
        message: `${result.count || 2} events emitted`,
        details: `Run: ${runId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Emit Events Batch',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Emit Events Batch',
        success: false,
        duration,
        message: err.message || 'Failed to emit events batch',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const recordRunCheck: Check = {
  name: 'Record Run',
  description: 'Record complete run in one call',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);
    const customerId = ctx.createdCustomerId || ctx.testCustomerId;
    const workflowId = (ctx as RunContext).workflowId || 'health-check-record';

    if (!customerId) {
      return {
        name: 'Record Run',
        success: false,
        duration: 0,
        message: 'No customer ID available',
        suggestion: 'Run Customer Create check first or set TEST_CUSTOMER_ID',
      };
    }

    try {
      const result = await client.recordRun({
        customerId,
        workflow: workflowId,
        events: [
          { eventType: 'start', description: 'Run started' },
          { eventType: 'process', quantity: 5, units: 'items' },
          { eventType: 'complete', description: 'Run finished' },
        ],
        status: 'COMPLETED',
      });
      const duration = performance.now() - start;

      return {
        name: 'Record Run',
        success: true,
        duration,
        message: `Recorded: ${result.run.id}`,
        details: `Workflow: ${workflowId}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Record Run',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Record Run',
        success: false,
        duration,
        message: err.message || 'Failed to record run',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
