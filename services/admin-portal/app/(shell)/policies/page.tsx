// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/policies/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/policies/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import PoliciesClient from './PoliciesClient';
import { openApiClient } from '@/api/client';
import type { Policy } from '@/api/types';

async function getPolicies(): Promise<Policy[]> {
  try {
    return await openApiClient.policies.list();
  } catch (error) {
    console.error('Failed to load policies', error);
    return [];
  }
}

export default async function PoliciesPage() {
  const policies = await getPolicies();

  return <PoliciesClient policies={policies} />;
}
