import DatasetsClient from './DatasetsClient';
import { openApiClient } from '@/api/client';
import type { Dataset } from '@/api/types';

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

  return <DatasetsClient datasets={datasets} />;
}
