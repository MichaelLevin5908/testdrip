/**
 * Shared test helpers for mocking fetch and creating test fixtures.
 * Used by unit and contract tests to avoid real HTTP calls.
 */
import { vi } from 'vitest';
import { Drip } from '@drip-sdk/node';

// ============================================================================
// Fetch Mocking
// ============================================================================

export function createMockFetch() {
  const mockFn = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();
  return mockFn;
}

export function installMockFetch() {
  const mockFetch = createMockFetch();
  globalThis.fetch = mockFetch as unknown as typeof globalThis.fetch;
  return mockFetch;
}

// ============================================================================
// Response Builders
// ============================================================================

export function mockJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function mockErrorResponse(
  message: string,
  status: number,
  code?: string,
): Response {
  return mockJsonResponse({ error: message, message, code }, status);
}

// ============================================================================
// Fixtures
// ============================================================================

export function mockCustomer(overrides: Record<string, unknown> = {}) {
  return {
    id: 'cust_test_123',
    businessId: 'biz_test_456',
    externalCustomerId: 'ext_user_789',
    onchainAddress: '0x1234567890abcdef1234567890abcdef12345678',
    isInternal: false,
    status: 'ACTIVE',
    metadata: null,
    createdAt: '2024-01-01T00:00:00.000Z',
    updatedAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

export function mockChargeResult(overrides: Record<string, unknown> = {}) {
  return {
    success: true,
    usageEventId: 'evt_test_abc',
    isDuplicate: false,
    charge: {
      id: 'chg_test_def',
      amountUsdc: '0.005000',
      amountToken: '5000',
      txHash: '0xabcdef1234567890',
      status: 'PENDING',
    },
    ...overrides,
  };
}

export function mockTrackUsageResult(overrides: Record<string, unknown> = {}) {
  return {
    success: true,
    usageEventId: 'evt_test_track',
    customerId: 'cust_test_123',
    usageType: 'api_calls',
    quantity: 1,
    isInternal: false,
    message: 'Usage recorded successfully',
    ...overrides,
  };
}

export function mockBalanceResult(overrides: Record<string, unknown> = {}) {
  return {
    customerId: 'cust_test_123',
    onchainAddress: '0x1234567890abcdef1234567890abcdef12345678',
    balanceUsdc: '100.000000',
    pendingChargesUsdc: '5.000000',
    availableUsdc: '95.000000',
    lastSyncedAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

export function mockWebhook(overrides: Record<string, unknown> = {}) {
  return {
    id: 'wh_test_123',
    url: 'https://example.com/webhooks',
    events: ['charge.succeeded', 'charge.failed'],
    description: 'Test webhook',
    isActive: true,
    healthStatus: 'HEALTHY',
    consecutiveFailures: 0,
    lastHealthChange: null,
    createdAt: '2024-01-01T00:00:00.000Z',
    updatedAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

export function mockWorkflow(overrides: Record<string, unknown> = {}) {
  return {
    id: 'wf_test_123',
    name: 'Test Workflow',
    slug: 'test_workflow',
    productSurface: 'CUSTOM',
    chain: null,
    description: null,
    isActive: true,
    createdAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

export function mockRunResult(overrides: Record<string, unknown> = {}) {
  return {
    id: 'run_test_123',
    customerId: 'cust_test_123',
    workflowId: 'wf_test_123',
    workflowName: 'Test Workflow',
    status: 'RUNNING',
    correlationId: null,
    createdAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

export function mockEventResult(overrides: Record<string, unknown> = {}) {
  return {
    id: 'revt_test_123',
    runId: 'run_test_123',
    eventType: 'agent.step',
    quantity: 1,
    costUnits: null,
    isDuplicate: false,
    timestamp: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

export function mockRecordRunResult(overrides: Record<string, unknown> = {}) {
  return {
    run: {
      id: 'run_test_123',
      workflowId: 'wf_test_123',
      workflowName: 'Test Workflow',
      status: 'COMPLETED',
      durationMs: 150,
    },
    events: { created: 3, duplicates: 0 },
    totalCostUnits: '0.25',
    summary: '✓ Test Workflow: 3 events recorded (150ms)',
    ...overrides,
  };
}

// ============================================================================
// Test Client Factory
// ============================================================================

const BASE_URL = 'https://mock.drip.test/v1';

export function createTestDrip(keyType: 'secret' | 'public' = 'secret') {
  const apiKey = keyType === 'secret' ? 'sk_test_mock_key_123' : 'pk_test_mock_key_123';
  return new Drip({ apiKey, baseUrl: BASE_URL });
}

export { BASE_URL };
