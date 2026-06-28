// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/intent-graph/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/intent-graph/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { openApiClient } from '@/api/client';
import type { IntentGraph } from '@/api/types';
import { isSimulationModeEnabled } from '@/lib/simulation';
import { simulationIntentGraph } from '@/lib/simulation-data';
import { IntentGraphActions } from './IntentGraphActions';

async function getGraph(): Promise<IntentGraph | null> {
  if (isSimulationModeEnabled()) {
    return simulationIntentGraph;
  }

  try {
    return await openApiClient.intentGraph.get();
  } catch (error) {
    console.error('Failed to load intent graph', error);
    return simulationIntentGraph;
  }
}

export default async function IntentGraphPage() {
  const graph = await getGraph();

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between text-[#041724]">
          <div>
            <h2 className="text-lg font-semibold text-[#041724]">Intent Graph</h2>
            <p className="text-sm text-[#041724]">Read-only view sourced from GET /intents/graph</p>
          </div>
          <IntentGraphActions graph={graph} />
        </div>
        <p className="mt-4 text-sm text-[#041724]">
          Visualisation is forthcoming. For now, the OpenAPI response is shown below for validation.
        </p>
      </Card>
      <JsonViewer value={graph ?? { nodes: [], edges: [] }} />
    </div>
  );
}
