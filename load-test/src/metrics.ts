import { LatencyStats, RequestResult, ScenarioResult } from './types.js';

export function calculateLatencyStats(latencies: number[]): LatencyStats {
  if (latencies.length === 0) {
    return { min: 0, max: 0, avg: 0, p50: 0, p95: 0, p99: 0 };
  }

  const sorted = [...latencies].sort((a, b) => a - b);
  const sum = sorted.reduce((a, b) => a + b, 0);

  return {
    min: sorted[0],
    max: sorted[sorted.length - 1],
    avg: sum / sorted.length,
    p50: percentile(sorted, 50),
    p95: percentile(sorted, 95),
    p99: percentile(sorted, 99),
  };
}

function percentile(sorted: number[], p: number): number {
  const index = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

export class MetricsCollector {
  private results: RequestResult[] = [];
  private errors: Map<string, number> = new Map();
  private startTime: number = 0;

  start(): void {
    this.startTime = performance.now();
  }

  record(result: RequestResult): void {
    this.results.push(result);
    if (!result.success && result.errorCode) {
      const count = this.errors.get(result.errorCode) || 0;
      this.errors.set(result.errorCode, count + 1);
    }
  }

  getResult(scenario: string): ScenarioResult {
    const duration = performance.now() - this.startTime;
    const succeeded = this.results.filter(r => r.success).length;
    const failed = this.results.filter(r => !r.success).length;
    const latencies = this.results.filter(r => r.success).map(r => r.duration);

    return {
      scenario,
      duration,
      totalRequests: this.results.length,
      succeeded,
      failed,
      latencies,
      errors: this.errors,
    };
  }

  reset(): void {
    this.results = [];
    this.errors = new Map();
    this.startTime = 0;
  }
}

export async function runConcurrent<T>(
  tasks: (() => Promise<T>)[],
  concurrency: number
): Promise<T[]> {
  const results: T[] = [];
  const executing: Promise<void>[] = [];

  for (const task of tasks) {
    const p = task().then(result => {
      results.push(result);
    });
    executing.push(p);

    if (executing.length >= concurrency) {
      await Promise.race(executing);
      // Remove completed promises
      for (let i = executing.length - 1; i >= 0; i--) {
        const status = await Promise.race([
          executing[i].then(() => 'resolved'),
          Promise.resolve('pending'),
        ]);
        if (status === 'resolved') {
          executing.splice(i, 1);
        }
      }
    }
  }

  await Promise.allSettled(executing);
  return results;
}

export async function runWithRateLimit<T>(
  taskGenerator: () => Promise<T>,
  rps: number,
  durationMs: number,
  onResult: (result: T) => void
): Promise<void> {
  const interval = 1000 / rps;
  const endTime = performance.now() + durationMs;
  const pending: Promise<void>[] = [];

  while (performance.now() < endTime) {
    const startTime = performance.now();

    // Fire and track the promise
    const p = taskGenerator()
      .then(onResult)
      .catch(() => {});
    pending.push(p);

    const elapsed = performance.now() - startTime;
    const waitTime = Math.max(0, interval - elapsed);

    if (waitTime > 0) {
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }

  // Wait for ALL pending requests to complete (with reasonable timeout)
  await Promise.race([
    Promise.allSettled(pending),
    new Promise(resolve => setTimeout(resolve, 60000)), // 60s max wait
  ]);
}
