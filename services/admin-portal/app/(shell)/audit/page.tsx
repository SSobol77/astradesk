// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/audit/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/audit/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import AuditClient from './AuditClient';
import { getQueryParamsFor } from '@/lib/guards';
import { openApiClient } from '@/api/client';
import type { AuditEntry } from '@/api/types';

async function getAuditEntries(): Promise<AuditEntry[]> {
  try {
    return await openApiClient.audit.list();
  } catch (error) {
    console.error('Failed to load audit entries', error);
    return [];
  }
}

export default async function AuditPage() {
  const [entries, filtersMeta] = await Promise.all([
    getAuditEntries(),
    Promise.resolve(getQueryParamsFor('audit', 'list')),
  ]);

  return <AuditClient initialEntries={entries} filtersMeta={filtersMeta} />;
}
