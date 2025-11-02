import FlowsClient from './FlowsClient';
import { openApiClient } from '@/api/client';
import type { Flow } from '@/api/types';

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

  return <FlowsClient flows={flows} />;
}
