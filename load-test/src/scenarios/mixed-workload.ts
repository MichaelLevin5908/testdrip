import { Drip, DripError } from '../drip-client.js';
import { MetricsCollector, runWithRateLimit } from '../metrics.js';
import { ScenarioConfig, ScenarioResult, RequestResult } from '../types.js';

type OperationType = 'charge' | 'balance' | 'customer';

interface OperationResult extends RequestResult {
  operation: OperationType;
}

export async function runMixedWorkload(config: ScenarioConfig): Promise<ScenarioResult> {
  const client = new Drip({ apiKey: config.apiKey, apiUrl: config.apiUrl });
  const metrics = new MetricsCollector();

  const rps = config.rps || 100;
  const durationMs = (config.duration || 60) * 1000;

  // Operation distribution: 70% charges, 20% balance, 10% customer ops
  const operations: OperationType[] = ['charge', 'charge', 'charge', 'charge', 'charge', 'charge', 'charge', 'balance', 'balance', 'customer'];

  let operationCount = 0;
  const operationCounts: Record<OperationType, number> = {
    charge: 0,
    balance: 0,
    customer: 0,
  };

  metrics.start();

  const generateTask = async (): Promise<OperationResult> => {
    const operation = operations[Math.floor(Math.random() * operations.length)];
    operationCounts[operation]++;
    operationCount++;

    if (operationCount % 100 === 0) {
      process.stdout.write(`\rRequests: ${operationCount} (${Math.round(operationCount / (rps * (durationMs / 1000)) * 100)}%)`);
    }

    const start = performance.now();

    try {
      switch (operation) {
        case 'charge':
          await client.charge({
            customerId: config.customerId,
            usageType: 'load_test_mixed',
            quantity: Math.floor(Math.random() * 10) + 1,
          });
          break;

        case 'balance':
          await client.getBalance(config.customerId);
          break;

        case 'customer':
          await client.getCustomer(config.customerId);
          break;
      }

      const duration = performance.now() - start;
      return { success: true, duration, operation };
    } catch (error) {
      const duration = performance.now() - start;
      const err = error as DripError;
      return {
        success: false,
        duration,
        error: err.message,
        errorCode: err.code || 'UNKNOWN',
        operation,
      };
    }
  };

  const results: OperationResult[] = [];

  await runWithRateLimit(
    generateTask,
    rps,
    durationMs,
    (result) => {
      results.push(result);
      metrics.record(result);
    }
  );

  console.log(''); // New line after progress
  console.log(`Operation breakdown: charges=${operationCounts.charge}, balance=${operationCounts.balance}, customer=${operationCounts.customer}`);

  return metrics.getResult('mixed-workload');
}
