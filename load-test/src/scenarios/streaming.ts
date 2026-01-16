import { Drip, DripError } from '../drip-client.js';
import { MetricsCollector } from '../metrics.js';
import { ScenarioConfig, ScenarioResult, RequestResult } from '../types.js';

export async function runStreaming(config: ScenarioConfig): Promise<ScenarioResult> {
  const client = new Drip({ apiKey: config.apiKey, apiUrl: config.apiUrl });
  const metrics = new MetricsCollector();

  const eventsPerStream = config.total; // Reuse total as events per stream

  metrics.start();

  // Create concurrent StreamMeters
  const tasks: (() => Promise<RequestResult>)[] = [];

  for (let i = 0; i < config.concurrency; i++) {
    const streamIndex = i;
    tasks.push(async () => {
      const start = performance.now();
      try {
        const meter = client.createStreamMeter({
          customerId: config.customerId,
          meter: config.meter ?? 'api_call',
        });

        // Accumulate random quantities
        for (let j = 0; j < eventsPerStream; j++) {
          const quantity = Math.floor(Math.random() * 10) + 1;
          meter.addSync(quantity);
        }

        // Flush and create charge
        const result = await meter.flush();
        const duration = performance.now() - start;

        if (result.charge) {
          return { success: true, duration };
        } else {
          return {
            success: false,
            duration,
            error: 'No charge created',
            errorCode: 'NO_CHARGE',
          };
        }
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

  // Execute all streams concurrently
  const results = await Promise.allSettled(tasks.map(t => t()));

  for (const result of results) {
    if (result.status === 'fulfilled') {
      metrics.record(result.value);
    } else {
      metrics.record({
        success: false,
        duration: 0,
        error: result.reason?.message || 'Unknown error',
        errorCode: 'EXCEPTION',
      });
    }
  }

  return metrics.getResult('streaming');
}
