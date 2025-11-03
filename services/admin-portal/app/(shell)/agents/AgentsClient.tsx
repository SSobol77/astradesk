'use client';

import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import Modal from '@/components/primitives/Modal';
import { Form, FormField, Input, Select } from '@/components/primitives/Form';
import { openApiClient } from '@/api/client';
import type { Agent } from '@/api/types';
import { useToast } from '@/hooks/useToast';

const ENV_OPTIONS: Array<{ value: Agent['env']; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'dev', label: 'Development' },
  { value: 'staging', label: 'Staging' },
  { value: 'prod', label: 'Production' },
];

type AgentFormState = {
  name: string;
  version: string;
  env: Agent['env'] | '';
  status: Agent['status'] | '';
  configJson: string;
};

const defaultFormState: AgentFormState = {
  name: '',
  version: '',
  env: '',
  status: '',
  configJson: '{\n  "model": "gpt-4"\n}',
};

export default function AgentsClient({ agents }: { agents: Agent[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [isModalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [formState, setFormState] = useState<AgentFormState>(defaultFormState);
  const [isSubmitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (modalMode === 'create') {
      setFormState(defaultFormState);
      setSelectedAgent(null);
      return;
    }
    if (selectedAgent) {
      setFormState({
        name: selectedAgent.name ?? '',
        version: selectedAgent.version ?? '',
        env: selectedAgent.env ?? '',
        status: selectedAgent.status ?? '',
        configJson: JSON.stringify(selectedAgent.config ?? {}, null, 2),
      });
    }
  }, [modalMode, selectedAgent]);

  const closeModal = () => {
    setModalOpen(false);
    setSelectedAgent(null);
    setFormState(defaultFormState);
  };

  const openCreateModal = () => {
    setModalMode('create');
    setFormState(defaultFormState);
    setModalOpen(true);
  };

  const openEditModal = (agent: Agent) => {
    setModalMode('edit');
    setSelectedAgent(agent);
    setModalOpen(true);
  };

  const handleInputChange =
    (key: keyof AgentFormState) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormState((current) => ({ ...current, [key]: event.target.value }));
  };

  const handleConfigChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setFormState((current) => ({ ...current, configJson: event.target.value }));
  };

  const parsedConfig = useMemo(() => {
    try {
      return formState.configJson ? JSON.parse(formState.configJson) : {};
    } catch {
      return null;
    }
  }, [formState.configJson]);

  const handleSaveAgent = async () => {
    if (!parsedConfig) {
      push({ title: 'Invalid config JSON', variant: 'error' });
      return;
    }
    if (!formState.name.trim()) {
      push({ title: 'Name is required', variant: 'error' });
      return;
    }
    const payload = {
      name: formState.name.trim(),
      config: {
        ...parsedConfig,
        version: formState.version || undefined,
        env: formState.env || undefined,
        status: formState.status || undefined,
      },
    };
    setSubmitting(true);
    try {
      if (modalMode === 'create') {
        await openApiClient.agents.create(payload);
        push({ title: 'Agent created', variant: 'success' });
      } else if (selectedAgent?.id) {
        await openApiClient.agents.update(selectedAgent.id, payload);
        push({ title: 'Agent updated', variant: 'success' });
      }
      closeModal();
      router.refresh();
    } catch (error) {
      console.error('Agent save failed', error);
      push({ title: 'Failed to save agent', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (agent: Agent) => {
    if (!agent.id) return;
  const confirmed = globalThis.confirm?.(`Delete agent "${agent.name ?? agent.id}"?`);
    if (!confirmed) return;
    try {
      await openApiClient.agents.delete(agent.id);
      push({ title: 'Agent deleted', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete agent failed', error);
      push({ title: 'Failed to delete agent', variant: 'error' });
    }
  };

  const handleTest = async (agent: Agent) => {
    if (!agent.id) return;
  const input = globalThis.prompt?.('Enter a test input message for the agent');
    if (input === null) return;
    try {
      const result = await openApiClient.agents.test(agent.id, input);
      push({ title: 'Test completed', description: JSON.stringify(result, null, 2), variant: 'info' });
    } catch (error) {
      console.error('Test agent failed', error);
      push({ title: 'Failed to test agent', variant: 'error' });
    }
  };

  const handleClone = async (agent: Agent) => {
    if (!agent.id) return;
    try {
      const clone = await openApiClient.agents.clone(agent.id);
      push({ title: 'Agent cloned', description: clone.name ?? clone.id ?? 'New agent created', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Clone agent failed', error);
      push({ title: 'Failed to clone agent', variant: 'error' });
    }
  };

  const handlePromote = async (agent: Agent) => {
    if (!agent.id) return;
    try {
      const promoted = await openApiClient.agents.promote(agent.id);
      push({ title: 'Agent promoted', description: promoted.status ?? 'Promotion successful', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Promote agent failed', error);
      push({ title: 'Failed to promote agent', variant: 'error' });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Agents</h2>
          <p className="text-sm text-slate-500">Backed by GET /agents</p>
        </div>
        <Button onClick={openCreateModal}>New Agent</Button>
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
                <Button variant="ghost" type="button" onClick={() => openEditModal(agent)}>
                  Edit
                </Button>
                <Button variant="ghost" type="button" onClick={() => handleTest(agent)}>
                  Test
                </Button>
                <Button variant="ghost" type="button" onClick={() => handleClone(agent)}>
                  Clone
                </Button>
                <Button variant="ghost" type="button" onClick={() => handlePromote(agent)}>
                  Promote
                </Button>
                <Button variant="ghost" type="button" onClick={() => handleDelete(agent)}>
                  Delete
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
        isOpen={isModalOpen}
        onClose={closeModal}
        primaryActionLabel="Save"
        onPrimaryAction={handleSaveAgent}
        isPrimaryDisabled={isSubmitting}
      >
        <Form>
          <FormField label="Name">
            <Input
              value={formState.name}
              onChange={handleInputChange('name')}
              required
            />
          </FormField>
          <FormField label="Version">
            <Input
              value={formState.version}
              onChange={handleInputChange('version')}
              placeholder="v1.0.0"
            />
          </FormField>
          <FormField label="Environment">
            <Select value={formState.env} onChange={handleInputChange('env')}>
              <option value="">Select environment</option>
              {ENV_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Status">
            <Input value={formState.status} onChange={handleInputChange('status')} placeholder="active" />
          </FormField>
          <FormField
            label="Config JSON"
            description="Provide the agent configuration payload. Example: { &quot;model&quot;: &quot;gpt-4&quot; }"
            error={parsedConfig ? undefined : 'Invalid JSON'}
          >
            <textarea
              className="h-40 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500"
              value={formState.configJson}
              onChange={handleConfigChange}
            />
          </FormField>
        </Form>
      </Modal>
    </div>
  );
}
