import DataTable from '@/components/data/DataTable';
import { openApiClient } from '@/api/client';
import type { Policy } from '@/api/types';
import Link from 'next/link';

async function getPolicies(): Promise<Policy[]> {
  try {
    return await openApiClient.policies.list();
  } catch (error) {
    console.error('Failed to load policies', error);
    return [];
  }
}

export default async function PoliciesPage() {
  const policies = await getPolicies();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Policies</h2>
          <p className="text-sm text-slate-500">GET /policies</p>
        </div>
        <Link
          href="/policies?create=1"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          Create Policy
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          {
            key: 'actions',
            header: 'Actions',
            render: (policy) => (
              <div className="flex gap-2">
                <Link className="text-indigo-600 hover:underline" href={`/policies/${policy.id}`}>
                  View
                </Link>
              </div>
            ),
          },
        ]}
        data={policies}
        emptyState={<p>No policies defined.</p>}
      />
    </div>
  );
}
