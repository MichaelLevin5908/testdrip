/**
 * Smoke Tests: TypeScript type inference from published .d.ts files.
 *
 * These validate that the emitted type declarations work correctly
 * when consumed via the package exports map. The SDK's internal typecheck
 * validates source; this validates the compiled output.
 */
import { describe, it, expectTypeOf } from 'vitest';
import {
  Drip,
  DripError,
  StreamMeter,
  type DripConfig,
  type Customer,
  type ChargeResult,
  type ChargeParams,
  type TrackUsageParams,
  type TrackUsageResult,
  type BalanceResult,
  type CreateCustomerParams,
  type ListCustomersResponse,
  type ChargeStatus,
  type WebhookEventType,
  type RunStatus,
  type RecordRunParams,
  type RecordRunResult,
  type WrapApiCallParams,
  type WrapApiCallResult,
  type CheckoutParams,
  type CheckoutResult,
  type Webhook,
  type CreateWebhookResponse,
  type RunTimeline,
  type RunDetails,
} from '@drip-sdk/node';

describe('Core type inference', () => {
  it('DripConfig has optional fields', () => {
    expectTypeOf<DripConfig>().toHaveProperty('apiKey');
    expectTypeOf<DripConfig>().toHaveProperty('baseUrl');
    expectTypeOf<DripConfig>().toHaveProperty('timeout');
    expectTypeOf<DripConfig>().toHaveProperty('resilience');
  });

  it('Drip.createCustomer accepts CreateCustomerParams and returns Customer', () => {
    type Params = Parameters<InstanceType<typeof Drip>['createCustomer']>[0];
    type Return = ReturnType<InstanceType<typeof Drip>['createCustomer']>;
    expectTypeOf<Params>().toMatchTypeOf<CreateCustomerParams>();
    expectTypeOf<Return>().toMatchTypeOf<Promise<Customer>>();
  });

  it('Drip.charge accepts ChargeParams and returns ChargeResult', () => {
    type Params = Parameters<InstanceType<typeof Drip>['charge']>[0];
    type Return = ReturnType<InstanceType<typeof Drip>['charge']>;
    expectTypeOf<Params>().toMatchTypeOf<ChargeParams>();
    expectTypeOf<Return>().toMatchTypeOf<Promise<ChargeResult>>();
  });

  it('Drip.trackUsage returns TrackUsageResult', () => {
    type Return = ReturnType<InstanceType<typeof Drip>['trackUsage']>;
    expectTypeOf<Return>().toMatchTypeOf<Promise<TrackUsageResult>>();
  });

  it('Drip.getBalance returns BalanceResult', () => {
    type Return = ReturnType<InstanceType<typeof Drip>['getBalance']>;
    expectTypeOf<Return>().toMatchTypeOf<Promise<BalanceResult>>();
  });

  it('Drip.recordRun returns RecordRunResult', () => {
    type Return = ReturnType<InstanceType<typeof Drip>['recordRun']>;
    expectTypeOf<Return>().toMatchTypeOf<Promise<RecordRunResult>>();
  });

  it('Drip.checkout returns CheckoutResult', () => {
    type Return = ReturnType<InstanceType<typeof Drip>['checkout']>;
    expectTypeOf<Return>().toMatchTypeOf<Promise<CheckoutResult>>();
  });

  it('DripError has statusCode and code properties', () => {
    expectTypeOf<DripError>().toHaveProperty('statusCode');
    expectTypeOf<DripError>().toHaveProperty('code');
    expectTypeOf<DripError>().toHaveProperty('message');
  });

  it('ChargeResult has correct shape', () => {
    expectTypeOf<ChargeResult>().toHaveProperty('success');
    expectTypeOf<ChargeResult>().toHaveProperty('usageEventId');
    expectTypeOf<ChargeResult>().toHaveProperty('isDuplicate');
    expectTypeOf<ChargeResult>().toHaveProperty('charge');
  });

  it('Customer has correct fields', () => {
    expectTypeOf<Customer>().toHaveProperty('id');
    expectTypeOf<Customer>().toHaveProperty('externalCustomerId');
    expectTypeOf<Customer>().toHaveProperty('onchainAddress');
    expectTypeOf<Customer>().toHaveProperty('isInternal');
    expectTypeOf<Customer>().toHaveProperty('status');
  });

  it('ChargeStatus is a string union', () => {
    expectTypeOf<ChargeStatus>().toBeString();
  });

  it('WebhookEventType is a string union', () => {
    expectTypeOf<WebhookEventType>().toBeString();
  });

  it('RunStatus is a string union', () => {
    expectTypeOf<RunStatus>().toBeString();
  });

  it('WrapApiCallParams generic T flows through', () => {
    type Params = WrapApiCallParams<{ tokens: number }>;
    expectTypeOf<Params>().toHaveProperty('call');
    expectTypeOf<Params>().toHaveProperty('extractUsage');
  });

  it('WrapApiCallResult generic T flows through', () => {
    type Result = WrapApiCallResult<{ tokens: number }>;
    expectTypeOf<Result>().toHaveProperty('result');
    expectTypeOf<Result>().toHaveProperty('charge');
    expectTypeOf<Result>().toHaveProperty('idempotencyKey');
  });
});

describe('Webhook type inference', () => {
  it('Webhook has expected fields', () => {
    expectTypeOf<Webhook>().toHaveProperty('id');
    expectTypeOf<Webhook>().toHaveProperty('url');
    expectTypeOf<Webhook>().toHaveProperty('events');
    expectTypeOf<Webhook>().toHaveProperty('isActive');
    expectTypeOf<Webhook>().toHaveProperty('healthStatus');
  });

  it('CreateWebhookResponse extends Webhook with secret', () => {
    expectTypeOf<CreateWebhookResponse>().toHaveProperty('secret');
    expectTypeOf<CreateWebhookResponse>().toHaveProperty('id');
    expectTypeOf<CreateWebhookResponse>().toHaveProperty('url');
  });
});

describe('Run type inference', () => {
  it('RunTimeline has events and summary', () => {
    expectTypeOf<RunTimeline>().toHaveProperty('events');
    expectTypeOf<RunTimeline>().toHaveProperty('summary');
    expectTypeOf<RunTimeline>().toHaveProperty('anomalies');
  });

  it('RunDetails has totals and links', () => {
    expectTypeOf<RunDetails>().toHaveProperty('totals');
    expectTypeOf<RunDetails>().toHaveProperty('_links');
  });
});
