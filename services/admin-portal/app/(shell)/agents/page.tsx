// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/agents/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/agents/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import AgentsClient from './AgentsClient';
import { openApiClient } from '@/api/client';
import type { Agent } from '@/api/types';
import { isSimulationModeEnabled } from '@/lib/simulation';
import { simulationAgents } from '@/lib/simulation-data';

async function getAgents(): Promise<Agent[]> {
  if (isSimulationModeEnabled()) {
    return simulationAgents;
  }

  try {
    return await openApiClient.agents.list();
  } catch (error) {
    console.error('Failed to load agents', error);
    return simulationAgents;
  }
}

export default async function AgentsPage() {
  const agents = await getAgents();

  return <AgentsClient agents={agents} />;
}
