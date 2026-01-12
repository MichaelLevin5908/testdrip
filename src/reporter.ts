import chalk from 'chalk';
import { CheckResult } from './types.js';
import { RunnerResult } from './runner.js';

export interface ReporterOptions {
  verbose?: boolean;
  json?: boolean;
}

const CHECK_ICON = chalk.green('✓');
const FAIL_ICON = chalk.red('✗');
const PENDING_ICON = chalk.yellow('○');

function formatDuration(ms: number): string {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function padRight(str: string, len: number): string {
  return str.padEnd(len);
}

export function printHeader(): void {
  console.log(chalk.bold('\nDrip Health Check'));
  console.log(chalk.gray('═'.repeat(47)));
}

export function printCheckStart(name: string): void {
  process.stdout.write(`   ${PENDING_ICON} ${padRight(name, 22)}`);
}

export function printCheckResult(result: CheckResult, options: ReporterOptions = {}): void {
  // Clear the line and rewrite
  process.stdout.write('\r');

  const icon = result.success ? CHECK_ICON : FAIL_ICON;
  const duration = formatDuration(result.duration);
  const durationStr = result.duration > 0 ? chalk.gray(duration.padStart(8)) : chalk.gray('-'.padStart(8));

  console.log(`   ${icon} ${padRight(result.name, 22)}${durationStr}    ${result.message}`);

  if (!result.success && result.details && options.verbose) {
    console.log(chalk.gray(`     └─ ${result.details}`));
  }

  if (!result.success && result.suggestion) {
    console.log(chalk.yellow(`     └─ Suggestion: ${result.suggestion}`));
  }
}

export function printSummary(result: RunnerResult): void {
  console.log(chalk.gray('═'.repeat(47)));

  const total = result.passed + result.failed;
  const passedStr = chalk.green(`${result.passed}/${total} checks passed`);
  const totalTime = formatDuration(result.totalDuration);

  console.log(`   ${passedStr}${' '.repeat(20)}Total: ${totalTime}`);

  if (result.failed === 0) {
    console.log(chalk.green.bold(`\n   Status: HEALTHY ✓\n`));
  } else {
    console.log(chalk.red.bold(`\n   Status: UNHEALTHY ✗\n`));
  }
}

export function printJson(result: RunnerResult): void {
  const output = {
    status: result.failed === 0 ? 'healthy' : 'unhealthy',
    checks: result.results.map(r => ({
      name: r.name,
      success: r.success,
      duration_ms: Math.round(r.duration),
      message: r.message,
      ...(r.details && { details: r.details }),
      ...(r.suggestion && { suggestion: r.suggestion }),
    })),
    summary: {
      total: result.passed + result.failed,
      passed: result.passed,
      failed: result.failed,
      duration_ms: Math.round(result.totalDuration),
    },
  };

  console.log(JSON.stringify(output, null, 2));
}

export class Reporter {
  private options: ReporterOptions;

  constructor(options: ReporterOptions = {}) {
    this.options = options;
  }

  start(): void {
    if (!this.options.json) {
      printHeader();
    }
  }

  onCheckStart(name: string): void {
    if (!this.options.json) {
      printCheckStart(name);
    }
  }

  onCheckComplete(result: CheckResult): void {
    if (!this.options.json) {
      printCheckResult(result, this.options);
    }
  }

  finish(result: RunnerResult): void {
    if (this.options.json) {
      printJson(result);
    } else {
      printSummary(result);
    }
  }
}
