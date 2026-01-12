// Use the real Drip SDK from npm
import { Drip as RealDrip, DripError as RealDripError } from '@drip-sdk/node';
import type { ChargeResult, Customer, BalanceResult } from '@drip-sdk/node';

// Re-export the real SDK
export { RealDrip as DripSDK, RealDripError };

// Wrapper class for load testing
export class Drip {
  private sdk: RealDrip;

  constructor(options: { apiKey: string; apiUrl?: string }) {
    this.sdk = new RealDrip({
      apiKey: options.apiKey,
      baseUrl: options.apiUrl || 'https://drip-app-hlunj.ondigitalocean.app',
    });
  }

  async createCustomer(data: { externalCustomerId?: string; onchainAddress?: string; name?: string }): Promise<Customer> {
    const onchainAddress = data.onchainAddress || `0x${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`.slice(0, 42);
    return this.sdk.createCustomer({
      externalCustomerId: data.externalCustomerId,
      onchainAddress,
    });
  }

  async getCustomer(customerId: string): Promise<Customer> {
    return this.sdk.getCustomer(customerId);
  }

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

  async getBalance(customerId: string): Promise<BalanceResult> {
    return this.sdk.getBalance(customerId);
  }

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
