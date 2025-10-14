import RunsClient from './RunsClient';
import { getQueryParamsFor } from '@/lib/guards';
import { openApiClient } from '@/openapi/openapi-client';
import type { Run } from '@/openapi/openapi-types';

async function getRuns(): Promise<Run[]> {
  try {
    return await openApiClient.runs.list();
  } catch (error) {
    console.error('Failed to load runs', error);
    return [];
  }
}

export default async function RunsPage() {
  const [runs, filtersMeta] = await Promise.all([
    getRuns(),
    Promise.resolve(getQueryParamsFor('runs', 'list')),
  ]);

  return <RunsClient initialRuns={runs} filtersMeta={filtersMeta} />;
}
