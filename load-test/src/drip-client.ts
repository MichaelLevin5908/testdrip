// Mock Drip SDK client for load testing
// Replace with actual @drip-sdk/node import when available

export class Drip {
  private apiKey: string;
  private apiUrl: string;

  constructor(options: { apiKey: string; apiUrl?: string }) {
    this.apiKey = options.apiKey;
    this.apiUrl = options.apiUrl || 'https://drip-app-hlunj.ondigitalocean.app';
  }

  async createCustomer(data: { externalCustomerId: string; name?: string }): Promise<{ customerId: string }> {
    const response = await fetch(`${this.apiUrl}/customers`, {
      method: 'POST',
      headers: {
        'x-api-key': this.apiKey,
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
      headers: { 'x-api-key': this.apiKey },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DripError(error.message || 'Failed to get customer', error.code, response.status);
    }
    return response.json();
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
        'x-api-key': this.apiKey,
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

  async getBalance(customerId: string): Promise<{ balanceUsdc: string }> {
    const response = await fetch(`${this.apiUrl}/customers/${customerId}/balance`, {
      headers: { 'x-api-key': this.apiKey },
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
