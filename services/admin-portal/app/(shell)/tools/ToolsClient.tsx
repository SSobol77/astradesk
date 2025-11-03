'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { TableColumn } from '@/components/data/DataTable';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Select, Textarea } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { Connector } from '@/api/types';
import { useToast } from '@/hooks/useToast';
import { ApiError } from '@/lib/api';

const TOOL_TYPES = [
  { value: 'slack', label: 'Slack Bot' },
  { value: 'zendesk', label: 'Zendesk' },
  { value: 'salesforce', label: 'Salesforce' },
] as const;

export default function ToolsClient({ tools }: { tools: Connector[] }) {
  const router = useRouter();
  const { push } = useToast();
  
  const [name, setName] = useState('');
  const [type, setType] = useState<typeof TOOL_TYPES[number]['value']>(TOOL_TYPES[0].value);
  const [config, setConfig] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name) {
      push({ title: 'Provide tool name', variant: 'error' });
      return;
    }

    let parsedConfig: Record<string, unknown>;
    try {
      parsedConfig = JSON.parse(config || '{}');
    } catch {
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
      push({ title: 'Tool created successfully', variant: 'success' });
      setName('');
      setConfig('');
      router.refresh();
    } catch (error) {
      console.error('Create tool failed:', error);
      push({
        title: 'Failed to create tool',
        description: error instanceof ApiError ? error.problem?.detail : 'Network error occurred',
        variant: 'error'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id?: string) => {
    if (!id) return;
    try {
      await openApiClient.tools.delete(id);
      push({ title: 'Tool deleted successfully', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete tool failed:', error);
      push({
        title: 'Failed to delete tool',
        description: error instanceof ApiError ? error.problem?.detail : 'Network error occurred',
        variant: 'error'
      });
    }
  };

  const columns: Array<TableColumn<Connector>> = [
    {
      key: 'name',
      header: 'Name',
      render: (tool) => (
        <Link 
          href={`/tools/${tool.id}`}
          className="text-blue-600 hover:text-blue-800"
        >
          {tool.name}
        </Link>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (tool) => {
        const type = TOOL_TYPES.find((t) => t.value === tool.type);
        return type?.label ?? tool.type;
      },
    },
    {
      key: 'actions',
      header: '',
      render: (tool) => (
        <Button
          variant="ghost"
          className="text-sm px-2 py-1"
          onClick={() => handleDelete(tool.id)}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="mb-8">
        <Card>
          <Form onSubmit={handleCreate}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Name">
                <Input
                  name="name"
                  placeholder="Tool name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </FormField>
              <FormField label="Type">
                <Select
                  name="type"
                  value={type}
                  onChange={(e) => setType(e.target.value as typeof TOOL_TYPES[number]['value'])}
                >
                  {TOOL_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </Select>
              </FormField>
              <div className="sm:col-span-2">
                <FormField label="Configuration">
                  <Textarea
                    name="config"
                    placeholder="Tool configuration (JSON)"
                    value={config}
                    onChange={(e) => setConfig(e.target.value)}
                    rows={4}
                  />
                </FormField>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <Button type="submit" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Tool'}
              </Button>
            </div>
          </Form>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={tools}
      />
    </>
  );
}