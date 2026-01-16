import { Drip, DripError } from '../drip-client.js';
import { MetricsCollector } from '../metrics.js';
import { ScenarioConfig, ScenarioResult, RequestResult } from '../types.js';

export async function runChargeBurst(config: ScenarioConfig): Promise<ScenarioResult> {
  const client = new Drip({ apiKey: config.apiKey, apiUrl: config.apiUrl });
  const metrics = new MetricsCollector();

  // Warm-up phase
  if (config.warmup && config.warmup > 0) {
    console.log(`Warming up with ${config.warmup} requests...`);
    for (let i = 0; i < config.warmup; i++) {
      try {
        await client.charge({
          customerId: config.customerId,
          meter: config.meter ?? 'api_call',
          quantity: 1,
        });
      } catch {
        // Ignore warmup errors
      }
    }
  }

  metrics.start();

  // Create all charge tasks
  const tasks: (() => Promise<RequestResult>)[] = [];

  for (let i = 0; i < config.total; i++) {
    const taskIndex = i;
    tasks.push(async () => {
      const start = performance.now();
      try {
        const idempotencyKey = config.useIdempotency
          ? `load-test-${Date.now()}-${taskIndex}`
          : undefined;

        await client.charge({
          customerId: config.customerId,
          meter: config.meter ?? 'api_call',
          quantity: 1,
          idempotencyKey,
        });

        const duration = performance.now() - start;
        return { success: true, duration };
      } catch (error) {
        const duration = performance.now() - start;
        const err = error as DripError;
        // Capture more detail for debugging
        const errorCode = err.code || (err.statusCode ? `HTTP_${err.statusCode}` : 'UNKNOWN');
        return {
          success: false,
          duration,
          error: err.message,
          errorCode,
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
      if (completed % 100 === 0) {
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

  return metrics.getResult('charge-burst');
}
