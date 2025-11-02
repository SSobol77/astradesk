'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Select, Textarea } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { Connector } from '@/api/types';
import { useToast } from '@/hooks/useToast';

const CONNECTOR_TYPES = [
  { value: 'slack', label: 'Slack Bot' },
  { value: 'zendesk', label: 'Zendesk' },
  { value: 'salesforce', label: 'Salesforce' },
] as const;

export default function ToolsClient({ connectors }: { connectors: Connector[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [name, setName] = useState('');
  const [type, setType] = useState('');
  const [configJson, setConfigJson] = useState('{\n  "apiKey": "",\n  "settings": {}\n}');
  const [isSubmitting, setSubmitting] = useState(false);

  const parsedConfig = useMemo(() => {
    try {
      return configJson ? JSON.parse(configJson) : {};
    } catch {
      return null;
    }
  }, [configJson]);

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !type) {
      push({ title: 'Provide connector name and type', variant: 'error' });
      return;
    }
    if (!parsedConfig) {
      push({ title: 'Invalid config JSON', variant: 'error' });
      return;
    }
    setSubmitting(true);
    try {
      await openApiClient.tools.create({
        name: name.trim(),
        type,
        config: parsedConfig,
      });
      push({ title: 'Connector created', variant: 'success' });
      setName('');
      setType('');
      router.refresh();
    } catch (error) {
      console.error('Create connector failed', error);
      push({ title: 'Failed to create connector', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (connector: Connector) => {
    if (!connector.id) return;
    const confirmed = window.confirm(`Delete connector "${connector.name ?? connector.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.tools.delete(connector.id);
      push({ title: 'Connector deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete connector failed', error);
      push({ title: 'Failed to delete connector', variant: 'error' });
    }
  };

  const handleUpdate = async (connector: Connector) => {
    if (!connector.id) return;
    const newName = window.prompt('Connector name', connector.name ?? '') ?? connector.name ?? '';
    const newType = window.prompt('Connector type', connector.type ?? '') ?? connector.type ?? '';
    const newConfigInput = window.prompt(
      'Connector config JSON',
      JSON.stringify((connector as { config?: Record<string, unknown> }).config ?? {}, null, 2),
    );
    if (newConfigInput === null) return;
    try {
      const payload = {
        name: newName,
        type: newType,
        config: newConfigInput ? JSON.parse(newConfigInput) : {},
      };
      await openApiClient.tools.update(connector.id, payload);
      push({ title: 'Connector updated', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Update connector failed', error);
      push({ title: 'Failed to update connector', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Create Connector</h2>
        <p className="text-sm text-slate-500">POST /connectors</p>
        <Form className="mt-4" onSubmit={handleCreate}>
          <FormField label="Name">
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Slack Support Bot"
              required
            />
          </FormField>
          <FormField label="Type">
            <Select value={type} onChange={(event) => setType(event.target.value)} required>
              <option value="">Select type</option>
              {CONNECTOR_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField
            label="Config JSON"
            description="Provide the connector configuration."
            error={parsedConfig ? undefined : 'Invalid JSON'}
          >
            <Textarea
              value={configJson}
              onChange={(event) => setConfigJson(event.target.value)}
              rows={6}
            />
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              Create Connector
            </Button>
          </div>
        </Form>
      </Card>

      <div>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Connectors</h2>
            <p className="text-sm text-slate-500">GET /connectors</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'name', header: 'Name', render: (connector) => connector.name ?? '—' },
              { key: 'type', header: 'Type', render: (connector) => connector.type ?? '—' },
              { key: 'status', header: 'Status', render: (connector) => connector.status ?? '—' },
              {
                key: 'actions',
                header: 'Actions',
                render: (connector) => (
                  <div className="flex gap-2">
                    {connector.id ? (
                      <>
                        <Link className="text-indigo-600 hover:underline" href={`/tools/${connector.id}`}>
                          View
                        </Link>
                        <button
                          type="button"
                          className="text-indigo-600 hover:underline"
                          onClick={() => handleUpdate(connector)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="text-rose-600 hover:underline"
                          onClick={() => handleDelete(connector)}
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
            data={connectors}
            emptyState={<p>No connectors configured.</p>}
          />
        </div>
      </div>
    </div>
  );
}
