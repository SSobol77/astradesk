import Card from '@/components/primitives/Card';
import { Tabs } from '@/components/primitives/Tabs';
import JsonViewer from '@/components/misc/JsonViewer';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/openapi/openapi-client';
import type { Agent, AgentIoMessage, AgentMetrics } from '@/openapi/openapi-types';
import { notFound } from 'next/navigation';

async function getAgent(id: string): Promise<Agent | null> {
  try {
    return await openApiClient.agents.get(id);
  } catch (error) {
    console.error('Failed to load agent', error);
    return null;
  }
}

async function getMetrics(id: string): Promise<AgentMetrics | null> {
  try {
    return await openApiClient.agents.metrics(id, { p95: true, p99: false });
  } catch (error) {
    console.error('Failed to load metrics', error);
    return null;
  }
}

async function getIo(id: string): Promise<AgentIoMessage[]> {
  try {
    return await openApiClient.agents.io(id, 10);
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
    { label: 'Name', value: agent.name },
    { label: 'Version', value: agent.version },
    { label: 'Environment', value: agent.env },
    { label: 'Status', value: agent.status },
    { label: 'Updated', value: formatDate(agent.updatedAt) },
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
          {agent.description ? (
            <div className="md:col-span-2">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Description</dt>
              <dd className="mt-1 text-sm text-slate-700">{agent.description}</dd>
            </div>
          ) : null}
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
                      <dd className="mt-1 text-sm text-slate-700">{metrics.latencyP95Ms ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">p99</dt>
                      <dd className="mt-1 text-sm text-slate-700">{metrics.latencyP99Ms ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tokens per minute</dt>
                      <dd className="mt-1 text-sm text-slate-700">{metrics.tokensPerMinute ?? '—'}</dd>
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
                      <li key={index} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span className="uppercase tracking-wide">{entry.role}</span>
                          <span>{formatDate(entry.timestamp)}</span>
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-sm">{entry.content}</p>
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
