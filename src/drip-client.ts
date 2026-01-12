import { CheckContext } from './types.js';

// Drip SDK client matching the actual API
export class Drip {
  private apiKey: string;
  private apiUrl: string;

  constructor(options: { apiKey: string; apiUrl?: string }) {
    this.apiKey = options.apiKey;
    this.apiUrl = options.apiUrl || 'https://drip-app-hlunj.ondigitalocean.app';
  }

  private getHeaders(extraHeaders?: Record<string, string>): Record<string, string> {
    return {
      'x-api-key': this.apiKey,
      'Content-Type': 'application/json',
      ...extraHeaders,
    };
  }

  async ping(): Promise<{ ok: boolean; latency: number }> {
    const start = performance.now();
    const response = await fetch(`${this.apiUrl}/health`, {
      headers: { 'x-api-key': this.apiKey },
    });
    const latency = performance.now() - start;
    return { ok: response.ok, latency };
  }

  // Customer endpoints
  async createCustomer(data: { externalCustomerId: string; name?: string }): Promise<{ id: string }> {
    const response = await fetch(`${this.apiUrl}/v1/customers`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to create customer', error.code, response.status);
    }
    return response.json() as Promise<{ id: string }>;
  }

  async getCustomer(customerId: string): Promise<{ id: string; externalCustomerId?: string }> {
    const response = await fetch(`${this.apiUrl}/v1/customers/${customerId}`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to get customer', error.code, response.status);
    }
    return response.json() as Promise<{ id: string; externalCustomerId?: string }>;
  }

  async listCustomers(filter?: { limit?: number }): Promise<{ data: Array<{ id: string }>; count: number }> {
    const params = new URLSearchParams();
    if (filter?.limit) params.set('limit', String(filter.limit));

    const response = await fetch(`${this.apiUrl}/v1/customers?${params}`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to list customers', error.code, response.status);
    }
    return response.json() as Promise<{ data: Array<{ id: string }>; count: number }>;
  }

  async deleteCustomer(customerId: string): Promise<void> {
    const response = await fetch(`${this.apiUrl}/v1/customers/${customerId}`, {
      method: 'DELETE',
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok && response.status !== 404) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to delete customer', error.code, response.status);
    }
  }

  async getBalance(customerId: string): Promise<{ balance: string; currency: string }> {
    const response = await fetch(`${this.apiUrl}/v1/customers/${customerId}/balance`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to get balance', error.code, response.status);
    }
    return response.json() as Promise<{ balance: string; currency: string }>;
  }

  // Usage endpoints - this creates charges
  async recordUsage(data: {
    customerId: string;
    usageType: string;
    quantity: number;
    units?: string;
    idempotencyKey?: string;
  }): Promise<{ usageEventId: string; charge?: { id: string; amountUsdc: string; status: string }; isDuplicate?: boolean }> {
    const headers = this.getHeaders();
    if (data.idempotencyKey) {
      headers['Idempotency-Key'] = data.idempotencyKey;
    }

    const response = await fetch(`${this.apiUrl}/v1/usage`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        customerId: data.customerId,
        usageType: data.usageType,
        quantity: data.quantity,
        units: data.units || 'units',
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to record usage', error.code, response.status);
    }
    return response.json() as Promise<{ usageEventId: string; charge?: { id: string; amountUsdc: string; status: string }; isDuplicate?: boolean }>;
  }

  // Charge endpoints
  async listCharges(filter?: { limit?: number; status?: string; customerId?: string }): Promise<{ data: Array<{ id: string; status: string; amountUsdc: string }>; count: number }> {
    const params = new URLSearchParams();
    if (filter?.limit) params.set('limit', String(filter.limit));
    if (filter?.status) params.set('status', filter.status);
    if (filter?.customerId) params.set('customerId', filter.customerId);

    const response = await fetch(`${this.apiUrl}/v1/charges?${params}`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to list charges', error.code, response.status);
    }
    return response.json() as Promise<{ data: Array<{ id: string; status: string; amountUsdc: string }>; count: number }>;
  }

  async getCharge(chargeId: string): Promise<{ id: string; status: string; amountUsdc: string; customerId: string }> {
    const response = await fetch(`${this.apiUrl}/v1/charges/${chargeId}`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to get charge', error.code, response.status);
    }
    return response.json() as Promise<{ id: string; status: string; amountUsdc: string; customerId: string }>;
  }

  async getChargeStatus(chargeId: string): Promise<{ id: string; status: string; txHash?: string }> {
    const response = await fetch(`${this.apiUrl}/v1/charges/${chargeId}/status`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to get charge status', error.code, response.status);
    }
    return response.json() as Promise<{ id: string; status: string; txHash?: string }>;
  }

  // Webhook endpoints
  async listWebhooks(): Promise<{ data: Array<{ id: string; url: string; events: string[] }> }> {
    const response = await fetch(`${this.apiUrl}/v1/webhooks`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to list webhooks', error.code, response.status);
    }
    return response.json() as Promise<{ data: Array<{ id: string; url: string; events: string[] }> }>;
  }

  async getWebhookEvents(): Promise<{ events: string[] }> {
    const response = await fetch(`${this.apiUrl}/v1/webhooks/events`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to get webhook events', error.code, response.status);
    }
    return response.json() as Promise<{ events: string[] }>;
  }

  // Charge method - uses /v1/usage endpoint
  async charge(data: {
    customerId: string;
    usageType: string;
    quantity: number;
    units?: string;
    idempotencyKey?: string;
  }): Promise<{ charge: { chargeId: string; amountUsdc: string; status: string }; isReplay?: boolean }> {
    const result = await this.recordUsage({
      customerId: data.customerId,
      usageType: data.usageType,
      quantity: data.quantity,
      units: data.units,
      idempotencyKey: data.idempotencyKey,
    });
    return {
      charge: {
        chargeId: result.charge?.id || result.usageEventId,
        amountUsdc: result.charge?.amountUsdc || '0',
        status: result.charge?.status || 'PENDING',
      },
      isReplay: result.isDuplicate,
    };
  }

  createStreamMeter(options: { customerId: string; usageType: string; units?: string }): StreamMeter {
    return new StreamMeter(this, options);
  }

  // Runs/workflow endpoints (if they exist)
  async recordRun(data: {
    customerId: string;
    workflow: string;
    events: Array<{ eventType: string; description?: string; quantity?: number; units?: string }>;
    status: string;
  }): Promise<{ runId: string }> {
    const response = await fetch(`${this.apiUrl}/v1/runs`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to record run', error.code, response.status);
    }
    return response.json() as Promise<{ runId: string }>;
  }

  async getRun(runId: string): Promise<{ runId: string; events: Array<unknown>; status: string }> {
    const response = await fetch(`${this.apiUrl}/v1/runs/${runId}`, {
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as Record<string, string>;
      throw new DripError(error.message || 'Failed to get run', error.code, response.status);
    }
    return response.json() as Promise<{ runId: string; events: Array<unknown>; status: string }>;
  }

  static verifyWebhookSignature(
    _payload: string,
    signature: string,
    _secret: string
  ): boolean {
    // Simplified signature verification for demo
    // Real implementation would use HMAC-SHA256
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
  private usageType: string;
  private units: string;
  private total: number = 0;

  constructor(drip: Drip, options: { customerId: string; usageType: string; units?: string }) {
    this.drip = drip;
    this.customerId = options.customerId;
    this.usageType = options.usageType;
    this.units = options.units || 'units';
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
    const result = await this.drip.recordUsage({
      customerId: this.customerId,
      usageType: this.usageType,
      quantity: this.total,
      units: this.units,
    });
    this.total = 0;
    return {
      charge: result.charge
        ? { chargeId: result.charge.id, amountUsdc: result.charge.amountUsdc }
        : undefined
    };
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
