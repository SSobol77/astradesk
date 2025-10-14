import { object, optional, safeParse, string } from 'valibot';

const clientEnvSchema = object({
  NEXT_PUBLIC_API_BASE_URL: string('NEXT_PUBLIC_API_BASE_URL is required'),
  NEXT_PUBLIC_SIMULATION_MODE: optional(string()),
});

const serverEnvSchema = object({
  ASTRADESK_API_TOKEN: optional(string()),
});

const clientEnvResult = safeParse(clientEnvSchema, {
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_SIMULATION_MODE: process.env.NEXT_PUBLIC_SIMULATION_MODE,
});

if (!clientEnvResult.success) {
  const message = clientEnvResult.issues.map((issue) => issue.message).join(', ');
  throw new Error(`Environment validation failed: ${message}`);
}

const serverEnvResult = safeParse(serverEnvSchema, {
  ASTRADESK_API_TOKEN: process.env.ASTRADESK_API_TOKEN,
});

export const clientEnv = clientEnvResult.output;

export const apiBaseUrl = clientEnv.NEXT_PUBLIC_API_BASE_URL;
export const apiToken = serverEnvResult.success ? serverEnvResult.output.ASTRADESK_API_TOKEN ?? '' : '';
export const simulationModeEnabled = clientEnv.NEXT_PUBLIC_SIMULATION_MODE === 'true';
