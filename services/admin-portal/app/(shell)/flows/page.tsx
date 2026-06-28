// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/flows/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/flows/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import FlowsClient from './FlowsClient';
import { openApiClient } from '@/api/client';
import type { Flow } from '@/api/types';

async function getFlows(): Promise<Flow[]> {
  try {
    return await openApiClient.flows.list();
  } catch (error) {
    console.error('Failed to load flows', error);
    return [];
  }
}

export default async function FlowsPage() {
  const flows = await getFlows();

  return <FlowsClient flows={flows} />;
}
