import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/openapi/openapi-client';
import type { AuditEntry } from '@/openapi/openapi-types';
import { notFound } from 'next/navigation';

async function getAuditEntry(id: string): Promise<AuditEntry | null> {
  try {
    return await openApiClient.audit.get(id);
  } catch (error) {
    console.error('Failed to load audit entry', error);
    return null;
  }
}

type AuditDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function AuditDetailPage({ params }: AuditDetailPageProps) {
  const { id } = await params;
  const entry = await getAuditEntry(id);

  if (!entry) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Audit Entry</h2>
        <dl className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Timestamp</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatDate(entry.when_ts)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">User</dt>
            <dd className="mt-1 text-sm text-slate-700">{entry.user_id}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Action</dt>
            <dd className="mt-1 text-sm text-slate-700">{entry.action}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resource</dt>
            <dd className="mt-1 text-sm text-slate-700">{entry.resource}</dd>
          </div>
          {entry.signature ? (
            <div className="md:col-span-2">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Signature</dt>
              <dd className="mt-1 text-sm text-slate-700">{entry.signature}</dd>
            </div>
          ) : null}
        </dl>
      </Card>
      <JsonViewer value={entry} />
    </div>
  );
}
