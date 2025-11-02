'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Textarea } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { Policy } from '@/api/types';
import { useToast } from '@/hooks/useToast';

export default function PoliciesClient({ policies }: { policies: Policy[] }) {
  const router = useRouter();
  const { push } = useToast();

  const [name, setName] = useState('');
  const [rego, setRego] = useState('package astra.policy\n\nallow { true }');
  const [isCreating, setCreating] = useState(false);

  const [editId, setEditId] = useState('');
  const [editName, setEditName] = useState('');
  const [editRego, setEditRego] = useState('');
  const [isUpdating, setUpdating] = useState(false);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !rego.trim()) {
      push({ title: 'Provide name and Rego text', variant: 'error' });
      return;
    }
    setCreating(true);
    try {
      await openApiClient.policies.create({
        name: name.trim(),
        rego_text: rego,
      });
      push({ title: 'Policy created', variant: 'success' });
      setName('');
      setRego('package astra.policy\n\nallow { true }');
      router.refresh();
    } catch (error) {
      console.error('Create policy failed', error);
      push({ title: 'Failed to create policy', variant: 'error' });
    } finally {
      setCreating(false);
    }
  };

  const beginEdit = (policy: Policy) => {
    if (!policy.id) return;
    setEditId(policy.id);
    setEditName(policy.name ?? '');
    setEditRego(policy.rego_text ?? '');
  };

  const handleUpdate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editId.trim() || !editRego.trim()) {
      push({ title: 'Provide policy ID and Rego text', variant: 'error' });
      return;
    }
    setUpdating(true);
    try {
      await openApiClient.policies.update(editId, {
        name: editName.trim() || undefined,
        rego_text: editRego,
      });
      push({ title: 'Policy updated', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Update policy failed', error);
      push({ title: 'Failed to update policy', variant: 'error' });
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async (policy: Policy) => {
    if (!policy.id) return;
    const confirmed = window.confirm(`Delete policy "${policy.name ?? policy.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.policies.delete(policy.id);
      push({ title: 'Policy deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete policy failed', error);
      push({ title: 'Failed to delete policy', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Create Policy</h2>
        <p className="text-sm text-slate-500">POST /policies</p>
        <Form className="mt-4" onSubmit={handleCreate}>
          <FormField label="Name">
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="allow-support" required />
          </FormField>
          <FormField label="Rego Text">
            <Textarea value={rego} onChange={(event) => setRego(event.target.value)} rows={8} required />
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isCreating}>
              Create Policy
            </Button>
          </div>
        </Form>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Update Policy</h2>
        <p className="text-sm text-slate-500">{'PUT /policies/{id}'}</p>
        <Form className="mt-4" onSubmit={handleUpdate}>
          <FormField label="Policy ID">
            <Input value={editId} onChange={(event) => setEditId(event.target.value)} placeholder="pol_123" required />
          </FormField>
          <FormField label="Name">
            <Input value={editName} onChange={(event) => setEditName(event.target.value)} placeholder="allow-support" />
          </FormField>
          <FormField label="Rego Text">
            <Textarea value={editRego} onChange={(event) => setEditRego(event.target.value)} rows={8} required />
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isUpdating}>
              Save Changes
            </Button>
          </div>
        </Form>
      </Card>

      <div>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Policies</h2>
            <p className="text-sm text-slate-500">GET /policies</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'name', header: 'Name' },
              {
                key: 'actions',
                header: 'Actions',
                render: (policy: Policy) => (
                  <div className="flex gap-2">
                    <Link className="text-indigo-600 hover:underline" href={`/policies/${policy.id}`}>
                      View
                    </Link>
                    <button type="button" className="text-indigo-600 hover:underline" onClick={() => beginEdit(policy)}>
                      Edit
                    </button>
                    <button type="button" className="text-rose-600 hover:underline" onClick={() => handleDelete(policy)}>
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
            data={policies}
            emptyState={<p>No policies defined.</p>}
          />
        </div>
      </div>
    </div>
  );
}
