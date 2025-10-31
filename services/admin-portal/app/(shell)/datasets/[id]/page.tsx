import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { Tabs } from '@/components/primitives/Tabs';
import { openApiClient } from '@/api/client';
import type { Dataset, DatasetEmbedding, DatasetSchema } from '@/api/types';
import { notFound } from 'next/navigation';

async function getDataset(id: string): Promise<Dataset | null> {
  try {
    return await openApiClient.datasets.get(id);
  } catch (error) {
    console.error('Failed to load dataset', error);
    return null;
  }
}

async function getSchema(id: string): Promise<DatasetSchema | null> {
  try {
    return await openApiClient.datasets.schema(id);
  } catch (error) {
    console.error('Failed to load schema', error);
    return null;
  }
}

async function getEmbeddings(id: string): Promise<DatasetEmbedding[]> {
  try {
    return await openApiClient.datasets.embeddings(id);
  } catch (error) {
    console.error('Failed to load embeddings', error);
    return [];
  }
}

type DatasetDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function DatasetDetailPage({ params }: DatasetDetailPageProps) {
  const { id } = await params;

  const [dataset, schema, embeddings] = await Promise.all([
    getDataset(id),
    getSchema(id),
    getEmbeddings(id),
  ]);

  if (!dataset) {
    notFound();
  }

  return (
    <Tabs
      tabs={[
        {
          key: 'schema',
          label: 'Schema',
          content: <JsonViewer value={schema ?? {}} />,
        },
        {
          key: 'embeddings',
          label: 'Embeddings',
          content: (
            <Card>
              {embeddings.length ? (
                <JsonViewer value={embeddings} />
              ) : (
                <p className="text-sm text-slate-500">No embeddings for this dataset.</p>
              )}
            </Card>
          ),
        },
        {
          key: 'metadata',
          label: 'Metadata',
          content: <JsonViewer value={dataset} />,
        },
      ]}
    />
  );
}
