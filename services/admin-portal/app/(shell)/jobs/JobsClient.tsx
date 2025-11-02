'use client';

import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Textarea } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { DlqItem, Job } from '@/api/types';
import { formatDate } from '@/lib/format';
import { useToast } from '@/hooks/useToast';

const emptyTaskDefinition = '{\n  "task": "send-summary"\n}';

export default function JobsClient({ jobs, dlq }: { jobs: Job[]; dlq: DlqItem[] }) {
  const router = useRouter();
  const { push } = useToast();

  const [createName, setCreateName] = useState('');
  const [createSchedule, setCreateSchedule] = useState('0 * * * *');
  const [createTaskJson, setCreateTaskJson] = useState(emptyTaskDefinition);
  const [isCreating, setCreating] = useState(false);

  const [editId, setEditId] = useState('');
  const [editName, setEditName] = useState('');
  const [editSchedule, setEditSchedule] = useState('');
  const [editTaskJson, setEditTaskJson] = useState(emptyTaskDefinition);
  const [isUpdating, setUpdating] = useState(false);

  const createTaskDefinition = useMemo(() => {
    try {
      return createTaskJson ? JSON.parse(createTaskJson) : {};
    } catch {
      return null;
    }
  }, [createTaskJson]);

  const updateTaskDefinition = useMemo(() => {
    try {
      return editTaskJson ? JSON.parse(editTaskJson) : {};
    } catch {
      return null;
    }
  }, [editTaskJson]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!createName.trim() || !createSchedule.trim()) {
      push({ title: 'Provide job name and schedule', variant: 'error' });
      return;
    }
    if (!createTaskDefinition) {
      push({ title: 'Invalid task definition JSON', variant: 'error' });
      return;
    }
    setCreating(true);
    try {
      await openApiClient.jobs.create({
        name: createName.trim(),
        schedule_expr: createSchedule.trim(),
        task_definition: createTaskDefinition,
      });
      push({ title: 'Job created', variant: 'success' });
      setCreateName('');
      setCreateTaskJson(emptyTaskDefinition);
      router.refresh();
    } catch (error) {
      console.error('Create job failed', error);
      push({ title: 'Failed to create job', variant: 'error' });
    } finally {
      setCreating(false);
    }
  };

  const beginEdit = (job: Job) => {
    if (!job.id) return;
    setEditId(job.id);
    setEditName(job.name ?? '');
    setEditSchedule(job.schedule_expr ?? '');
    const definition = (job as { task_definition?: Record<string, unknown> }).task_definition ?? {};
    setEditTaskJson(JSON.stringify(definition, null, 2));
  };

  const handleUpdate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editId.trim()) {
      push({ title: 'Select a job to update', variant: 'error' });
      return;
    }
    if (!editSchedule.trim()) {
      push({ title: 'Schedule is required', variant: 'error' });
      return;
    }
    if (!updateTaskDefinition) {
      push({ title: 'Invalid task definition JSON', variant: 'error' });
      return;
    }
    setUpdating(true);
    try {
      await openApiClient.jobs.update(editId, {
        name: editName.trim() || undefined,
        schedule_expr: editSchedule.trim(),
        task_definition: updateTaskDefinition,
      });
      push({ title: 'Job updated', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Update job failed', error);
      push({ title: 'Failed to update job', variant: 'error' });
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async (job: Job) => {
    if (!job.id) return;
    const confirmed = window.confirm(`Delete job "${job.name ?? job.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.jobs.delete(job.id);
      push({ title: 'Job deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete job failed', error);
      push({ title: 'Failed to delete job', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Create Job</h2>
        <p className="text-sm text-slate-500">POST /jobs</p>
        <Form className="mt-4" onSubmit={handleCreate}>
          <FormField label="Name">
            <Input value={createName} onChange={(event) => setCreateName(event.target.value)} placeholder="Weekly summary" required />
          </FormField>
          <FormField label="Schedule (CRON)">
            <Input value={createSchedule} onChange={(event) => setCreateSchedule(event.target.value)} placeholder="0 * * * *" required />
          </FormField>
          <FormField label="Task Definition" error={createTaskDefinition ? undefined : 'Invalid JSON'}>
            <Textarea value={createTaskJson} onChange={(event) => setCreateTaskJson(event.target.value)} rows={5} />
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isCreating}>
              Create Job
            </Button>
          </div>
        </Form>
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Update Job</h2>
            <p className="text-sm text-slate-500">{'PUT /jobs/{id}'}</p>
          </div>
          <span className="text-xs text-slate-500">Select a job below to populate this form.</span>
        </div>
        <Form className="mt-4" onSubmit={handleUpdate}>
          <FormField label="Job ID">
            <Input value={editId} onChange={(event) => setEditId(event.target.value)} placeholder="job_123" required />
          </FormField>
          <FormField label="Name">
            <Input value={editName} onChange={(event) => setEditName(event.target.value)} placeholder="Weekly summary" />
          </FormField>
          <FormField label="Schedule (CRON)">
            <Input value={editSchedule} onChange={(event) => setEditSchedule(event.target.value)} placeholder="0 * * * *" required />
          </FormField>
          <FormField label="Task Definition" error={updateTaskDefinition ? undefined : 'Invalid JSON'}>
            <Textarea value={editTaskJson} onChange={(event) => setEditTaskJson(event.target.value)} rows={5} />
          </FormField>
          <div className="flex justify-end gap-2">
            <Button type="submit" disabled={isUpdating}>
              Save Changes
            </Button>
          </div>
        </Form>
      </Card>

      <div>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Jobs</h2>
            <p className="text-sm text-slate-500">GET /jobs</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'name', header: 'Name', render: (job) => job.name ?? '—' },
              { key: 'schedule_expr', header: 'Schedule', render: (job) => job.schedule_expr ?? '—' },
              { key: 'status', header: 'Status', render: (job) => job.status ?? '—' },
              {
                key: 'task_definition',
                header: 'Task',
                render: (job) => {
                  const taskDefinition = (job as { task_definition?: Record<string, unknown> }).task_definition ?? {};
                  return <code className="text-xs text-[#2978B3]">{JSON.stringify(taskDefinition, null, 2)}</code>;
                },
              },
              {
                key: 'actions',
                header: 'Actions',
                render: (job) => (
                  <div className="flex flex-wrap gap-2">
                    {job.id ? (
                      <>
                        <Link className="text-indigo-600 hover:underline" href={`/jobs/${job.id}`}>
                          View
                        </Link>
                        <button
                          type="button"
                          className="text-indigo-600 hover:underline"
                          onClick={() => beginEdit(job)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="text-rose-600 hover:underline"
                          onClick={() => handleDelete(job)}
                        >
                          Delete
                        </button>
                      </>
                    ) : (
                      <span className="text-slate-400">No ID</span>
                    )}
                  </div>
                ),
              },
            ]}
            data={jobs}
            emptyState={<p>No jobs scheduled.</p>}
          />
        </div>
      </div>

      <section>
        <h3 className="text-base font-semibold text-slate-900">Dead Letter Queue</h3>
        <DataTable
          columns={[
            { key: 'id', header: 'ID' },
            {
              key: 'failed_at',
              header: 'Failed At',
              render: (item) => formatDate(item.failed_at),
            },
            { key: 'error_message', header: 'Reason' },
          ]}
          data={dlq}
          emptyState={<p>No DLQ entries.</p>}
        />
      </section>
    </div>
  );
}
