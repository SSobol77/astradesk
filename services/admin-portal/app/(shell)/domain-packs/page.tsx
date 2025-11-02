import DomainPacksClient from './DomainPacksClient';
import { openApiClient } from '@/api/client';
import type { DomainPack } from '@/api/types';

async function getDomainPacks(): Promise<DomainPack[]> {
  try {
    return await openApiClient.domainPacks.list();
  } catch (error) {
    console.error('Failed to load domain packs', error);
    return [];
  }
}

export default async function DomainPacksPage() {
  const packs = await getDomainPacks();
  return <DomainPacksClient packs={packs} />;
}
