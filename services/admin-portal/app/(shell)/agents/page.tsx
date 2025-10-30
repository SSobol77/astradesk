import AgentsClient from './AgentsClient';
import { openApiClient } from '@/openapi/openapi-client';
import type { Agent } from '@/api/types.gen';

async function getAgents(): Promise<Agent[]> {
  try {
    return await openApiClient.agents.list();
  } catch (error) {
    console.error('Failed to load agents', error);
    return [];
  }
}

export default async function AgentsPage() {
  const agents = await getAgents();

  return <AgentsClient agents={agents} />;
}
