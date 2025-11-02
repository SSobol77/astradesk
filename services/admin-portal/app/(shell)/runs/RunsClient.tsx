'use client';

import { useMemo, useState, useEffect } from 'react';
import FilterBar, { type FilterConfig } from '@/components/data/FilterBar';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { Run } from '@/api/types';
import type { QueryParamMeta } from '@/api/operations-map';
import { useToast } from '@/hooks/useToast';
import { useRunsStream } from '@/hooks/useRunsStream';

function toFilterConfig(meta: QueryParamMeta): FilterConfig {
  return {
    key: meta.key,
    label: meta.label,
    type: meta.type,
    options: meta.options,
  };
}

export default function RunsClient({
  filtersMeta,
}: {
  filtersMeta: QueryParamMeta[];
}) {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const { push } = useToast();
  const streamParams = useMemo(() => {
    const agentIdRaw = filters.agentId;
    const statusRaw = filters.status;

    return {
      agentId: agentIdRaw ? agentIdRaw.trim() || undefined : undefined,
      status: statusRaw ? (statusRaw as Run['status']) : undefined,
    };
  }, [filters.agentId, filters.status]);

  const listParams = useMemo(() => {
    const fromRaw = filters.from;
    const toRaw = filters.to;

    return {
      ...streamParams,
      from: fromRaw ? fromRaw : undefined,
      to: toRaw ? toRaw : undefined,
    };
  }, [filters.from, filters.to, streamParams]);
  const { runs, error } = useRunsStream(streamParams, { initialFetchParams: listParams });

  useEffect(() => {
    if (error) {
      push({ title: error, variant: 'warn' });
    }
  }, [error, push]);

  const filterConfigs = useMemo(() => filtersMeta.map(toFilterConfig), [filtersMeta]);

  const applyFilters = (values: Record<string, string>) => {
    setFilters(values);
  };

  const exportLogs = async (format: 'json' | 'ndjson' | 'csv') => {
    try {
      await openApiClient.runs.exportLogs(format, {
        agentId: filters.agentId,
        status: filters.status as Run['status'] | undefined,
        from: filters.from,
        to: filters.to,
      });
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
          <Button type="button" variant="secondary" onClick={() => exportLogs('csv')}>
            Export CSV
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
