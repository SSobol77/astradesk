import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { openApiClient } from '@/api/client';
import type { Job } from '@/api/types';
import { notFound } from 'next/navigation';
import JobActions from './JobActions';

async function getJob(id: string): Promise<Job | null> {
  try {
    return await openApiClient.jobs.get(id);
  } catch (error) {
    console.error('Failed to load job', error);
    return null;
  }
}

type JobDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function JobDetailPage({ params }: JobDetailPageProps) {
  const { id } = await params;
  const job = await getJob(id);

  if (!job || !job.id) {
    notFound();
  }

  const jobId = job.id;
  const taskDefinition = (job as { task_definition?: Record<string, unknown> }).task_definition ?? {};

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{job.name ?? 'Untitled job'}</h2>
            <p className="text-sm text-slate-500">Schedule: {job.schedule_expr ?? '—'}</p>
          </div>
          <JobActions id={jobId} />
        </div>
        <dl className="mt-4 grid gap-4 md:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</dt>
            <dd className="mt-1 text-sm text-slate-700">{job.status ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Job ID</dt>
            <dd className="mt-1 text-sm text-slate-700">{jobId}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Task Definition</dt>
            <dd className="mt-1 text-sm text-slate-700">
              <code className="text-xs text-[#2978B3]">{JSON.stringify(taskDefinition, null, 2)}</code>
            </dd>
          </div>
        </dl>
      </Card>
      <JsonViewer value={job} />
    </div>
  );
}
