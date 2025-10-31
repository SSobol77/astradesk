import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { openApiClient } from '@/api/client';
import { notFound } from 'next/navigation';
import ConnectorActions from './ConnectorActions';

async function getConnector(id: string) {
  try {
    return await openApiClient.tools.get(id);
  } catch (error) {
    console.error('Failed to load connector', error);
    return null;
  }
}

type ConnectorDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ConnectorDetailPage({ params }: ConnectorDetailPageProps) {
  const { id } = await params;
  const connector = await getConnector(id);

  if (!connector) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{connector.name}</h2>
            <p className="text-sm text-slate-500">Type: {connector.type}</p>
          </div>
          <ConnectorActions id={connector.id} />
        </div>
      </Card>
      <JsonViewer value={connector} />
    </div>
  );
}
