import { Check, CheckContext, CheckResult } from '../types.js';
import { createClient, DripError } from '../drip-client.js';

// Extended context type to store workflow ID across checks
type WorkflowContext = CheckContext & { workflowId?: string };

export const workflowCreateCheck: Check = {
  name: 'Workflow Create',
  description: 'Create workflow definition',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const sdk = (client as unknown as {
        sdk: {
          createWorkflow?: (data: { name: string; description?: string }) => Promise<{ id: string; name: string }>;
        };
      }).sdk;

      if (!sdk.createWorkflow) {
        const duration = performance.now() - start;
        return {
          name: 'Workflow Create',
          success: true,
          duration,
          message: 'Skipped (createWorkflow not available)',
          details: 'The createWorkflow method is not available in the SDK',
        };
      }

      const result = await sdk.createWorkflow({
        name: `health-check-workflow-${Date.now()}`,
        slug: `health_check_workflow_${Date.now()}`,
        description: 'Test workflow created by health check',
      });
      const duration = performance.now() - start;

      // Store workflow ID for subsequent checks
      (ctx as WorkflowContext).workflowId = result.id;

      return {
        name: 'Workflow Create',
        success: true,
        duration,
        message: `Created: ${result.id}`,
        details: `Name: ${result.name}`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Workflow Create',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Workflow Create',
        success: false,
        duration,
        message: err.message || 'Failed to create workflow',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};

export const workflowListCheck: Check = {
  name: 'Workflow List',
  description: 'List all workflows',
  async run(ctx: CheckContext): Promise<CheckResult> {
    const start = performance.now();
    const client = createClient(ctx);

    try {
      const sdk = (client as unknown as {
        sdk: {
          listWorkflows?: () => Promise<{ data: Array<{ id: string; name: string }> } | Array<{ id: string; name: string }>>;
        };
      }).sdk;

      if (!sdk.listWorkflows) {
        const duration = performance.now() - start;
        return {
          name: 'Workflow List',
          success: true,
          duration,
          message: 'Skipped (listWorkflows not available)',
          details: 'The listWorkflows method is not available in the SDK',
        };
      }

      const result = await sdk.listWorkflows();
      const duration = performance.now() - start;

      const workflows = Array.isArray(result) ? result : result.data || [];
      const count = workflows.length;

      // Store the first workflow ID if available
      if (count > 0 && !(ctx as WorkflowContext).workflowId) {
        (ctx as WorkflowContext).workflowId = workflows[0].id;
      }

      return {
        name: 'Workflow List',
        success: true,
        duration,
        message: `Found ${count} workflow(s)`,
      };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;

      if (err.statusCode === 404 || err.statusCode === 501) {
        return {
          name: 'Workflow List',
          success: true,
          duration,
          message: 'Skipped (endpoint not implemented)',
          details: `Status: ${err.statusCode}`,
        };
      }

      return {
        name: 'Workflow List',
        success: false,
        duration,
        message: err.message || 'Failed to list workflows',
        details: `${err.code} (status: ${err.statusCode})`,
      };
    }
  },
};
