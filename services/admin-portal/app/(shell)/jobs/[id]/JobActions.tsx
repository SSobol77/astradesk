'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { useToast } from '@/hooks/useToast';
import { openApiClient } from '@/openapi/openapi-client';

export default function JobActions({ id }: { id: string }) {
  const { push } = useToast();
  const [isTriggering, setIsTriggering] = useState(false);
  const [isPausing, setIsPausing] = useState(false);

  const trigger = async () => {
    try {
      setIsTriggering(true);
      const result = await openApiClient.jobs.trigger(id);
      push({ title: 'Job triggered', description: result.run_id, variant: 'success' });
    } catch (error) {
      push({ title: 'Trigger failed', variant: 'error' });
    } finally {
      setIsTriggering(false);
    }
  };

  const pause = async () => {
    try {
      setIsPausing(true);
      await openApiClient.jobs.pause(id);
      push({ title: 'Job pause request sent', variant: 'info' });
    } catch (error) {
      push({ title: 'Pause failed', variant: 'error' });
    } finally {
      setIsPausing(false);
    }
  };

  return (
    <div className="flex gap-2">
      <Button type="button" onClick={trigger} disabled={isTriggering}>
        {isTriggering ? 'Triggering…' : 'Trigger Now'}
      </Button>
      <Button type="button" variant="secondary" onClick={pause} disabled={isPausing}>
        {isPausing ? 'Pausing…' : 'Pause / Resume'}
      </Button>
    </div>
  );
}
