'use client';

import { useMemo, useState } from 'react';
import FilterBar, { type FilterConfig } from '@/components/data/FilterBar';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { AuditEntry } from '@/api/types';
import type { QueryParamMeta } from '@/api/operations-map';
import { useToast } from '@/hooks/useToast';
import { formatDate } from '@/lib/format';
import { apiBaseUrl, apiToken } from '@/lib/env';
import { resolveSimulationResponse } from '@/lib/simulation';

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
  const [exportingFormat, setExportingFormat] = useState<'json' | 'ndjson' | 'csv' | null>(null);
  const { push } = useToast();

  const applyFilters = async (values: Record<string, string>) => {
    setFilters(values);
    try {
      const next = await openApiClient.audit.list({
        userId: values.userId,
        action: values.action,
        resource: values.resource,
        from: values.from,
        to: values.to,
      });
      setEntries(next);
    } catch (error) {
      push({ title: 'Failed to filter audit trail', variant: 'error' });
    }
  };

  const downloadFilename = useMemo(() => {
    return (format: 'json' | 'ndjson' | 'csv') => {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      return `audit-export-${timestamp}.${format === 'ndjson' ? 'ndjson' : format}`;
    };
  }, []);

  const parseFilename = (contentDisposition: string | null, fallback: string) => {
    if (!contentDisposition) {
      return fallback;
    }
    const match = contentDisposition.match(/filename\\*?=(?:UTF-8''|\"?)([^\";]+)/i);
    if (match && match[1]) {
      try {
        return decodeURIComponent(match[1]);
      } catch {
        return match[1];
      }
    }
    return fallback;
  };

  const exportAudit = async (format: 'json' | 'ndjson' | 'csv') => {
    setExportingFormat(format);
    try {
      const searchParams = new URLSearchParams({ format });
      (['userId', 'action', 'resource', 'from', 'to'] as const).forEach((key) => {
        const value = filters[key];
        if (value) {
          searchParams.set(key, value);
        }
      });

      const exportPath = `/api/admin/v1/audit/export${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      const simulationPayload = resolveSimulationResponse(exportPath, 'GET');
      if (simulationPayload !== undefined) {
        const simulatedContent =
          typeof simulationPayload === 'string'
            ? simulationPayload
            : JSON.stringify(simulationPayload, null, 2);
        downloadBlob(simulatedContent, format, mimeTypeFor(format));
        push({ title: `Audit export ready (${format.toUpperCase()})`, variant: 'success' });
        return;
      }

      let requestUrl: string;
      try {
        requestUrl = new URL(exportPath, apiBaseUrl).toString();
      } catch {
        requestUrl = new URL(exportPath, window.location.origin).toString();
      }

      const response = await fetch(requestUrl, {
        method: 'GET',
        headers: {
          ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Export failed with status ${response.status}`);
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get('content-disposition');
      const filename = parseFilename(contentDisposition, downloadFilename(format));

      const blobUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = blobUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(blobUrl);

      push({ title: `Audit export ready (${format.toUpperCase()})`, variant: 'success' });
    } catch (error) {
      console.error('Audit export failed', error);
      push({ title: 'Audit export failed', variant: 'error' });
    } finally {
      setExportingFormat(null);
    }
  };

  const downloadBlob = (content: string, format: 'json' | 'ndjson' | 'csv', mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const filename = downloadFilename(format);
    const blobUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(blobUrl);
  };

  const mimeTypeFor = (format: 'json' | 'ndjson' | 'csv') => {
    switch (format) {
      case 'json':
        return 'application/json';
      case 'ndjson':
        return 'application/x-ndjson';
      case 'csv':
        return 'text/csv';
      default:
        return 'application/octet-stream';
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
          <Button
            type="button"
            variant="secondary"
            onClick={() => exportAudit('json')}
            disabled={exportingFormat === 'json'}
          >
            Export JSON
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => exportAudit('ndjson')}
            disabled={exportingFormat === 'ndjson'}
          >
            Export NDJSON
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => exportAudit('csv')}
            disabled={exportingFormat === 'csv'}
          >
            Export CSV
          </Button>
        </div>
      </div>
      <FilterBar filters={filtersMeta.map(toFilterConfig)} onChange={applyFilters} initialValues={filters} />
      <DataTable
        columns={[
          { key: 'when_ts', header: 'Timestamp', render: (entry) => formatDate(entry.when_ts ?? null) },
          { key: 'user_id', header: 'User', render: (entry) => entry.user_id ?? '—' },
          { key: 'action', header: 'Action', render: (entry) => entry.action ?? '—' },
          { key: 'resource', header: 'Resource', render: (entry) => entry.resource ?? '—' },
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
