// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/auth/tokenStore.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/auth/tokenStore.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

/**
 * Browser-side session storage for the OIDC access/refresh tokens (ISSUE 021).
 *
 * Deliberately `sessionStorage`, not `localStorage`: the session is cleared
 * when the tab closes rather than persisting indefinitely on disk, reducing
 * the exfiltration window if an XSS vulnerability is ever found elsewhere in
 * the portal. This is a stricter default than the ad-hoc
 * `localStorage.astradesk_token` mechanism this replaces (see root
 * `README.md`'s prior "Authentication" section).
 *
 * Every export is guarded for a non-browser (`typeof window === 'undefined'`)
 * environment so this module is safe to import from Next.js Server
 * Components / SSR code paths — it simply reports "no session" there,
 * exactly like `lib/api.ts`'s existing `apiToken` server/client split.
 */

const SESSION_STORAGE_KEY = 'astradesk_admin_oidc_session';

/** Milliseconds of slack subtracted from `expiresAt` so a token is treated as expired
 * slightly before the IdP would actually reject it (clock skew, request latency). */
const EXPIRY_LEEWAY_MS = 30_000;

export type AuthSession = {
  accessToken: string;
  idToken?: string;
  refreshToken?: string;
  /** Epoch milliseconds. */
  expiresAt: number;
  scope?: string;
};

function hasSessionStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

export function saveSession(session: AuthSession): void {
  if (!hasSessionStorage()) {
    return;
  }
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function loadSession(): AuthSession | null {
  if (!hasSessionStorage()) {
    return null;
  }
  const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (typeof parsed.accessToken !== 'string' || typeof parsed.expiresAt !== 'number') {
      return null;
    }
    return parsed as AuthSession;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  if (!hasSessionStorage()) {
    return;
  }
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
}

export function isSessionValid(
  session: AuthSession | null,
  now: number = Date.now(),
): session is AuthSession {
  if (!session) {
    return false;
  }
  return session.expiresAt - EXPIRY_LEEWAY_MS > now;
}

/**
 * The access token to attach to Admin API requests, or `null` if there is no
 * valid browser session — callers must never substitute a placeholder when
 * this returns `null` (`INV-DUAL-PATH`-style: unauthenticated must stay
 * unauthenticated, not silently privileged).
 */
export function getAccessToken(): string | null {
  const session = loadSession();
  return isSessionValid(session) ? session.accessToken : null;
}

/**
 * Best-effort, unverified decode of an ID token's claims for UI display
 * (name/email in the Topbar). The Admin API independently verifies the
 * access token's signature server-side (NEW-SEC); this decode is never used
 * for an authorization decision.
 */
export function decodeIdTokenClaims(idToken: string): Record<string, unknown> | null {
  const parts = idToken.split('.');
  if (parts.length !== 3) {
    return null;
  }
  try {
    const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), '=');
    const decoded = atob(padded);
    return JSON.parse(decoded) as Record<string, unknown>;
  } catch {
    return null;
  }
}
