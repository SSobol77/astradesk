'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { Form, FormField, Textarea } from '@/components/primitives/Form';
import { useToast } from '@/hooks/useToast';
import { openApiClient } from '@/api/client';

export default function PolicyActions({ id }: { id: string }) {
  const { push } = useToast();
  const [input, setInput] = useState('{}');
  const [result, setResult] = useState<string>('');
  const [isSimulating, setIsSimulating] = useState(false);

  const simulate = async () => {
    try {
      setIsSimulating(true);
      const parsed = JSON.parse(input || '{}');
      const output = await openApiClient.policies.simulate(id, parsed);
      setResult(JSON.stringify(output, null, 2));
      push({ title: 'Simulation complete', variant: 'success' });
    } catch (error) {
      push({ title: 'Simulation failed', variant: 'error' });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="space-y-4">
      <Form onSubmit={(event) => event.preventDefault()}>
        <FormField label="Input JSON" description="POST /policies/{id}:simulate">
          <Textarea rows={6} value={input} onChange={(event) => setInput(event.target.value)} />
        </FormField>
        <Button type="button" onClick={simulate} disabled={isSimulating}>
          {isSimulating ? 'Simulating…' : 'Simulate'}
        </Button>
      </Form>
      {result ? (
        <pre className="rounded-xl border border-slate-200 bg-slate-900 p-4 text-xs text-slate-100">{result}</pre>
      ) : null}
    </div>
  );
}
