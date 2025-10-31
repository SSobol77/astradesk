import DataTable from '@/components/data/DataTable';
import { openApiClient } from '@/api/client';
import type { Dataset } from '@/api/types';
import Link from 'next/link';

async function getDatasets(): Promise<Dataset[]> {
  try {
    return await openApiClient.datasets.list();
  } catch (error) {
    console.error('Failed to load datasets', error);
    return [];
  }
}

export default async function DatasetsPage() {
  const datasets = await getDatasets();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Datasets</h2>
          <p className="text-sm text-slate-500">GET /datasets</p>
        </div>
        <Link
          href="/datasets?create=1"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          New Dataset
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'type', header: 'Type' },
          { key: 'indexing_status', header: 'Indexing Status' },
          {
            key: 'actions',
            header: 'Actions',
            render: (dataset) => (
              <div className="flex gap-2">
                <Link className="text-indigo-600 hover:underline" href={`/datasets/${dataset.id}`}>
                  View
                </Link>
                <a className="text-indigo-600 hover:underline" href={`#reindex-${dataset.id}`}>
                  Reindex
                </a>
              </div>
            ),
          },
        ]}
        data={datasets}
        emptyState={<p>No datasets yet.</p>}
      />
    </div>
  );
}
