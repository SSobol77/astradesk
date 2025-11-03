'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Textarea } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { Flow } from '@/api/types';
import { useToast } from '@/hooks/useToast';

export default function FlowsClient({ flows }: { flows: Flow[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [name, setName] = useState('');
  const [graphJson, setGraphJson] = useState('{\n  "nodes": [],\n  "edges": []\n}');
  const [isSubmitting, setSubmitting] = useState(false);

  const parsedGraph = useMemo(() => {
    try {
      return graphJson ? JSON.parse(graphJson) : {};
    } catch {
      return null;
    }
  }, [graphJson]);

  const handleCreateFlow = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      push({ title: 'Name is required', variant: 'error' });
      return;
    }
    if (!parsedGraph) {
      push({ title: 'Invalid graph JSON', variant: 'error' });
      return;
    }
    setSubmitting(true);
    try {
      await openApiClient.flows.create({
        name: name.trim(),
        graph: parsedGraph,
      });
      push({ title: 'Flow created', variant: 'success' });
      setName('');
      router.refresh();
    } catch (error) {
      console.error('Create flow failed', error);
      push({ title: 'Failed to create flow', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (flow: Flow) => {
    if (!flow.id) return;
  const confirmed = globalThis.confirm?.(`Delete flow "${flow.name ?? flow.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.flows.delete(flow.id);
      push({ title: 'Flow deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete flow failed', error);
      push({ title: 'Failed to delete flow', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Create Flow</h2>
        <p className="text-sm text-slate-500">POST /flows</p>
        <Form
          className="mt-4"
          onSubmit={handleCreateFlow}
        >
          <FormField label="Name">
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Support Router"
              required
            />
          </FormField>
          <FormField
            label="Graph JSON"
            description="Provide the graph definition for the flow."
            error={parsedGraph ? undefined : 'Invalid JSON'}
          >
            <Textarea
              value={graphJson}
              onChange={(event) => setGraphJson(event.target.value)}
              rows={6}
            />
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              Create Flow
            </Button>
          </div>
        </Form>
      </Card>

      <div>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Flows</h2>
            <p className="text-sm text-slate-500">GET /flows</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'name', header: 'Name' },
              { key: 'id', header: 'ID' },
              {
                key: 'actions',
                header: 'Actions',
                render: (flow) => (
                  <div className="flex gap-2">
                    <Link className="text-indigo-600 hover:underline" href={`/flows/${flow.id}`}>
                      View
                    </Link>
                    <button
                      type="button"
                      className="text-rose-600 hover:underline"
                      onClick={() => handleDelete(flow)}
                    >
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
            data={flows}
            emptyState={<p>No flows yet.</p>}
          />
        </div>
      </div>
    </div>
  );
}
