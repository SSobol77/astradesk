import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { openApiClient } from '@/api/client';
import type { Policy } from '@/api/types';
import { notFound } from 'next/navigation';
import PolicyActions from './PolicyActions';

async function getPolicy(id: string): Promise<Policy | null> {
  try {
    return await openApiClient.policies.get(id);
  } catch (error) {
    console.error('Failed to load policy', error);
    return null;
  }
}

type PolicyDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function PolicyDetailPage({ params }: PolicyDetailPageProps) {
  const { id } = await params;
  const policy = await getPolicy(id);

  if (!policy) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">{policy.name}</h2>
      </Card>
      <PolicyActions id={policy.id} />
      <JsonViewer value={policy} />
    </div>
  );
}
