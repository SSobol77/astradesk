import DataTable from '@/components/data/DataTable';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/openapi/openapi-client';
import type { Secret } from '@/openapi/openapi-types';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

async function getSecrets(): Promise<Secret[]> {
  try {
    return await openApiClient.secrets.list();
  } catch (error) {
    console.error('Failed to load secrets', error);
    return [];
  }
}

export default async function SecretsPage() {
  const secrets = await getSecrets();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Secrets</h2>
          <p className="text-sm text-slate-500">GET /secrets</p>
        </div>
        <Link
          href="/secrets?create=1"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          New Secret
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'type', header: 'Type' },
          {
            key: 'last_used_at',
            header: 'Last Used',
            render: (secret) => formatDate(secret.last_used_at ?? null),
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (secret) => (
              <div className="flex gap-2">
                <button
                  type="button"
                  className="text-indigo-600 hover:underline"
                  data-action="rotate-secret"
                  data-secret-id={secret.id}
                >
                  Rotate
                </button>
                <button
                  type="button"
                  className="text-indigo-600 hover:underline"
                  data-action="disable-secret"
                  data-secret-id={secret.id}
                >
                  Disable
                </button>
              </div>
            ),
          },
        ]}
        data={secrets}
        emptyState={<p>No secrets recorded.</p>}
      />
    </div>
  );
}
