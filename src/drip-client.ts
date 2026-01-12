import { CheckContext } from './types.js';

// Mock Drip SDK client for demonstration
// Replace with actual @drip-sdk/node import when available
export class Drip {
  private apiKey: string;
  private apiUrl: string;

  constructor(options: { apiKey: string; apiUrl?: string }) {
    this.apiKey = options.apiKey;
    this.apiUrl = options.apiUrl || 'http://localhost:3001';
  }

  async ping(): Promise<{ ok: boolean; latency: number }> {
    const start = performance.now();
    const response = await fetch(`${this.apiUrl}/health`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    const latency = performance.now() - start;
    return { ok: response.ok, latency };
  }

  async createCustomer(data: { externalCustomerId: string; name?: string }): Promise<{ customerId: string }> {
    const response = await fetch(`${this.apiUrl}/customers`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to create customer', error.code, response.status);
    }
    return response.json();
  }

  async getCustomer(customerId: string): Promise<{ customerId: string; name?: string }> {
    const response = await fetch(`${this.apiUrl}/customers/${customerId}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to get customer', error.code, response.status);
    }
    return response.json();
  }

  async listCustomers(filter?: { limit?: number }): Promise<{ customers: Array<{ customerId: string }> }> {
    const params = new URLSearchParams();
    if (filter?.limit) params.set('limit', String(filter.limit));

    const response = await fetch(`${this.apiUrl}/customers?${params}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to list customers', error.code, response.status);
    }
    return response.json();
  }

  async deleteCustomer(customerId: string): Promise<void> {
    const response = await fetch(`${this.apiUrl}/customers/${customerId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    if (!response.ok && response.status !== 404) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to delete customer', error.code, response.status);
    }
  }

  async charge(data: {
    customerId: string;
    meter: string;
    quantity: number;
    idempotencyKey?: string;
  }): Promise<{ charge: { chargeId: string; amountUsdc: string; status: string }; isReplay?: boolean }> {
    const response = await fetch(`${this.apiUrl}/charges`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        ...(data.idempotencyKey && { 'Idempotency-Key': data.idempotencyKey }),
      },
      body: JSON.stringify({
        customerId: data.customerId,
        meter: data.meter,
        quantity: data.quantity,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to create charge', error.code, response.status);
    }
    return response.json();
  }

  async getCharge(chargeId: string): Promise<{ chargeId: string; status: string; amountUsdc: string }> {
    const response = await fetch(`${this.apiUrl}/charges/${chargeId}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to get charge', error.code, response.status);
    }
    return response.json();
  }

  async getBalance(customerId: string): Promise<{ balanceUsdc: string }> {
    const response = await fetch(`${this.apiUrl}/customers/${customerId}/balance`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to get balance', error.code, response.status);
    }
    return response.json();
  }

  createStreamMeter(options: { customerId: string; meter: string }): StreamMeter {
    return new StreamMeter(this, options);
  }

  async recordRun(data: {
    customerId: string;
    workflow: string;
    events: Array<{ eventType: string; description?: string; quantity?: number; units?: string }>;
    status: string;
  }): Promise<{ runId: string }> {
    const response = await fetch(`${this.apiUrl}/runs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to record run', error.code, response.status);
    }
    return response.json();
  }

  async getRun(runId: string): Promise<{ runId: string; events: Array<unknown>; status: string }> {
    const response = await fetch(`${this.apiUrl}/runs/${runId}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to get run', error.code, response.status);
    }
    return response.json();
  }

  static verifyWebhookSignature(
    payload: string,
    signature: string,
    secret: string
  ): boolean {
    // Simplified signature verification for demo
    // Real implementation would use HMAC-SHA256
    const crypto = globalThis.crypto;
    if (!crypto?.subtle) {
      // Fallback for environments without Web Crypto
      return signature.startsWith('sha256=');
    }
    return signature.startsWith('sha256=');
  }

  static async verifyWebhookSignatureAsync(
    payload: string,
    signature: string,
    secret: string
  ): Promise<boolean> {
    return Drip.verifyWebhookSignature(payload, signature, secret);
  }
}

export class StreamMeter {
  private drip: Drip;
  private customerId: string;
  private meter: string;
  private total: number = 0;

  constructor(drip: Drip, options: { customerId: string; meter: string }) {
    this.drip = drip;
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

  async flush(): Promise<{ charge?: { chargeId: string; amountUsdc: string } }> {
    if (this.total === 0) {
      return {};
    }
    const result = await this.drip.charge({
      customerId: this.customerId,
      meter: this.meter,
      quantity: this.total,
    });
    this.total = 0;
    return { charge: result.charge };
  }
}

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
