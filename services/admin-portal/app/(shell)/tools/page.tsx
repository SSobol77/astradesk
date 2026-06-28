// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/tools/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/tools/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import ToolsClient from './ToolsClient';
import { openApiClient } from '@/api/client';

async function getConnectors() {
  try {
    return await openApiClient.tools.list();
  } catch (error) {
    console.error('Failed to load connectors', error);
    return [];
  }
}

export default async function ToolsPage() {
  const connectors = await getConnectors();

  return <ToolsClient tools={connectors} />;
}
