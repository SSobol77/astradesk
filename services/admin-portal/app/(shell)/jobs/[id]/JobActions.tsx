// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/jobs/[id]/JobActions.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/jobs/[id]/JobActions.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { useToast } from '@/hooks/useToast';
import { openApiClient } from '@/api/client';

export default function JobActions({ id }: { id: string }) {
  const { push } = useToast();
  const [isTriggering, setIsTriggering] = useState(false);
  const [isPausing, setIsPausing] = useState(false);
  const [isResuming, setIsResuming] = useState(false);

  const trigger = async () => {
    try {
      setIsTriggering(true);
      const result = await openApiClient.jobs.trigger(id);
      push({ title: 'Job triggered', description: result.run_id ?? 'Accepted', variant: 'success' });
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

  const resume = async () => {
    try {
      setIsResuming(true);
      await openApiClient.jobs.resume(id);
      push({ title: 'Job resume request sent', variant: 'success' });
    } catch (error) {
      push({ title: 'Resume failed', variant: 'error' });
    } finally {
      setIsResuming(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" onClick={trigger} disabled={isTriggering}>
        {isTriggering ? 'Triggering…' : 'Trigger Now'}
      </Button>
      <Button type="button" variant="secondary" onClick={pause} disabled={isPausing}>
        {isPausing ? 'Pausing…' : 'Pause'}
      </Button>
      <Button type="button" variant="ghost" onClick={resume} disabled={isResuming}>
        {isResuming ? 'Resuming…' : 'Resume'}
      </Button>
    </div>
  );
}
