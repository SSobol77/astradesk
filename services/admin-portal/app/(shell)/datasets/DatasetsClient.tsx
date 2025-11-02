'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Select } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { Dataset } from '@/api/types';
import { useToast } from '@/hooks/useToast';

const DATASET_TYPES: Array<{ value: Dataset['type']; label: string }> = [
  { value: 's3', label: 'Amazon S3' },
  { value: 'postgres', label: 'Postgres' },
  { value: 'git', label: 'Git Repository' },
];

export default function DatasetsClient({ datasets }: { datasets: Dataset[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [name, setName] = useState('');
  const [type, setType] = useState<Dataset['type'] | ''>('');
  const [isSubmitting, setSubmitting] = useState(false);

  const handleCreateDataset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !type) {
      push({ title: 'Provide name and type', variant: 'error' });
      return;
    }
    setSubmitting(true);
    try {
      await openApiClient.datasets.create({
        name: name.trim(),
        type,
      });
      push({ title: 'Dataset created', variant: 'success' });
      setName('');
      setType('');
      router.refresh();
    } catch (error) {
      console.error('Create dataset failed', error);
      push({ title: 'Failed to create dataset', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (dataset: Dataset) => {
    if (!dataset.id) return;
    const confirmed = window.confirm(`Delete dataset "${dataset.name ?? dataset.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.datasets.delete(dataset.id);
      push({ title: 'Dataset deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete dataset failed', error);
      push({ title: 'Failed to delete dataset', variant: 'error' });
    }
  };

  const handleReindex = async (dataset: Dataset) => {
    if (!dataset.id) return;
    try {
      await openApiClient.datasets.reindex(dataset.id);
      push({ title: 'Reindex started', description: 'A background job was triggered.', variant: 'info' });
    } catch (error) {
      console.error('Reindex dataset failed', error);
      push({ title: 'Failed to reindex dataset', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Create Dataset</h2>
        <p className="text-sm text-slate-500">POST /datasets</p>
        <Form className="mt-4" onSubmit={handleCreateDataset}>
          <FormField label="Name">
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Knowledge Base"
              required
            />
          </FormField>
          <FormField label="Type">
            <Select value={type} onChange={(event) => setType(event.target.value as Dataset['type'])} required>
              <option value="">Select type</option>
              {DATASET_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              Create Dataset
            </Button>
          </div>
        </Form>
      </Card>

      <div>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Datasets</h2>
            <p className="text-sm text-slate-500">GET /datasets</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'name', header: 'Name' },
              { key: 'type', header: 'Type' },
              { key: 'indexing_status', header: 'Indexing Status' },
              {
                key: 'actions',
                header: 'Actions',
                render: (dataset) => (
                  <div className="flex gap-2">
                    <Link className="text-indigo-600 hover:underline" href={`/datasets/${dataset.id}`}>
                      View
                    </Link>
                    <button
                      type="button"
                      className="text-indigo-600 hover:underline"
                      onClick={() => handleReindex(dataset)}
                    >
                      Reindex
                    </button>
                    <button
                      type="button"
                      className="text-rose-600 hover:underline"
                      onClick={() => handleDelete(dataset)}
                    >
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
            data={datasets}
            emptyState={<p>No datasets yet.</p>}
          />
        </div>
      </div>
    </div>
  );
}
