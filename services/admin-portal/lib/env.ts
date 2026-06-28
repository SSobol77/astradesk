// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/env.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/env.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import { object, optional, safeParse, string } from 'valibot';

const clientEnvSchema = object({
  NEXT_PUBLIC_API_BASE_URL: string('NEXT_PUBLIC_API_BASE_URL is required'),
  NEXT_PUBLIC_SIMULATION_MODE: optional(string()),
});

const serverEnvSchema = object({
  ASTRADESK_API_TOKEN: optional(string()),
});

const clientEnvResult = safeParse(clientEnvSchema, {
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_SIMULATION_MODE: process.env.NEXT_PUBLIC_SIMULATION_MODE,
});

if (!clientEnvResult.success) {
  const message = clientEnvResult.issues.map((issue) => issue.message).join(', ');
  throw new Error(`Environment validation failed: ${message}`);
}

const serverEnvResult = safeParse(serverEnvSchema, {
  ASTRADESK_API_TOKEN: process.env.ASTRADESK_API_TOKEN,
});

export const clientEnv = clientEnvResult.output;

export const apiBaseUrl = clientEnv.NEXT_PUBLIC_API_BASE_URL;
export const apiToken = serverEnvResult.success ? serverEnvResult.output.ASTRADESK_API_TOKEN ?? '' : '';
export const simulationModeEnabled = clientEnv.NEXT_PUBLIC_SIMULATION_MODE === 'true';
