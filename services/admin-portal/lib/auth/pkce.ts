// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/auth/pkce.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/auth/pkce.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

/**
 * PKCE (RFC 7636) helpers for the Authorization Code + PKCE flow used by
 * `lib/auth/oidcClient.ts` (ISSUE 021).
 *
 * Uses only the Web Crypto API (`crypto.getRandomValues`/`crypto.subtle`,
 * available in both browsers and Node 22) and `btoa` — no npm dependency,
 * so no `@auth0/auth0-react`-style SDK is required for a public-client SPA
 * flow.
 */

const CODE_VERIFIER_BYTE_LENGTH = 64;
const DEFAULT_TOKEN_BYTE_LENGTH = 16;

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomBytes(length: number): Uint8Array {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return bytes;
}

/** A high-entropy, URL-safe secret kept client-side for the lifetime of one login attempt. */
export function generateCodeVerifier(): string {
  return base64UrlEncode(randomBytes(CODE_VERIFIER_BYTE_LENGTH));
}

/** The S256 PKCE code challenge sent in the authorization request. */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return base64UrlEncode(new Uint8Array(digest));
}

/** A random `state`/`nonce` value; not a secret, only unguessable. */
export function generateRandomToken(byteLength: number = DEFAULT_TOKEN_BYTE_LENGTH): string {
  return base64UrlEncode(randomBytes(byteLength));
}
