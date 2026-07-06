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
  // Front-channel OIDC (ISSUE 021). All optional: unset means OIDC login is
  // not configured for this deployment (see lib/auth/config.ts). Generic
  // OIDC naming (not Auth0-specific) matches OIDC_ISSUER/OIDC_AUDIENCE
  // already used server-side by the API Gateway and Admin API, and keeps the
  // portal provider-agnostic (Auth0, Keycloak, Okta, ...).
  NEXT_PUBLIC_OIDC_ISSUER: optional(string()),
  NEXT_PUBLIC_OIDC_CLIENT_ID: optional(string()),
  NEXT_PUBLIC_OIDC_AUDIENCE: optional(string()),
  NEXT_PUBLIC_OIDC_REDIRECT_URI: optional(string()),
  NEXT_PUBLIC_OIDC_SCOPE: optional(string()),
  NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI: optional(string()),
});

const serverEnvSchema = object({
  ASTRADESK_API_TOKEN: optional(string()),
});

const clientEnvResult = safeParse(clientEnvSchema, {
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_SIMULATION_MODE: process.env.NEXT_PUBLIC_SIMULATION_MODE,
  NEXT_PUBLIC_OIDC_ISSUER: process.env.NEXT_PUBLIC_OIDC_ISSUER,
  NEXT_PUBLIC_OIDC_CLIENT_ID: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID,
  NEXT_PUBLIC_OIDC_AUDIENCE: process.env.NEXT_PUBLIC_OIDC_AUDIENCE,
  NEXT_PUBLIC_OIDC_REDIRECT_URI: process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI,
  NEXT_PUBLIC_OIDC_SCOPE: process.env.NEXT_PUBLIC_OIDC_SCOPE,
  NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI: process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI,
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

export const oidcEnv = {
  issuer: clientEnv.NEXT_PUBLIC_OIDC_ISSUER,
  clientId: clientEnv.NEXT_PUBLIC_OIDC_CLIENT_ID,
  audience: clientEnv.NEXT_PUBLIC_OIDC_AUDIENCE,
  redirectUri: clientEnv.NEXT_PUBLIC_OIDC_REDIRECT_URI,
  scope: clientEnv.NEXT_PUBLIC_OIDC_SCOPE || 'openid profile email',
  postLogoutRedirectUri: clientEnv.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI,
};
