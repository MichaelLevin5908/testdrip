import { config } from 'dotenv';

config();

export interface DripConfig {
  apiKey: string;
  apiUrl: string;
  testCustomerId?: string;
  skipCleanup: boolean;
  timeout: number;
}

export function loadConfig(): DripConfig {
  const apiKey = process.env.DRIP_API_KEY;

  if (!apiKey) {
    throw new Error('DRIP_API_KEY environment variable is required');
  }

  return {
    apiKey,
    apiUrl: process.env.DRIP_API_URL || 'https://drip-app-hlunj.ondigitalocean.app',
    testCustomerId: process.env.TEST_CUSTOMER_ID,
    skipCleanup: process.env.SKIP_CLEANUP === 'true',
    timeout: parseInt(process.env.CHECK_TIMEOUT || '30000', 10),
  };
}
