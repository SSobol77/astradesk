import DataTable from '@/components/data/DataTable';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/openapi/openapi-client';
import type { DlqItem, Job } from '@/openapi/openapi-types';
import Link from 'next/link';

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Jobs & Schedules</h2>
          <p className="text-sm text-slate-500">GET /jobs</p>
        </div>
        <Link
          href="/jobs?create=1"
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          New Job
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'schedule_expr', header: 'Schedule' },
          { key: 'status', header: 'Status' },
          {
            key: 'last_run_at',
            header: 'Last Run',
            render: (job) => formatDate(job.last_run_at ?? null),
          },
          {
            key: 'next_run_at',
            header: 'Next Run',
            render: (job) => formatDate(job.next_run_at ?? null),
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (job) => (
              <div className="flex gap-2">
                <Link className="text-indigo-600 hover:underline" href={`/jobs/${job.id}`}>
                  View
                </Link>
              </div>
            ),
          },
        ]}
        data={jobs}
        emptyState={<p>No jobs scheduled.</p>}
      />
      <section>
        <h3 className="text-base font-semibold text-slate-900">Dead Letter Queue</h3>
        <DataTable
          columns={[
            { key: 'job_id', header: 'Job' },
            { key: 'failure_reason', header: 'Reason' },
            {
              key: 'created_at',
              header: 'Created',
              render: (item) => formatDate(item.created_at),
            },
          ]}
          data={dlq}
          emptyState={<p>No DLQ entries.</p>}
        />
      </section>
    </div>
  );
}
