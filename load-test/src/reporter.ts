import chalk from 'chalk';
import { ScenarioResult, LatencyStats } from './types.js';
import { calculateLatencyStats } from './metrics.js';

export interface ReporterOptions {
  format: 'pretty' | 'json' | 'csv';
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatLatency(ms: number): string {
  return Math.round(ms).toString();
}

export function printResults(result: ScenarioResult, options: ReporterOptions = { format: 'pretty' }): void {
  switch (options.format) {
    case 'json':
      printJson(result);
      break;
    case 'csv':
      printCsv(result);
      break;
    default:
      printPretty(result);
  }
}

function printPretty(result: ScenarioResult): void {
  const stats = calculateLatencyStats(result.latencies);
  const successRate = result.totalRequests > 0
    ? ((result.succeeded / result.totalRequests) * 100).toFixed(1)
    : '0';
  const throughput = result.duration > 0
    ? (result.totalRequests / (result.duration / 1000)).toFixed(1)
    : '0';

  console.log('');
  console.log(chalk.bold('Drip Load Test Results'));
  console.log(chalk.gray('══════════════════════════════════════'));
  console.log(`${chalk.cyan('Scenario:')}      ${result.scenario}`);
  console.log(`${chalk.cyan('Duration:')}      ${formatDuration(result.duration)}`);
  console.log('');

  console.log(chalk.bold('Requests:'));
  console.log(`  Total:        ${result.totalRequests}`);
  console.log(`  Succeeded:    ${chalk.green(result.succeeded)} (${successRate}%)`);
  console.log(`  Failed:       ${chalk.red(result.failed)} (${(100 - parseFloat(successRate)).toFixed(1)}%)`);
  console.log('');

  if (result.latencies.length > 0) {
    console.log(chalk.bold('Latency (ms):'));
    console.log(`  Min:          ${formatLatency(stats.min)}`);
    console.log(`  Max:          ${formatLatency(stats.max)}`);
    console.log(`  Avg:          ${formatLatency(stats.avg)}`);
    console.log(`  p50:          ${formatLatency(stats.p50)}`);
    console.log(`  p95:          ${formatLatency(stats.p95)}`);
    console.log(`  p99:          ${formatLatency(stats.p99)}`);
    console.log('');
  }

  if (result.errors.size > 0) {
    console.log(chalk.bold('Errors:'));
    for (const [code, count] of result.errors) {
      console.log(`  ${chalk.red(code)}:  ${count}`);
    }
    console.log('');
  }

  console.log(`${chalk.cyan('Throughput:')}   ${chalk.bold(throughput)} req/s`);
  console.log(chalk.gray('══════════════════════════════════════'));
  console.log('');
}

function printJson(result: ScenarioResult): void {
  const stats = calculateLatencyStats(result.latencies);
  const output = {
    scenario: result.scenario,
    duration_ms: Math.round(result.duration),
    requests: {
      total: result.totalRequests,
      succeeded: result.succeeded,
      failed: result.failed,
      success_rate: result.totalRequests > 0
        ? (result.succeeded / result.totalRequests) * 100
        : 0,
    },
    latency_ms: {
      min: Math.round(stats.min),
      max: Math.round(stats.max),
      avg: Math.round(stats.avg),
      p50: Math.round(stats.p50),
      p95: Math.round(stats.p95),
      p99: Math.round(stats.p99),
    },
    errors: Object.fromEntries(result.errors),
    throughput_rps: result.duration > 0
      ? result.totalRequests / (result.duration / 1000)
      : 0,
  };

  console.log(JSON.stringify(output, null, 2));
}

function printCsv(result: ScenarioResult): void {
  const stats = calculateLatencyStats(result.latencies);
  const throughput = result.duration > 0
    ? (result.totalRequests / (result.duration / 1000)).toFixed(2)
    : '0';

  // Header
  console.log('scenario,duration_ms,total,succeeded,failed,success_rate,min_ms,max_ms,avg_ms,p50_ms,p95_ms,p99_ms,throughput_rps');

  // Data
  console.log([
    result.scenario,
    Math.round(result.duration),
    result.totalRequests,
    result.succeeded,
    result.failed,
    result.totalRequests > 0
      ? ((result.succeeded / result.totalRequests) * 100).toFixed(2)
      : '0',
    Math.round(stats.min),
    Math.round(stats.max),
    Math.round(stats.avg),
    Math.round(stats.p50),
    Math.round(stats.p95),
    Math.round(stats.p99),
    throughput,
  ].join(','));
}
