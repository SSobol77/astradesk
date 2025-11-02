import RunsClient from './RunsClient';
import { getQueryParamsFor } from '@/lib/guards';

export default async function RunsPage() {
  const filtersMeta = getQueryParamsFor('runs', 'list');

  return <RunsClient filtersMeta={filtersMeta} />;
}
