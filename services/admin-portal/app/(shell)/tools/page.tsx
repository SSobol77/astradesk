import ToolsClient from './ToolsClient';
import { openApiClient } from '@/api/client';

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

  return <ToolsClient connectors={connectors} />;
}
