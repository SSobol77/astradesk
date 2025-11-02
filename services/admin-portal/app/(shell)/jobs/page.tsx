import JobsClient from './JobsClient';
import { openApiClient } from '@/api/client';
import type { DlqItem, Job } from '@/api/types';

async function getJobs(): Promise<Job[]> {
  try {
    return await openApiClient.jobs.list();
  } catch (error) {
    console.error('Failed to load jobs', error);
    return [];
  }
}

async function getDlq(): Promise<DlqItem[]> {
  try {
    return await openApiClient.jobs.dlq();
  } catch (error) {
    console.error('Failed to load DLQ', error);
    return [];
  }
}

export default async function JobsPage() {
  const [jobs, dlq] = await Promise.all([getJobs(), getDlq()]);

  return <JobsClient jobs={jobs} dlq={dlq} />;
}
