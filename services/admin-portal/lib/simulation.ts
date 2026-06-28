// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/simulation.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/simulation.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import { getSimulationMutationResponse, getSimulationResponse } from '@/lib/simulation-data';
import { clientEnv, simulationModeEnabled } from '@/lib/env';

export function isSimulationModeEnabled(): boolean {
  return simulationModeEnabled;
}

const ACTION_METHODS = new Set(['POST', 'DELETE', 'PUT']);

const normalizePath = (path: string) => path.replace(/\?.*$/, '');

const ALLOWED_ACTION_PATH = (path: string) => path.includes(':');

export function resolveSimulationResponse(path: string, method: string, body?: unknown) {
  if (!isSimulationModeEnabled()) {
    return undefined;
  }

  const normalizedPath = normalizePath(path);

  if (method === 'GET') {
    return getSimulationResponse(path);
  }

  if (ACTION_METHODS.has(method)) {
    const mutationResponse = getSimulationMutationResponse(method, normalizedPath, body);
    if (mutationResponse !== undefined) {
      return mutationResponse;
    }

    if (ALLOWED_ACTION_PATH(normalizedPath)) {
      return getSimulationResponse(path);
    }
  }

  return undefined;
}

export const simulationConfig = {
  modeEnabled: isSimulationModeEnabled(),
  apiBaseUrl: clientEnv.NEXT_PUBLIC_API_BASE_URL,
};
