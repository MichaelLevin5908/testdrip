// Use the real Drip SDK from npm
import { Drip as RealDrip, DripError as RealDripError } from '@drip-sdk/node';
import type { ChargeResult, Customer, BalanceResult, Charge, ListChargesResponse, ListCustomersResponse } from '@drip-sdk/node';
import { CheckContext } from './types.js';

// Re-export the real SDK classes
export { RealDrip as DripSDK, RealDripError };

// Wrapper class that adapts the real SDK to our health check interface
export class Drip {
  private sdk: RealDrip;
  private baseUrl: string;
  private apiKey: string;

  constructor(options: { apiKey: string; apiUrl?: string }) {
    this.apiKey = options.apiKey;
    // The SDK expects baseUrl to include /v1
    const rawUrl = options.apiUrl || 'https://drip-app-hlunj.ondigitalocean.app';
    this.baseUrl = rawUrl.endsWith('/v1') ? rawUrl : `${rawUrl}/v1`;
    this.sdk = new RealDrip({
      apiKey: options.apiKey,
      baseUrl: this.baseUrl,
    });
  }

  // Ping endpoint (not in SDK, so we do it manually)
  async ping(): Promise<{ ok: boolean; latency: number }> {
    const start = performance.now();
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        headers: { 'x-api-key': this.apiKey },
      });
      const latency = performance.now() - start;
      return { ok: response.ok, latency };
    } catch {
      const latency = performance.now() - start;
      return { ok: false, latency };
    }
  }

  // Customer endpoints - use SDK
  async createCustomer(data: { externalCustomerId?: string; onchainAddress?: string; name?: string }): Promise<Customer> {
    // SDK requires onchainAddress (42 chars: 0x + 40 hex chars), generate one if not provided
    const onchainAddress = data.onchainAddress ||
      `0x${Date.now().toString(16).padStart(12, '0')}${Math.random().toString(16).slice(2).padEnd(28, '0')}`.slice(0, 42);
    return this.sdk.createCustomer({
      externalCustomerId: data.externalCustomerId,
      onchainAddress,
    });
  }

  async getCustomer(customerId: string): Promise<Customer> {
    return this.sdk.getCustomer(customerId);
  }

  async listCustomers(filter?: { limit?: number }): Promise<ListCustomersResponse> {
    return this.sdk.listCustomers({ limit: filter?.limit });
  }

  async deleteCustomer(_customerId: string): Promise<void> {
    // SDK doesn't have deleteCustomer, make direct API call
    const response = await fetch(`${this.baseUrl}/customers/${_customerId}`, {
      method: 'DELETE',
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok && response.status !== 404) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to delete customer', error.code, response.status);
    }
  }

  async getBalance(customerId: string): Promise<BalanceResult> {
    return this.sdk.getBalance(customerId);
  }

  // Charge endpoint - use SDK
  async charge(data: {
    customerId: string;
    meter: string;
    quantity: number;
    idempotencyKey?: string;
  }): Promise<ChargeResult> {
    return this.sdk.charge({
      customerId: data.customerId,
      meter: data.meter,
      quantity: data.quantity,
      idempotencyKey: data.idempotencyKey,
    });
  }

  // List charges - use SDK
  async listCharges(filter?: { limit?: number; status?: string; customerId?: string }): Promise<ListChargesResponse> {
    return this.sdk.listCharges({
      limit: filter?.limit,
      customerId: filter?.customerId,
      status: filter?.status as 'PENDING' | 'SUBMITTED' | 'CONFIRMED' | 'FAILED' | 'REFUNDED' | undefined,
    });
  }

  async getCharge(chargeId: string): Promise<Charge> {
    return this.sdk.getCharge(chargeId);
  }

  async getChargeStatus(chargeId: string): Promise<{ status: string; txHash?: string }> {
    return this.sdk.getChargeStatus(chargeId);
  }

  // Webhook endpoints - use SDK
  async listWebhooks() {
    return this.sdk.listWebhooks();
  }

  // Runs - use SDK's recordRun
  async recordRun(data: {
    customerId: string;
    workflow: string;
    events: Array<{ eventType: string; description?: string; quantity?: number; units?: string }>;
    status: 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'TIMEOUT';
  }) {
    return this.sdk.recordRun({
      customerId: data.customerId,
      workflow: data.workflow,
      events: data.events,
      status: data.status,
    });
  }

  async getRunTimeline(runId: string) {
    return this.sdk.getRunTimeline(runId);
  }

  // Static methods
  static verifyWebhookSignature(payload: string, signature: string, secret: string): boolean {
    return RealDrip.verifyWebhookSignature(payload, signature, secret);
  }

  // StreamMeter factory
  createStreamMeter(options: { customerId: string; meter: string }): StreamMeter {
    return new StreamMeter(this.sdk, options);
  }
}

// StreamMeter that uses the real SDK
export class StreamMeter {
  private sdk: RealDrip;
  private customerId: string;
  private meter: string;
  private total: number = 0;

  constructor(sdk: RealDrip, options: { customerId: string; meter: string }) {
    this.sdk = sdk;
    this.customerId = options.customerId;
    this.meter = options.meter;
  }

  addSync(quantity: number): void {
    this.total += quantity;
  }

  async add(quantity: number): Promise<void> {
    this.total += quantity;
  }

  getTotal(): number {
    return this.total;
  }

  async flush(): Promise<ChargeResult | { charge: undefined }> {
    if (this.total === 0) {
      return { charge: undefined } as { charge: undefined };
    }
    const result = await this.sdk.charge({
      customerId: this.customerId,
      meter: this.meter,
      quantity: this.total,
    });
    this.total = 0;
    return result;
  }
}

// Re-export DripError for backwards compatibility
export class DripError extends Error {
  code?: string;
  statusCode: number;

  constructor(message: string, code?: string, statusCode: number = 500) {
    super(message);
    this.name = 'DripError';
    this.code = code;
    this.statusCode = statusCode;
  }
}

export function createClient(ctx: CheckContext): Drip {
  return new Drip({
    apiKey: ctx.apiKey,
    apiUrl: ctx.apiUrl,
  });
}
