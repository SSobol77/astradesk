// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/datasets/[id]/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/datasets/[id]/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import JsonViewer from '@/components/misc/JsonViewer';
import { Tabs } from '@/components/primitives/Tabs';
import { openApiClient } from '@/api/client';
import type { Dataset, DatasetEmbedding, DatasetSchema } from '@/api/types';
import { notFound } from 'next/navigation';

async function getDataset(id: string): Promise<Dataset | null> {
  try {
    return await openApiClient.datasets.get(id);
  } catch (error) {
    console.error('Failed to load dataset', error);
    return null;
  }
}

async function getSchema(id: string): Promise<DatasetSchema | null> {
  try {
    return await openApiClient.datasets.schema(id);
  } catch (error) {
    console.error('Failed to load schema', error);
    return null;
  }
}

async function getEmbeddings(id: string): Promise<DatasetEmbedding[]> {
  try {
    return await openApiClient.datasets.embeddings(id);
  } catch (error) {
    console.error('Failed to load embeddings', error);
    return [];
  }
}

type DatasetDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function DatasetDetailPage({ params }: DatasetDetailPageProps) {
  const { id } = await params;

  const [dataset, schema, embeddings] = await Promise.all([
    getDataset(id),
    getSchema(id),
    getEmbeddings(id),
  ]);

  if (!dataset) {
    notFound();
  }

  return (
    <Tabs
      tabs={[
        {
          key: 'schema',
          label: 'Schema',
          content: <JsonViewer value={schema ?? {}} />,
        },
        {
          key: 'embeddings',
          label: 'Embeddings',
          content: (
            <Card>
              {embeddings.length ? (
                <JsonViewer value={embeddings} />
              ) : (
                <p className="text-sm text-slate-500">No embeddings for this dataset.</p>
              )}
            </Card>
          ),
        },
        {
          key: 'metadata',
          label: 'Metadata',
          content: <JsonViewer value={dataset} />,
        },
      ]}
    />
  );
}
