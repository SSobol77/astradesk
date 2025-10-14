'use client';

import { useEffect, useMemo, useState } from 'react';
import FilterBar, { type FilterConfig } from '@/components/data/FilterBar';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import { createSseStream } from '@/lib/sse';
import { openApiClient } from '@/openapi/openapi-client';
import type { Run } from '@/openapi/openapi-types';
import type { QueryParamMeta } from '@/openapi/paths-map';
import { useToast } from '@/hooks/useToast';

function toFilterConfig(meta: QueryParamMeta): FilterConfig {
  return {
    key: meta.key,
    label: meta.label,
    type: meta.type,
    options: meta.options,
  };
}

export default function RunsClient({
  initialRuns,
  filtersMeta,
}: {
  initialRuns: Run[];
  filtersMeta: QueryParamMeta[];
}) {
  const [runs, setRuns] = useState(initialRuns);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const { push } = useToast();

  useEffect(() => {
    const cleanup = createSseStream({
      path: '/runs/stream',
      onMessage: (event) => {
        setRuns((current) => [event, ...current].slice(0, 50));
      },
      onError: () => {
        push({ title: 'Stream disconnected', variant: 'warn' });
      },
    });

    return cleanup;
  }, [push]);

  const filterConfigs = useMemo(() => filtersMeta.map(toFilterConfig), [filtersMeta]);

  const applyFilters = async (values: Record<string, string>) => {
    setFilters(values);
    try {
      const nextRuns = await openApiClient.runs.list(values);
      setRuns(nextRuns);
    } catch (error) {
      push({ title: 'Failed to filter runs', variant: 'error' });
    }
  };

  const exportLogs = async (format: 'json' | 'ndjson') => {
    try {
      await openApiClient.runs.exportLogs(format);
      push({ title: `Export started (${format.toUpperCase()})`, variant: 'info' });
    } catch (error) {
      push({ title: 'Export failed', variant: 'error' });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Runs</h2>
          <p className="text-sm text-slate-500">Streaming via /runs/stream</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="secondary" onClick={() => exportLogs('json')}>
            Export JSON
          </Button>
          <Button type="button" variant="secondary" onClick={() => exportLogs('ndjson')}>
            Export NDJSON
          </Button>
        </div>
      </div>
      <FilterBar filters={filterConfigs} onChange={applyFilters} initialValues={filters} />
      <DataTable
        columns={[
          { key: 'id', header: 'Run ID' },
          { key: 'agent_id', header: 'Agent' },
          { key: 'status', header: 'Status' },
          {
            key: 'latency_ms',
            header: 'Latency (ms)',
            render: (run) => run.latency_ms ?? '—',
          },
          {
            key: 'cost_usd',
            header: 'Cost (USD)',
            render: (run) => (run.cost_usd ? `$${run.cost_usd.toFixed(2)}` : '—'),
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (run) => (
              <a className="text-indigo-600 hover:underline" href={`/runs/${run.id}`}>
                View
              </a>
            ),
          },
        ]}
        data={runs}
        emptyState={<p>No runs yet.</p>}
      />
    </div>
  );
}
