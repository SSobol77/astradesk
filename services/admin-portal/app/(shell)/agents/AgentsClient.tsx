'use client';

import { useState } from 'react';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import Modal from '@/components/primitives/Modal';
import { Form, FormField, Input, Select, Textarea } from '@/components/primitives/Form';
import type { Agent } from '@/openapi/openapi-types';

const ENV_OPTIONS: Array<{ value: Agent['env']; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'dev', label: 'Development' },
  { value: 'staging', label: 'Staging' },
  { value: 'prod', label: 'Production' },
];

export default function AgentsClient({ agents }: { agents: Agent[] }) {
  const [isCreateOpen, setCreateOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');

  const openCreate = () => {
    setModalMode('create');
    setCreateOpen(true);
  };

  const openEdit = (agent: Agent) => {
    setSelectedAgent(agent);
    setModalMode('edit');
    setCreateOpen(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Agents</h2>
          <p className="text-sm text-slate-500">Backed by GET /agents</p>
        </div>
        <Button onClick={openCreate}>New Agent</Button>
      </div>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'version', header: 'Version' },
          { key: 'env', header: 'Environment' },
          { key: 'status', header: 'Status' },
          {
            key: 'actions',
            header: 'Actions',
            render: (agent) => (
              <div className="flex flex-wrap gap-2">
                <Button variant="ghost" type="button" onClick={() => openEdit(agent)}>
                  Edit
                </Button>
                <Button variant="ghost" type="button" onClick={() => console.log('Test agent', agent.id)}>
                  Test
                </Button>
                <Button variant="ghost" type="button" onClick={() => console.log('Clone agent', agent.id)}>
                  Clone
                </Button>
                <Button variant="ghost" type="button" onClick={() => console.log('Promote agent', agent.id)}>
                  Promote
                </Button>
              </div>
            ),
          },
        ]}
        data={agents}
        emptyState={<p>No agents available yet.</p>}
      />

      <Modal
        title={modalMode === 'create' ? 'New Agent' : `Edit ${selectedAgent?.name ?? ''}`}
        isOpen={isCreateOpen}
        onClose={() => {
          setCreateOpen(false);
          setSelectedAgent(null);
        }}
        primaryActionLabel="Save"
        onPrimaryAction={() => console.log('Submit form to OpenAPI endpoint')}
      >
        <Form>
          <FormField label="Name">
            <Input defaultValue={selectedAgent?.name} required />
          </FormField>
          <FormField label="Version">
            <Input defaultValue={selectedAgent?.version} required />
          </FormField>
          <FormField label="Environment">
            <Select defaultValue={selectedAgent?.env} required>
              <option value="" disabled>
                Select environment
              </option>
              {ENV_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Status">
            <Input defaultValue={selectedAgent?.status} />
          </FormField>

        </Form>
      </Modal>
    </div>
  );
}
tarea defaultValue={selectedAgent?.description} rows={3} />
          </FormField>
        </Form>
      </Modal>
    </div>
  );
}
