import DataTable from '@/components/data/DataTable';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/api/client';
import type { DlqItem, Job } from '@/api/types';
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
            key: 'task_definition',
            header: 'Task',
            render: (job) => <code className="text-xs">{JSON.stringify(job.task_definition ?? {}, null, 2)}</code>,
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
            { key: 'id', header: 'ID' },
            { key: 'error_message', header: 'Reason' },
            {
              key: 'failed_at',
              header: 'Failed At',
              render: (item) => formatDate(item.failed_at),
            },
          ]}
          data={dlq}
          emptyState={<p>No DLQ entries.</p>}
        />
      </section>
    </div>
  );
}
