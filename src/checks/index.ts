import { Check } from '../types.js';
import { connectivityCheck, authenticationCheck } from './connectivity.js';
import { customerCreateCheck, customerGetCheck, customerListCheck, customerCleanupCheck } from './customer.js';
import { chargeCreateCheck, chargeStatusCheck } from './charge.js';
import { balanceGetCheck } from './balance.js';
import { streamMeterAddCheck, streamMeterFlushCheck } from './streaming.js';
import { idempotencyCheck } from './idempotency.js';
import { webhookSignCheck, webhookVerifyCheck } from './webhooks.js';
import { runCreateCheck, runTimelineCheck } from './runs.js';
import { trackUsageCheck } from './usage.js';
import { wrapApiCallBasicCheck, wrapApiCallIdempotencyCheck, wrapApiCallErrorHandlingCheck } from './wrapApiCall.js';

export const allChecks: Check[] = [
  connectivityCheck,
  authenticationCheck,
  customerCreateCheck,
  customerGetCheck,
  customerListCheck,
  chargeCreateCheck,
  chargeStatusCheck,
  trackUsageCheck,
  balanceGetCheck,
  streamMeterAddCheck,
  streamMeterFlushCheck,
  idempotencyCheck,
  wrapApiCallBasicCheck,
  wrapApiCallIdempotencyCheck,
  wrapApiCallErrorHandlingCheck,
  webhookSignCheck,
  webhookVerifyCheck,
  runCreateCheck,
  runTimelineCheck,
  customerCleanupCheck, // Always run cleanup last
];

export const quickChecks: Check[] = allChecks.filter(check => check.quick);

export function getChecksByName(names: string[]): Check[] {
  const lowerNames = names.map(n => n.toLowerCase());
  return allChecks.filter(check =>
    lowerNames.includes(check.name.toLowerCase()) ||
    lowerNames.some(n => check.name.toLowerCase().includes(n))
  );
}
