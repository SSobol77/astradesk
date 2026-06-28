// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/secrets/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/secrets/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import SecretsClient from './SecretsClient';
import { openApiClient } from '@/api/client';
import type { Secret } from '@/api/types';

export const dynamic = 'force-dynamic';

async function getSecrets(): Promise<Secret[]> {
  try {
    return await openApiClient.secrets.list();
  } catch (error) {
    console.error('Failed to load secrets', error);
    return [];
  }
}

export default async function SecretsPage() {
  const secrets = await getSecrets();

  return <SecretsClient secrets={secrets} />;
}
