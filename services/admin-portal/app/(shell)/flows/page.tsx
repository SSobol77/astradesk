import DataTable from '@/components/data/DataTable';
import { openApiClient } from '@/openapi/openapi-client';
import type { Flow } from '@/openapi/openapi-types';
import Link from 'next/link';

async function getFlows(): Promise<Flow[]> {
  try {
    return await openApiClient.flows.list();
  } catch (error) {
    console.error('Failed to load flows', error);
    return [];
  }
}

export default async function FlowsPage() {
  const flows = await getFlows();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Flows</h2>
          <p className="text-sm text-slate-500">GET /flows</p>
        </div>
        <Link
          href="/flows?create=1"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          New Flow
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'id', header: 'ID' },
          {
            key: 'actions',
            header: 'Actions',
            render: (flow) => (
              <div className="flex gap-2">
                <Link className="text-indigo-600 hover:underline" href={`/flows/${flow.id}`}>
                  View
                </Link>
              </div>
            ),
          },
        ]}
        data={flows}
        emptyState={<p>No flows yet.</p>}
      />
    </div>
  );
}
