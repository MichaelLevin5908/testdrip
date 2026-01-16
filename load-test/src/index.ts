#!/usr/bin/env node

import { Command } from 'commander';
import { config } from 'dotenv';
import { loadConfig } from './config.js';
import { runChargeBurst, runStreaming, runCustomerCreate, runMixedWorkload } from './scenarios/index.js';
import { printResults, ReporterOptions } from './reporter.js';
import { ScenarioConfig } from './types.js';

// Load environment variables
config();

const program = new Command();

program
  .name('drip-load')
  .description('CLI load testing tool for Drip billing backend')
  .version('1.0.0');

program
  .command('charge')
  .description('Run charge burst test - fire N concurrent charges')
  .option('-c, --concurrency <number>', 'Number of concurrent requests', '50')
  .option('-t, --total <number>', 'Total number of requests', '1000')
  .option('--customer <id>', 'Customer ID to charge')
  .option('--meter <name>', 'Meter/usage type to charge (default: api_call)', 'api_call')
  .option('--idempotency', 'Use idempotency keys')
  .option('--warmup <number>', 'Warmup requests before measuring', '0')
  .option('-o, --output <format>', 'Output format: pretty, json, csv', 'pretty')
  .action(async (options) => {
    try {
      const cfg = loadConfig();
      const customerId = options.customer || cfg.defaultCustomerId;

      if (!customerId) {
        console.error('Error: Customer ID required. Use --customer or set DEFAULT_CUSTOMER_ID');
        process.exit(2);
      }

      const scenarioConfig: ScenarioConfig = {
        apiKey: cfg.apiKey,
        apiUrl: cfg.apiUrl,
        customerId,
        concurrency: parseInt(options.concurrency, 10),
        total: parseInt(options.total, 10),
        useIdempotency: options.idempotency,
        warmup: parseInt(options.warmup, 10),
        meter: options.meter,
      };

      console.log(`Running charge burst: ${scenarioConfig.total} requests @ ${scenarioConfig.concurrency} concurrency`);

      const result = await runChargeBurst(scenarioConfig);
      printResults(result, { format: options.output as ReporterOptions['format'] });

      process.exit(result.failed > 0 ? 1 : 0);
    } catch (error) {
      console.error(`Error: ${(error as Error).message}`);
      process.exit(2);
    }
  });

program
  .command('stream')
  .description('Run streaming meter test - multiple concurrent StreamMeters')
  .option('-c, --concurrency <number>', 'Number of concurrent streams', '20')
  .option('-e, --events <number>', 'Events per stream', '100')
  .option('--customer <id>', 'Customer ID')
  .option('--meter <name>', 'Meter/usage type to charge (default: api_call)', 'api_call')
  .option('-o, --output <format>', 'Output format: pretty, json, csv', 'pretty')
  .action(async (options) => {
    try {
      const cfg = loadConfig();
      const customerId = options.customer || cfg.defaultCustomerId;

      if (!customerId) {
        console.error('Error: Customer ID required. Use --customer or set DEFAULT_CUSTOMER_ID');
        process.exit(2);
      }

      const scenarioConfig: ScenarioConfig = {
        apiKey: cfg.apiKey,
        apiUrl: cfg.apiUrl,
        customerId,
        concurrency: parseInt(options.concurrency, 10),
        total: parseInt(options.events, 10),
        meter: options.meter,
      };

      console.log(`Running streaming test: ${scenarioConfig.concurrency} streams @ ${scenarioConfig.total} events each`);

      const result = await runStreaming(scenarioConfig);
      printResults(result, { format: options.output as ReporterOptions['format'] });

      process.exit(result.failed > 0 ? 1 : 0);
    } catch (error) {
      console.error(`Error: ${(error as Error).message}`);
      process.exit(2);
    }
  });

program
  .command('customers')
  .description('Run bulk customer creation test')
  .option('-c, --concurrency <number>', 'Number of concurrent requests', '20')
  .option('-t, --total <number>', 'Total customers to create', '100')
  .option('--test-duplicates', 'Test duplicate handling')
  .option('-o, --output <format>', 'Output format: pretty, json, csv', 'pretty')
  .action(async (options) => {
    try {
      const cfg = loadConfig();

      const scenarioConfig: ScenarioConfig = {
        apiKey: cfg.apiKey,
        apiUrl: cfg.apiUrl,
        customerId: '', // Not used for customer creation
        concurrency: parseInt(options.concurrency, 10),
        total: parseInt(options.total, 10),
        useIdempotency: options.testDuplicates,
      };

      console.log(`Running customer creation: ${scenarioConfig.total} customers @ ${scenarioConfig.concurrency} concurrency`);

      const result = await runCustomerCreate(scenarioConfig);
      printResults(result, { format: options.output as ReporterOptions['format'] });

      process.exit(result.failed > 0 ? 1 : 0);
    } catch (error) {
      console.error(`Error: ${(error as Error).message}`);
      process.exit(2);
    }
  });

program
  .command('mixed')
  .description('Run mixed workload - simulate realistic traffic')
  .option('-d, --duration <seconds>', 'Test duration in seconds', '60')
  .option('-r, --rps <number>', 'Requests per second', '100')
  .option('--customer <id>', 'Customer ID')
  .option('--meter <name>', 'Meter/usage type to charge (default: api_call)', 'api_call')
  .option('-o, --output <format>', 'Output format: pretty, json, csv', 'pretty')
  .action(async (options) => {
    try {
      const cfg = loadConfig();
      const customerId = options.customer || cfg.defaultCustomerId;

      if (!customerId) {
        console.error('Error: Customer ID required. Use --customer or set DEFAULT_CUSTOMER_ID');
        process.exit(2);
      }

      const scenarioConfig: ScenarioConfig = {
        apiKey: cfg.apiKey,
        apiUrl: cfg.apiUrl,
        customerId,
        concurrency: 1, // Not used for rate-limited test
        total: 0, // Not used
        duration: parseInt(options.duration, 10),
        rps: parseInt(options.rps, 10),
        meter: options.meter,
      };

      console.log(`Running mixed workload: ${scenarioConfig.duration}s @ ${scenarioConfig.rps} RPS`);
      console.log('Distribution: 70% charges, 20% balance, 10% customer ops');

      const result = await runMixedWorkload(scenarioConfig);
      printResults(result, { format: options.output as ReporterOptions['format'] });

      process.exit(result.failed > 0 ? 1 : 0);
    } catch (error) {
      console.error(`Error: ${(error as Error).message}`);
      process.exit(2);
    }
  });

program.parse();
