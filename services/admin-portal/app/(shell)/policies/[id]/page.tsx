// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/policies/[id]/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/policies/[id]/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { openApiClient } from '@/api/client';
import type { Policy } from '@/api/types';
import { notFound } from 'next/navigation';
import PolicyActions from './PolicyActions';

async function getPolicy(id: string): Promise<Policy | null> {
  try {
    return await openApiClient.policies.get(id);
  } catch (error) {
    console.error('Failed to load policy', error);
    return null;
  }
}

type PolicyDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function PolicyDetailPage({ params }: PolicyDetailPageProps) {
  const { id } = await params;
  const policy = await getPolicy(id);

  if (!policy || !policy.id) {
    notFound();
  }

  const policyId = policy.id;

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold text-slate-900">{policy.name}</h2>
      </Card>
      <PolicyActions id={policyId} />
      <JsonViewer value={policy} />
    </div>
  );
}
