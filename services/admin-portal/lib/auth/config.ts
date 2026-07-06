// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/auth/config.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/auth/config.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

/**
 * Front-channel OIDC configuration surface (ISSUE 021).
 *
 * All values come from `lib/env.ts`'s validated `NEXT_PUBLIC_OIDC_*`
 * variables — never hardcoded here. A deployment that has not set these
 * variables is "unconfigured", not silently allowed through: see
 * `hooks/useAuth.tsx`'s `unconfigured` status, which blocks the protected
 * shell exactly like `unauthenticated` does.
 */

import { oidcEnv } from '@/lib/env';

export type OidcConfig = {
  issuer: string;
  clientId: string;
  redirectUri: string;
  audience?: string;
  scope: string;
  postLogoutRedirectUri?: string;
};

export function isOidcConfigured(): boolean {
  return Boolean(oidcEnv.issuer && oidcEnv.clientId && oidcEnv.redirectUri);
}

export function requireOidcConfig(): OidcConfig {
  if (!oidcEnv.issuer || !oidcEnv.clientId || !oidcEnv.redirectUri) {
    throw new Error(
      'OIDC is not configured: set NEXT_PUBLIC_OIDC_ISSUER, NEXT_PUBLIC_OIDC_CLIENT_ID, ' +
        'and NEXT_PUBLIC_OIDC_REDIRECT_URI to enable admin login.',
    );
  }
  return {
    issuer: oidcEnv.issuer,
    clientId: oidcEnv.clientId,
    redirectUri: oidcEnv.redirectUri,
    audience: oidcEnv.audience,
    scope: oidcEnv.scope,
    postLogoutRedirectUri: oidcEnv.postLogoutRedirectUri,
  };
}
