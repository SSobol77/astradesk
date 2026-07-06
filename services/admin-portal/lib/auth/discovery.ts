// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/auth/discovery.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/auth/discovery.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

/**
 * OIDC discovery (`.well-known/openid-configuration`), ISSUE 021.
 *
 * Resolving endpoints via discovery — rather than hardcoding Auth0's
 * `/authorize` + `/oauth/token` paths — keeps the portal provider-agnostic:
 * Keycloak, Okta, and Auth0 all publish this document at the same
 * well-known path but with different endpoint shapes underneath.
 */

export type OidcMetadata = {
  authorization_endpoint: string;
  token_endpoint: string;
  end_session_endpoint?: string;
  jwks_uri?: string;
};

const metadataCache = new Map<string, Promise<OidcMetadata>>();

export function discoverOidcMetadata(issuer: string): Promise<OidcMetadata> {
  const normalizedIssuer = issuer.replace(/\/+$/, '');
  const cached = metadataCache.get(normalizedIssuer);
  if (cached) {
    return cached;
  }

  const promise = fetch(`${normalizedIssuer}/.well-known/openid-configuration`, {
    method: 'GET',
    cache: 'no-store',
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`OIDC discovery failed for ${normalizedIssuer}: HTTP ${response.status}`);
    }
    const body = (await response.json()) as Partial<OidcMetadata>;
    if (!body.authorization_endpoint || !body.token_endpoint) {
      throw new Error(`OIDC discovery document for ${normalizedIssuer} is missing required endpoints.`);
    }
    return body as OidcMetadata;
  });

  metadataCache.set(normalizedIssuer, promise);
  promise.catch(() => metadataCache.delete(normalizedIssuer));
  return promise;
}

/** Test-only escape hatch; also useful if an operator rotates issuers without a full reload. */
export function clearOidcMetadataCache(): void {
  metadataCache.clear();
}
