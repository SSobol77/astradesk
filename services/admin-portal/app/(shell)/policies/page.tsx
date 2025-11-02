import PoliciesClient from './PoliciesClient';
import { openApiClient } from '@/api/client';
import type { Policy } from '@/api/types';

async function getPolicies(): Promise<Policy[]> {
  try {
    return await openApiClient.policies.list();
  } catch (error) {
    console.error('Failed to load policies', error);
    return [];
  }
}

export default async function PoliciesPage() {
  const policies = await getPolicies();

  return <PoliciesClient policies={policies} />;
}
