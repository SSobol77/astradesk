import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { formatCurrency, formatDate, formatLatency } from '@/lib/format';
import { openApiClient } from '@/openapi/openapi-client';
import type { Run } from '@/openapi/openapi-types';
import { notFound } from 'next/navigation';

async function getRun(id: string): Promise<Run | null> {
  try {
    return await openApiClient.runs.get(id);
  } catch (error) {
    console.error('Failed to load run', error);
    return null;
  }
}

type RunDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { id } = await params;
  const run = await getRun(id);

  if (!run) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Run {run.id}</h2>
        <dl className="mt-4 grid gap-4 md:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Agent</dt>
            <dd className="mt-1 text-sm text-slate-700">{run.agent_id}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</dt>
            <dd className="mt-1 text-sm text-slate-700">{run.status}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Latency</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatLatency(run.latency_ms ?? null)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Cost</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatCurrency(run.cost_usd ?? null)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Created</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatDate(run.created_at)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Completed</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatDate(run.completed_at)}</dd>
          </div>
        </dl>
      </Card>
      <JsonViewer value={run} />
    </div>
  );
}
