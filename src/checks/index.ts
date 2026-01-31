import { Check } from '../types.js';
import { connectivityCheck, authenticationCheck } from './connectivity.js';
import { customerCreateCheck, customerGetCheck, customerListCheck, customerCleanupCheck } from './customer.js';
import { chargeCreateCheck, chargeStatusCheck, getChargeCheck, listChargesFilteredCheck } from './charge.js';
import { balanceGetCheck } from './balance.js';
import { streamMeterAddCheck, streamMeterFlushCheck } from './streaming.js';
import { idempotencyCheck } from './idempotency.js';
import { webhookSignCheck, webhookVerifyCheck } from './webhooks.js';
import { webhookCreateCheck, webhookListCheck, webhookGetCheck, webhookTestCheck, webhookRotateSecretCheck, webhookDeleteCheck } from './webhooks-crud.js';
import { runCreateCheck, runTimelineCheck, runEndCheck, emitEventCheck, emitEventsBatchCheck, recordRunCheck } from './runs.js';
import { trackUsageCheck } from './usage.js';
import { wrapApiCallBasicCheck, wrapApiCallIdempotencyCheck, wrapApiCallErrorHandlingCheck } from './wrapApiCall.js';
import { checkoutCreateCheck } from './checkout.js';
import { workflowCreateCheck, workflowListCheck } from './workflows.js';
import { listMetersCheck } from './meters.js';
import { estimateFromUsageCheck, estimateFromHypotheticalCheck } from './estimates.js';
import { getMetricsCheck, getHealthCheck } from './resilience.js';
import { generateIdempotencyKeyCheck, createStreamMeterCheck } from './utilities.js';

export const allChecks: Check[] = [
  // Connectivity & auth
  connectivityCheck,
  authenticationCheck,

  // Customer operations
  customerCreateCheck,
  customerGetCheck,
  customerListCheck,

  // Charge operations
  chargeCreateCheck,
  chargeStatusCheck,
  getChargeCheck,
  listChargesFilteredCheck,

  // Usage tracking
  trackUsageCheck,
  balanceGetCheck,

  // Streaming
  streamMeterAddCheck,
  streamMeterFlushCheck,

  // Idempotency
  idempotencyCheck,

  // API wrapping
  wrapApiCallBasicCheck,
  wrapApiCallIdempotencyCheck,
  wrapApiCallErrorHandlingCheck,

  // Checkout
  checkoutCreateCheck,

  // Webhook signature (quick checks)
  webhookSignCheck,
  webhookVerifyCheck,

  // Webhooks CRUD
  webhookCreateCheck,
  webhookListCheck,
  webhookGetCheck,
  webhookTestCheck,
  webhookRotateSecretCheck,
  webhookDeleteCheck,

  // Workflows
  workflowCreateCheck,
  workflowListCheck,

  // Runs
  runCreateCheck,
  runTimelineCheck,
  runEndCheck,
  emitEventCheck,
  emitEventsBatchCheck,
  recordRunCheck,

  // Meters
  listMetersCheck,

  // Estimates
  estimateFromUsageCheck,
  estimateFromHypotheticalCheck,

  // Resilience
  getMetricsCheck,
  getHealthCheck,

  // Utilities
  generateIdempotencyKeyCheck,
  createStreamMeterCheck,

  // Cleanup (always last)
  customerCleanupCheck,
];

export const quickChecks: Check[] = allChecks.filter(check => check.quick);

export function getChecksByName(names: string[]): Check[] {
  const lowerNames = names.map(n => n.toLowerCase());
  return allChecks.filter(check =>
    lowerNames.includes(check.name.toLowerCase()) ||
    lowerNames.some(n => check.name.toLowerCase().includes(n))
  );
}
