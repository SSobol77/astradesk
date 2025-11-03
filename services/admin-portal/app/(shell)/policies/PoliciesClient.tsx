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
import { useConfirm } from '@/hooks/useConfirm';

export default function PoliciesClient({ policies }: { policies: Policy[] }) {
  const router = useRouter();
  const { push } = useToast();
  const { confirm, ConfirmDialog } = useConfirm();

  const [name, setName] = useState('');
  const [rego, setRego] = useState('package astra.policy\n\nallow { true }');
  const [isCreating, setCreating] = useState(false);

  const [editId, setEditId] = useState('');
  const [editName, setEditName] = useState('');
  const [editRego, setEditRego] = useState('');
  const [isUpdating, setUpdating] = useState(false);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    const trimmedName = name.trim();
    const trimmedRego = rego.trim();
    
    if (!trimmedName) {
      push({ title: 'Name is required', description: 'Please provide a policy name', variant: 'error' });
      return;
    }
    
    if (!trimmedRego) {
      push({ title: 'Rego text is required', description: 'Please provide the policy definition', variant: 'error' });
      return;
    }
    
    setCreating(true);
    try {
      await openApiClient.policies.create({
        name: trimmedName,
        rego_text: trimmedRego,
      });
      
      push({ 
        title: 'Policy created successfully',
        description: `Policy "${trimmedName}" has been created`,
        variant: 'success' 
      });
      
      // Reset form
      setName('');
      setRego('package astra.policy\n\nallow { true }');
      router.refresh();
    } catch (error) {
      console.error('Create policy failed:', error);
      push({ 
        title: 'Failed to create policy',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        variant: 'error'
      });
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
    
    const trimmedId = editId.trim();
    const trimmedRego = editRego.trim();
    const trimmedName = editName.trim();
    
    if (!trimmedId) {
      push({ 
        title: 'Invalid policy',
        description: 'No policy selected for update',
        variant: 'error'
      });
      return;
    }
    
    if (!trimmedRego) {
      push({ 
        title: 'Rego text is required',
        description: 'Please provide the policy definition',
        variant: 'error'
      });
      return;
    }
    
    setUpdating(true);
    try {
      await openApiClient.policies.update(trimmedId, {
        name: trimmedName || 'New Policy',  // Default name if empty
        rego_text: trimmedRego,
      });
      
      push({ 
        title: 'Policy updated successfully',
        description: `Policy "${trimmedName || 'New Policy'}" has been updated`,
        variant: 'success'
      });
      
      router.refresh();
    } catch (error) {
      console.error('Update policy failed:', error);
      push({ 
        title: 'Failed to update policy',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async (policy: Policy) => {
    if (!policy.id) return;
    
    const confirmed = await confirm({
      title: 'Delete Policy',
      message: `Are you sure you want to delete policy "${policy.name ?? policy.id}"?`,
      confirmText: 'Delete',
      cancelText: 'Cancel'
    });
    
    if (!confirmed) return;
    
    try {
      await openApiClient.policies.delete(policy.id);
      push({ title: 'Policy deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete policy failed:', error);
      push({ 
        title: 'Failed to delete policy',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        variant: 'error'
      });
    }
  };

  return (
    <div className="space-y-6">
      {ConfirmDialog}
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
