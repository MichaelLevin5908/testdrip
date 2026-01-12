import { config } from 'dotenv';

config();

export interface LoadTestConfig {
  apiKey: string;
  apiUrl: string;
  defaultCustomerId?: string;
}

export function loadConfig(): LoadTestConfig {
  const apiKey = process.env.DRIP_API_KEY;

  if (!apiKey) {
    throw new Error('DRIP_API_KEY environment variable is required');
  }

  return {
    apiKey,
    apiUrl: process.env.DRIP_API_URL || 'https://drip-app-hlunj.ondigitalocean.app',
    defaultCustomerId: process.env.DEFAULT_CUSTOMER_ID,
  };
}
