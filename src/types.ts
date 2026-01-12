export interface CheckResult {
  name: string;
  success: boolean;
  duration: number;
  message: string;
  details?: string;
  suggestion?: string;
}

export interface CheckContext {
  apiKey: string;
  apiUrl: string;
  testCustomerId?: string;
  createdCustomerId?: string;
  skipCleanup: boolean;
  timeout: number;
}

export type CheckFunction = (ctx: CheckContext) => Promise<CheckResult>;

export interface Check {
  name: string;
  description: string;
  run: CheckFunction;
  quick?: boolean;
}
