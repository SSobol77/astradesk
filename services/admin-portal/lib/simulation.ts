import { getSimulationResponse } from '@/lib/simulation-data';
import { clientEnv, simulationModeEnabled } from '@/lib/env';

export function isSimulationModeEnabled(): boolean {
  return simulationModeEnabled;
}

export function resolveSimulationResponse(path: string, method: string) {
  if (!isSimulationModeEnabled() || method !== 'GET') {
    return undefined;
  }
  return getSimulationResponse(path);
}

export const simulationConfig = {
  modeEnabled: isSimulationModeEnabled(),
  apiBaseUrl: clientEnv.NEXT_PUBLIC_API_BASE_URL,
};
