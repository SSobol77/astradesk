// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/tools/[id]/ConnectorActions.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/tools/[id]/ConnectorActions.tsx.
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
