import { getSimulationResponse } from '@/lib/simulation-data';
import { clientEnv, simulationModeEnabled } from '@/lib/env';

export function isSimulationModeEnabled(): boolean {
  return simulationModeEnabled;
}

const ACTION_METHODS = new Set(['POST', 'DELETE', 'PUT']);

const ALLOWED_ACTION_PATH = (path: string) => path.includes(':');

export function resolveSimulationResponse(path: string, method: string) {
  if (!isSimulationModeEnabled()) {
    return undefined;
  }

  if (method === 'GET' || (ACTION_METHODS.has(method) && ALLOWED_ACTION_PATH(path))) {
    return getSimulationResponse(path);
  }

  return undefined;
}

export const simulationConfig = {
  modeEnabled: isSimulationModeEnabled(),
  apiBaseUrl: clientEnv.NEXT_PUBLIC_API_BASE_URL,
};
