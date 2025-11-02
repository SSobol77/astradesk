'use client';

import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { formatDate } from '@/lib/format';
import { openApiClient } from '@/api/client';
import type { Secret } from '@/api/types';
import { useToast } from '@/hooks/useToast';

type SecretFormState = {
  name: string;
  value: string;
  type: string;
};

const defaultFormState: SecretFormState = {
  name: '',
  value: '',
  type: '',
};

export default function SecretsClient({ secrets }: { secrets: Secret[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [formState, setFormState] = useState(defaultFormState);
  const [isSubmitting, setSubmitting] = useState(false);

  const updateField = (key: keyof SecretFormState) => (event: ChangeEvent<HTMLInputElement>) => {
    setFormState((current) => ({ ...current, [key]: event.target.value }));
  };

  const handleCreateSecret = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.name.trim() || !formState.value.trim()) {
      push({ title: 'Provide name and value', variant: 'error' });
      return;
    }
    setSubmitting(true);
    try {
      await openApiClient.secrets.create({
        name: formState.name.trim(),
        value: formState.value,
        type: formState.type.trim() || undefined,
      });
      push({ title: 'Secret created', variant: 'success' });
      setFormState(defaultFormState);
      router.refresh();
    } catch (error) {
      console.error('Create secret failed', error);
      push({ title: 'Failed to create secret', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRotate = async (secret: Secret) => {
    if (!secret.id) return;
    try {
      await openApiClient.secrets.rotate(secret.id);
      push({ title: 'Rotation triggered', variant: 'info' });
      router.refresh();
    } catch (error) {
      console.error('Rotate secret failed', error);
      push({ title: 'Failed to rotate secret', variant: 'error' });
    }
  };

  const handleDisable = async (secret: Secret) => {
    if (!secret.id) return;
    const confirmed = window.confirm(`Disable secret "${secret.name ?? secret.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.secrets.disable(secret.id);
      push({ title: 'Secret disabled', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Disable secret failed', error);
      push({ title: 'Failed to disable secret', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Create Secret</h2>
        <p className="text-sm text-slate-500">POST /secrets</p>
        <Form className="mt-4" onSubmit={handleCreateSecret}>
          <FormField label="Name">
            <Input value={formState.name} onChange={updateField('name')} placeholder="openai-api-key" required />
          </FormField>
          <FormField label="Value">
            <Input
              type="password"
              value={formState.value}
              onChange={updateField('value')}
              placeholder="sk-..."
              required
            />
          </FormField>
          <FormField label="Type">
            <Input value={formState.type} onChange={updateField('type')} placeholder="api-key" />
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              Save Secret
            </Button>
          </div>
        </Form>
      </Card>

      <div>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Secrets</h2>
            <p className="text-sm text-slate-500">GET /secrets</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'name', header: 'Name' },
              { key: 'type', header: 'Type' },
              {
                key: 'last_used_at',
                header: 'Last Used',
                render: (secret) => formatDate(secret.last_used_at ?? null),
              },
              {
                key: 'actions',
                header: 'Actions',
                render: (secret) => (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="text-indigo-600 hover:underline"
                      onClick={() => handleRotate(secret)}
                    >
                      Rotate
                    </button>
                    <button
                      type="button"
                      className="text-rose-600 hover:underline"
                      onClick={() => handleDisable(secret)}
                    >
                      Disable
                    </button>
                  </div>
                ),
              },
            ]}
            data={secrets}
            emptyState={<p>No secrets recorded.</p>}
          />
        </div>
      </div>
    </div>
  );
}
