import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { apiBaseUrl } from '@/lib/env';
import { openApiClient } from '@/openapi/openapi-client';
import type { IntentGraph } from '@/openapi/openapi-types';

async function getGraph(): Promise<IntentGraph | null> {
  try {
    return await openApiClient.intentGraph.get();
  } catch (error) {
    console.error('Failed to load intent graph', error);
    return null;
  }
}

export default async function IntentGraphPage() {
  const graph = await getGraph();

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Intent Graph</h2>
            <p className="text-sm text-slate-500">Read-only view sourced from GET /intents/graph</p>
          </div>
          <a
            href={`${apiBaseUrl}/intents/graph`}
            className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Export JSON
          </a>
        </div>
        <p className="mt-4 text-sm text-slate-600">
          Visualisation is forthcoming. For now, the OpenAPI response is shown below for validation.
        </p>
      </Card>
      <JsonViewer value={graph ?? { nodes: [], edges: [] }} />
    </div>
  );
}
