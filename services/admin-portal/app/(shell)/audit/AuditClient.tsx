'use client';

import { useState } from 'react';
import FilterBar, { type FilterConfig } from '@/components/data/FilterBar';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/openapi/openapi-client';
import type { AuditEntry } from '@/openapi/openapi-types';
import type { QueryParamMeta } from '@/openapi/paths-map';
import { useToast } from '@/hooks/useToast';
import { formatDate } from '@/lib/format';

function toFilterConfig(meta: QueryParamMeta): FilterConfig {
  return {
    key: meta.key,
    label: meta.label,
    type: meta.type,
    options: meta.options,
  };
}

export default function AuditClient({
  initialEntries,
  filtersMeta,
}: {
  initialEntries: AuditEntry[];
  filtersMeta: QueryParamMeta[];
}) {
  const [entries, setEntries] = useState(initialEntries);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const { push } = useToast();

  const applyFilters = async (values: Record<string, string>) => {
    setFilters(values);
    try {
      const next = await openApiClient.audit.list(values);
      setEntries(next);
    } catch (error) {
      push({ title: 'Failed to filter audit trail', variant: 'error' });
    }
  };

  const exportAudit = async (format: 'json' | 'ndjson') => {
    try {
      await openApiClient.audit.exportData(format);
      push({ title: `Audit export started (${format.toUpperCase()})`, variant: 'info' });
    } catch (error) {
      push({ title: 'Audit export failed', variant: 'error' });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Audit Trail</h2>
          <p className="text-sm text-slate-500">GET /audit</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="secondary" onClick={() => exportAudit('json')}>
            Export JSON
          </Button>
          <Button type="button" variant="secondary" onClick={() => exportAudit('ndjson')}>
            Export NDJSON
          </Button>
        </div>
      </div>
      <FilterBar filters={filtersMeta.map(toFilterConfig)} onChange={applyFilters} initialValues={filters} />
      <DataTable
        columns={[
          { key: 'when_ts', header: 'Timestamp', render: (entry) => formatDate(entry.when_ts) },
          { key: 'user_id', header: 'User' },
          { key: 'action', header: 'Action' },
          { key: 'resource', header: 'Resource' },
          {
            key: 'actions',
            header: 'Actions',
            render: (entry) => (
              <a className="text-indigo-600 hover:underline" href={`/audit/${entry.id}`}>
                View
              </a>
            ),
          },
        ]}
        data={entries}
        emptyState={<p>No audit entries yet.</p>}
      />
    </div>
  );
}
