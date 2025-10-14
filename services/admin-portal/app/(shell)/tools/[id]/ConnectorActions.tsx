'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { useToast } from '@/hooks/useToast';
import { openApiClient } from '@/openapi/openapi-client';

export default function ConnectorActions({ id }: { id: string }) {
  const { push } = useToast();
  const [isTesting, setIsTesting] = useState(false);
  const [isProbing, setIsProbing] = useState(false);

  const runTest = async () => {
    try {
      setIsTesting(true);
      await openApiClient.tools.test(id);
      push({ title: 'Connector test passed', variant: 'success' });
    } catch (error) {
      push({ title: 'Connector test failed', variant: 'error' });
    } finally {
      setIsTesting(false);
    }
  };

  const runProbe = async () => {
    try {
      setIsProbing(true);
      const result = await openApiClient.tools.probe(id);
      push({ title: 'Probe completed', description: `Latency: ${result.latency_ms}ms`, variant: 'info' });
    } catch (error) {
      push({ title: 'Probe failed', variant: 'error' });
    } finally {
      setIsProbing(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" onClick={runTest} disabled={isTesting}>
        {isTesting ? 'Testing…' : 'Test Connector'}
      </Button>
      <Button type="button" variant="secondary" onClick={runProbe} disabled={isProbing}>
        {isProbing ? 'Probing…' : 'Probe Connector'}
      </Button>
    </div>
  );
}
