import Card from '@/components/primitives/Card';
import { Tabs } from '@/components/primitives/Tabs';
import JsonViewer from '@/components/misc/JsonViewer';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/api/client';
import type { Agent, AgentIoMessage, AgentMetrics } from '@/api/types';
import { simulationAgentIo, simulationAgentMetrics, simulationAgents } from '@/lib/simulation-data';
import { isSimulationModeEnabled } from '@/lib/simulation';
import { notFound } from 'next/navigation';

async function getAgent(id: string): Promise<Agent | null> {
  if (isSimulationModeEnabled()) {
    return simulationAgents.find((agent) => agent.id === id) ?? simulationAgents[0] ?? null;
  }

  try {
    return await openApiClient.agents.get(id);
  } catch (error) {
    console.error('Failed to load agent', error);
    return null;
  }
}

async function getMetrics(id: string): Promise<AgentMetrics | null> {
  if (isSimulationModeEnabled()) {
    return simulationAgentMetrics;
  }

  try {
    return await openApiClient.agents.metrics(id);
  } catch (error) {
    console.error('Failed to load metrics', error);
    return null;
  }
}

async function getIo(id: string): Promise<AgentIoMessage[]> {
  if (isSimulationModeEnabled()) {
    return simulationAgentIo;
  }

  try {
    return await openApiClient.agents.io(id, { limit: 10 });
  } catch (error) {
    console.error('Failed to load IO logs', error);
    return [];
  }
}

type AgentDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function AgentDetailPage({ params }: AgentDetailPageProps) {
  const { id } = await params;

  const [agent, metrics, io] = await Promise.all([
    getAgent(id),
    getMetrics(id),
    getIo(id),
  ]);

  if (!agent) {
    notFound();
  }

  const overviewEntries: Array<{ label: string; value: string }> = [
    { label: 'ID', value: agent.id },
    { label: 'Name', value: agent.name },
    { label: 'Version', value: agent.version ?? '—' },
    { label: 'Environment', value: agent.env ?? '—' },
    { label: 'Status', value: agent.status ?? '—' },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Agent Overview</h2>
        <dl className="mt-4 grid gap-4 md:grid-cols-2">
          {overviewEntries.map((entry) => (
            <div key={entry.label}>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{entry.label}</dt>
              <dd className="mt-1 text-sm text-slate-700">{entry.value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Tabs
        tabs={[
          {
            key: 'metrics',
            label: 'Metrics',
            content: (
              <Card>
                <h3 className="text-base font-semibold text-slate-900">Latency Metrics</h3>
                {metrics ? (
                  <dl className="mt-4 grid gap-4 md:grid-cols-3">
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">p95</dt>
                      <dd className="mt-1 text-sm text-slate-700">{metrics.p95_latency_ms ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">p99</dt>
                      <dd className="mt-1 text-sm text-slate-700">{metrics.p99_latency_ms ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Request count</dt>
                      <dd className="mt-1 text-sm text-slate-700">{metrics.request_count ?? '—'}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="mt-4 text-sm text-slate-500">Metrics unavailable.</p>
                )}
              </Card>
            ),
          },
          {
            key: 'io',
            label: 'IO',
            content: (
              <Card>
                <h3 className="text-base font-semibold text-slate-900">Recent Inputs & Outputs (tail=10)</h3>
                {io.length ? (
                  <ul className="mt-4 space-y-3 text-sm text-slate-700">
                    {io.map((entry, index) => (
                      <li key={`${entry.timestamp}-${index}`} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>Input</span>
                          <span>{formatDate(entry.timestamp)}</span>
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-sm">{entry.input}</p>
                        <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Output</div>
                        <p className="mt-2 whitespace-pre-wrap text-sm">{entry.output}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 text-sm text-slate-500">No IO entries for this agent.</p>
                )}
              </Card>
            ),
          },
          {
            key: 'raw',
            label: 'Raw JSON',
            content: <JsonViewer value={agent} />,
          },
        ]}
        initialKey="metrics"
      />
    </div>
  );
}
