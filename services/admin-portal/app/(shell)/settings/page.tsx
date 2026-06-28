// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/settings/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/settings/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import SettingsClient from './SettingsClient';
import { openApiClient } from '@/api/client';
import type { Setting } from '@/api/types';

async function fetchSettings() {
  const [integrations, localization, platform] = await Promise.all([
    openApiClient.settings.list('integrations'),
    openApiClient.settings.list('localization'),
    openApiClient.settings.list('platform'),
  ]);

  return { integrations, localization, platform } satisfies {
    integrations: Setting[];
    localization: Setting[];
    platform: Setting[];
  };
}

export default async function SettingsPage() {
  const settings = await fetchSettings();

  return <SettingsClient {...settings} />;
}
