'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { useToast } from '@/hooks/useToast';
import { apiBaseUrl } from '@/lib/env';
import type { IntentGraph } from '@/api/types';

type IntentGraphActionsProps = {
  graph: IntentGraph | null;
};

export function IntentGraphActions({ graph }: IntentGraphActionsProps) {
  const { push } = useToast();
  const [isExporting, setIsExporting] = useState(false);

  const downloadJson = (data: unknown) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `intent-graph-${timestamp}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      if (graph) {
        downloadJson(graph);
        return;
      }

      const response = await fetch(`${apiBaseUrl}/api/admin/v1/intents/graph`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Export failed with status ${response.status}`);
      }

      const json = await response.json();
      downloadJson(json);
    } catch (error) {
      console.error('Intent graph export failed', error);
      push({ title: 'Failed to export intent graph', variant: 'error' });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Button type="button" onClick={handleExport} disabled={isExporting}>
      {isExporting ? 'Exporting…' : 'Export JSON'}
    </Button>
  );
}

