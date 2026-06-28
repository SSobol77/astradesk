// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/runs/[id]/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/runs/[id]/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { formatCurrency, formatDate, formatLatency } from '@/lib/format';
import { openApiClient } from '@/api/client';
import type { Run } from '@/api/types';
import { notFound } from 'next/navigation';

async function getRun(id: string): Promise<Run | null> {
  try {
    return await openApiClient.runs.get(id);
  } catch (error) {
    console.error('Failed to load run', error);
    return null;
  }
}

type RunDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { id } = await params;
  const run = await getRun(id);

  if (!run) {
    notFound();
  }

  const runId = run.id ?? id;

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">Run {runId}</h2>
        <dl className="mt-4 grid gap-4 md:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Agent</dt>
            <dd className="mt-1 text-sm text-slate-700">{run.agent_id ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</dt>
            <dd className="mt-1 text-sm text-slate-700">{run.status ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Latency</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatLatency(run.latency_ms ?? null)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Cost</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatCurrency(run.cost_usd ?? null)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Created</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatDate(run.created_at ?? null)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Completed</dt>
            <dd className="mt-1 text-sm text-slate-700">{formatDate(run.completed_at ?? null)}</dd>
          </div>
        </dl>
      </Card>
      <JsonViewer value={run} />
    </div>
  );
}
