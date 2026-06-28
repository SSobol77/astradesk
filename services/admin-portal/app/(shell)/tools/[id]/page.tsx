// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/tools/[id]/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/tools/[id]/page.tsx.
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
import { notFound } from 'next/navigation';
import ConnectorActions from './ConnectorActions';

async function getConnector(id: string) {
  try {
    return await openApiClient.tools.get(id);
  } catch (error) {
    console.error('Failed to load connector', error);
    return null;
  }
}

type ConnectorDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ConnectorDetailPage({ params }: ConnectorDetailPageProps) {
  const { id } = await params;
  const connector = await getConnector(id);

  if (!connector || !connector.id) {
    notFound();
  }

  const connectorId = connector.id;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{connector.name ?? 'Unnamed connector'}</h2>
            <p className="text-sm text-slate-500">Type: {connector.type ?? '—'}</p>
          </div>
          <ConnectorActions id={connectorId} />
        </div>
      </Card>
      <JsonViewer value={connector} />
    </div>
  );
}
