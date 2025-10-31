import DataTable from '@/components/data/DataTable';
import { openApiClient } from '@/api/client';
import Link from 'next/link';

async function getConnectors() {
  try {
    return await openApiClient.tools.list();
  } catch (error) {
    console.error('Failed to load connectors', error);
    return [];
  }
}

export default async function ToolsPage() {
  const connectors = await getConnectors();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Connectors</h2>
          <p className="text-sm text-slate-500">GET /connectors</p>
        </div>
        <Link
          href="/tools?create=1"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          New Connector
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name', render: (connector) => connector.name ?? '—' },
          { key: 'type', header: 'Type', render: (connector) => connector.type ?? '—' },
          { key: 'status', header: 'Status', render: (connector) => connector.status ?? '—' },
          {
            key: 'actions',
            header: 'Actions',
            render: (connector) => (
              <div className="flex gap-2">
                {connector.id ? (
                  <Link className="text-indigo-600 hover:underline" href={`/tools/${connector.id}`}>
                    View
                  </Link>
                ) : (
                  <span className="text-slate-400">No ID</span>
                )}
              </div>
            ),
          },
        ]}
        data={connectors}
        emptyState={<p>No connectors configured.</p>}
      />
    </div>
  );
}
