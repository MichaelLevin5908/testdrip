import { Drip, DripError } from '../drip-client.js';
import { MetricsCollector } from '../metrics.js';
import { ScenarioConfig, ScenarioResult, RequestResult } from '../types.js';

export async function runCustomerCreate(config: ScenarioConfig): Promise<ScenarioResult> {
  const client = new Drip({ apiKey: config.apiKey, apiUrl: config.apiUrl });
  const metrics = new MetricsCollector();
  const createdCustomerIds: string[] = [];

  metrics.start();

  // Create all customer creation tasks
  const tasks: (() => Promise<RequestResult>)[] = [];

  for (let i = 0; i < config.total; i++) {
    const taskIndex = i;
    tasks.push(async () => {
      const start = performance.now();
      try {
        const externalId = `load-test-${Date.now()}-${taskIndex}-${Math.random().toString(36).slice(2)}`;

        const result = await client.createCustomer({
          externalCustomerId: externalId,
          name: `Load Test Customer ${taskIndex}`,
        });

        const duration = performance.now() - start;
        createdCustomerIds.push(result.customerId);
        return { success: true, duration };
      } catch (error) {
        const duration = performance.now() - start;
        const err = error as DripError;
        return {
          success: false,
          duration,
          error: err.message,
          errorCode: err.code || 'UNKNOWN',
        };
      }
    });
  }

  // Execute with concurrency limit
  const executing: Promise<void>[] = [];
  let completed = 0;

  for (const task of tasks) {
    const p = task().then(result => {
      metrics.record(result);
      completed++;
      if (completed % 50 === 0) {
        process.stdout.write(`\rProgress: ${completed}/${config.total}`);
      }
    });
    executing.push(p);

    if (executing.length >= config.concurrency) {
      await Promise.race(executing);
      // Clean up completed promises
      const stillExecuting: Promise<void>[] = [];
      for (const ep of executing) {
        const status = await Promise.race([
          ep.then(() => 'done'),
          Promise.resolve('pending'),
        ]);
        if (status === 'pending') {
          stillExecuting.push(ep);
        }
      }
      executing.length = 0;
      executing.push(...stillExecuting);
    }
  }

  // Wait for all remaining
  await Promise.allSettled(executing);
  console.log(''); // New line after progress

  // Optional: Test duplicate handling
  if (config.useIdempotency && createdCustomerIds.length > 0) {
    console.log('Testing duplicate customer creation...');
    const duplicateStart = performance.now();
    try {
      await client.createCustomer({
        externalCustomerId: `load-test-duplicate-${Date.now()}`,
        name: 'Duplicate Test',
      });
      // Try to create same customer again
      await client.createCustomer({
        externalCustomerId: `load-test-duplicate-${Date.now()}`,
        name: 'Duplicate Test',
      });
    } catch {
      // Expected - duplicate should be rejected
      console.log(`Duplicate handling: ${(performance.now() - duplicateStart).toFixed(0)}ms`);
    }
  }

  return metrics.getResult('customer-create');
}
