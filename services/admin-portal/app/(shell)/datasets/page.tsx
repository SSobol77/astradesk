// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/datasets/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/datasets/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import DatasetsClient from './DatasetsClient';
import { openApiClient } from '@/api/client';
import type { Dataset } from '@/api/types';

async function getDatasets(): Promise<Dataset[]> {
  try {
    return await openApiClient.datasets.list();
  } catch (error) {
    console.error('Failed to load datasets', error);
    return [];
  }
}

export default async function DatasetsPage() {
  const datasets = await getDatasets();

  return <DatasetsClient datasets={datasets} />;
}
