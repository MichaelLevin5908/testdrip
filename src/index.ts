#!/usr/bin/env node

import { Command } from 'commander';
import { config } from 'dotenv';
import { loadConfig } from './config.js';
import { allChecks, quickChecks, getChecksByName } from './checks/index.js';
import { runChecks } from './runner.js';
import { Reporter } from './reporter.js';
import { CheckContext } from './types.js';

// Load environment variables
config();

const program = new Command();

program
  .name('drip-health')
  .description('CLI tool that validates the Drip backend is functioning correctly')
  .version('1.0.0');

program
  .command('check')
  .description('Run health checks against the Drip backend')
  .option('--only <checks>', 'Run specific checks (comma-separated)')
  .option('--quick', 'Run only quick checks (connectivity, auth, webhooks)')
  .option('--verbose', 'Show detailed output with request/response info')
  .option('--json', 'Output results as JSON')
  .option('--env <environment>', 'Check against specific environment')
  .option('--no-cleanup', 'Skip cleanup of test data')
  .action(async (options) => {
    try {
      const dripConfig = loadConfig();

      // Determine which checks to run
      let checksToRun = allChecks;

      if (options.quick) {
        checksToRun = quickChecks;
      } else if (options.only) {
        const checkNames = options.only.split(',').map((s: string) => s.trim());
        checksToRun = getChecksByName(checkNames);

        if (checksToRun.length === 0) {
          console.error(`No checks found matching: ${options.only}`);
          console.error('Available checks:', allChecks.map(c => c.name).join(', '));
          process.exit(2);
        }
      }

      // Create context
      const context: CheckContext = {
        apiKey: dripConfig.apiKey,
        apiUrl: dripConfig.apiUrl,
        testCustomerId: dripConfig.testCustomerId,
        skipCleanup: options.cleanup === false || dripConfig.skipCleanup,
        timeout: dripConfig.timeout,
      };

      // Create reporter
      const reporter = new Reporter({
        verbose: options.verbose,
        json: options.json,
      });

      reporter.start();

      // Run checks
      const result = await runChecks({
        checks: checksToRun,
        context,
        onCheckStart: (check) => reporter.onCheckStart(check.name),
        onCheckComplete: (_, checkResult) => reporter.onCheckComplete(checkResult),
      });

      reporter.finish(result);

      // Exit with appropriate code
      process.exit(result.failed > 0 ? 1 : 0);
    } catch (error) {
      if (error instanceof Error) {
        console.error(`Error: ${error.message}`);
      } else {
        console.error('An unknown error occurred');
      }
      process.exit(2);
    }
  });

// Default command is check
program
  .action(() => {
    program.commands.find(cmd => cmd.name() === 'check')?.parse(process.argv);
  });

program.parse();
