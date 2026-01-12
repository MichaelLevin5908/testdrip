import { Check, CheckContext, CheckResult } from './types.js';

export interface RunnerOptions {
  checks: Check[];
  context: CheckContext;
  onCheckStart?: (check: Check) => void;
  onCheckComplete?: (check: Check, result: CheckResult) => void;
}

export interface RunnerResult {
  results: CheckResult[];
  totalDuration: number;
  passed: number;
  failed: number;
}

export async function runChecks(options: RunnerOptions): Promise<RunnerResult> {
  const { checks, context, onCheckStart, onCheckComplete } = options;
  const results: CheckResult[] = [];
  const startTime = performance.now();

  for (const check of checks) {
    onCheckStart?.(check);

    try {
      const timeoutPromise = new Promise<CheckResult>((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Check timed out after ${context.timeout}ms`));
        }, context.timeout);
      });

      const result = await Promise.race([
        check.run(context),
        timeoutPromise,
      ]);

      results.push(result);
      onCheckComplete?.(check, result);
    } catch (error) {
      const result: CheckResult = {
        name: check.name,
        success: false,
        duration: 0,
        message: (error as Error).message || 'Unknown error',
        details: 'Check threw an exception',
      };
      results.push(result);
      onCheckComplete?.(check, result);
    }
  }

  const totalDuration = performance.now() - startTime;
  const passed = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;

  return {
    results,
    totalDuration,
    passed,
    failed,
  };
}
