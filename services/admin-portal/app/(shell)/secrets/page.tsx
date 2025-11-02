import SecretsClient from './SecretsClient';
import { openApiClient } from '@/api/client';
import type { Secret } from '@/api/types';

export const dynamic = 'force-dynamic';

async function getSecrets(): Promise<Secret[]> {
  try {
    return await openApiClient.secrets.list();
  } catch (error) {
    console.error('Failed to load secrets', error);
    return [];
  }
}

export default async function SecretsPage() {
  const secrets = await getSecrets();

  return <SecretsClient secrets={secrets} />;
}
