'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Card from '@/components/primitives/Card';
import Button from '@/components/primitives/Button';
import { Form, FormField, Input, Select, Textarea } from '@/components/primitives/Form';
import { openApiClient } from '@/api/client';
import type { Flow } from '@/api/types';
import { useToast } from '@/hooks/useToast';

const STATUS_OPTIONS: Array<{ value: Flow['status']; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
];

export default function FlowActions({ flow }: { flow: Flow }) {
  const router = useRouter();
  const { push } = useToast();
  const [name, setName] = useState(flow.name ?? '');
  const [status, setStatus] = useState<Flow['status'] | ''>(flow.status ?? '');
  const [configYaml, setConfigYaml] = useState(flow.config_yaml ?? '');
  const [isSubmitting, setSubmitting] = useState(false);

  const handleUpdateFlow = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!flow.id) return;
    if (!configYaml.trim()) {
      push({ title: 'Config YAML is required', variant: 'error' });
      return;
    }
    setSubmitting(true);
    try {
      await openApiClient.flows.update(flow.id, {
        name: name.trim() || undefined,
        status: status || undefined,
        config_yaml: configYaml,
      });
      push({ title: 'Flow updated', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Update flow failed', error);
      push({ title: 'Failed to update flow', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <h3 className="text-base font-semibold text-slate-900">Update Flow</h3>
      <Form
        className="mt-4"
        onSubmit={handleUpdateFlow}
      >
        <FormField label="Name">
          <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Support Router" />
        </FormField>
        <FormField label="Status">
          <Select value={status ?? ''} onChange={(event) => setStatus(event.target.value as Flow['status'] | '')}>
            <option value="">Keep current</option>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Config YAML">
          <Textarea
            value={configYaml}
            onChange={(event) => setConfigYaml(event.target.value)}
            rows={12}
            required
          />
        </FormField>
        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting}>
            Save changes
          </Button>
        </div>
      </Form>
    </Card>
  );
}
