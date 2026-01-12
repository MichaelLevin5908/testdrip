export interface RequestResult {
  success: boolean;
  duration: number;
  error?: string;
  errorCode?: string;
}

export interface ScenarioResult {
  scenario: string;
  duration: number;
  totalRequests: number;
  succeeded: number;
  failed: number;
  latencies: number[];
  errors: Map<string, number>;
}

export interface LatencyStats {
  min: number;
  max: number;
  avg: number;
  p50: number;
  p95: number;
  p99: number;
}

export interface ScenarioConfig {
  apiKey: string;
  apiUrl: string;
  customerId: string;
  concurrency: number;
  total: number;
  duration?: number;
  rps?: number;
  useIdempotency?: boolean;
  warmup?: number;
}

export type ScenarioFunction = (config: ScenarioConfig) => Promise<ScenarioResult>;
