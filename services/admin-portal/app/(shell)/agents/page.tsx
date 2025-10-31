import AgentsClient from './AgentsClient';
import { openApiClient } from '@/api/client';
import type { Agent } from '@/api/types';
import { isSimulationModeEnabled } from '@/lib/simulation';
import { simulationAgents } from '@/lib/simulation-data';

async function getAgents(): Promise<Agent[]> {
  if (isSimulationModeEnabled()) {
    return simulationAgents;
  }

  try {
    return await openApiClient.agents.list();
  } catch (error) {
    console.error('Failed to load agents', error);
    return simulationAgents;
  }
}

export default async function AgentsPage() {
  const agents = await getAgents();

  return <AgentsClient agents={agents} />;
}
