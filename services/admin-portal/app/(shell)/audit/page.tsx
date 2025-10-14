import AuditClient from './AuditClient';
import { getQueryParamsFor } from '@/lib/guards';
import { openApiClient } from '@/openapi/openapi-client';
import type { AuditEntry } from '@/openapi/openapi-types';

async function getAuditEntries(): Promise<AuditEntry[]> {
  try {
    return await openApiClient.audit.list();
  } catch (error) {
    console.error('Failed to load audit entries', error);
    return [];
  }
}

export default async function AuditPage() {
  const [entries, filtersMeta] = await Promise.all([
    getAuditEntries(),
    Promise.resolve(getQueryParamsFor('audit', 'list')),
  ]);

  return <AuditClient initialEntries={entries} filtersMeta={filtersMeta} />;
}
