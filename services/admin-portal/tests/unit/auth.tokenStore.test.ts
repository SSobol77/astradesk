// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/tests/unit/auth.tokenStore.test.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Verifies AstraDesk behavior for the associated component.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
}

describe('tokenStore (ISSUE 021)', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('isSessionValid', () => {
    it('rejects a null session', async () => {
      const { isSessionValid } = await import('@/lib/auth/tokenStore');
      expect(isSessionValid(null)).toBe(false);
    });

    it('accepts a session with a future expiry', async () => {
      const { isSessionValid } = await import('@/lib/auth/tokenStore');
      const now = 1_000_000;
      expect(
        isSessionValid({ accessToken: 'a', expiresAt: now + 60_000 }, now),
      ).toBe(true);
    });

    it('rejects a session inside the expiry leeway window', async () => {
      const { isSessionValid } = await import('@/lib/auth/tokenStore');
      const now = 1_000_000;
      // Expires in 10s, well within the 30s leeway -> treated as expired.
      expect(
        isSessionValid({ accessToken: 'a', expiresAt: now + 10_000 }, now),
      ).toBe(false);
    });

    it('rejects an already-expired session', async () => {
      const { isSessionValid } = await import('@/lib/auth/tokenStore');
      const now = 1_000_000;
      expect(
        isSessionValid({ accessToken: 'a', expiresAt: now - 1 }, now),
      ).toBe(false);
    });
  });

  describe('outside the browser (no window)', () => {
    it('getAccessToken returns null server-side without throwing', async () => {
      const { getAccessToken } = await import('@/lib/auth/tokenStore');
      expect(getAccessToken()).toBeNull();
    });

    it('saveSession/clearSession are no-ops server-side', async () => {
      const { saveSession, clearSession, loadSession } = await import('@/lib/auth/tokenStore');
      expect(() => saveSession({ accessToken: 'x', expiresAt: Date.now() + 60_000 })).not.toThrow();
      expect(() => clearSession()).not.toThrow();
      expect(loadSession()).toBeNull();
    });
  });

  describe('in the browser (stubbed sessionStorage)', () => {
    beforeEach(() => {
      vi.stubGlobal('window', { sessionStorage: new MemoryStorage() });
    });

    it('round-trips a saved session through loadSession', async () => {
      const { saveSession, loadSession } = await import('@/lib/auth/tokenStore');
      const session = { accessToken: 'abc', expiresAt: Date.now() + 60_000, scope: 'openid' };

      saveSession(session);

      expect(loadSession()).toEqual(session);
    });

    it('getAccessToken returns the token only while the session is valid', async () => {
      const { saveSession, getAccessToken } = await import('@/lib/auth/tokenStore');

      saveSession({ accessToken: 'valid-token', expiresAt: Date.now() + 60_000 });
      expect(getAccessToken()).toBe('valid-token');

      saveSession({ accessToken: 'expired-token', expiresAt: Date.now() - 1 });
      expect(getAccessToken()).toBeNull();
    });

    it('clearSession removes the stored session', async () => {
      const { saveSession, clearSession, loadSession } = await import('@/lib/auth/tokenStore');

      saveSession({ accessToken: 'abc', expiresAt: Date.now() + 60_000 });
      clearSession();

      expect(loadSession()).toBeNull();
    });

    it('loadSession returns null for malformed stored JSON', async () => {
      const storage = new MemoryStorage();
      vi.stubGlobal('window', { sessionStorage: storage });
      storage.setItem('astradesk_admin_oidc_session', '{not-json');

      const { loadSession } = await import('@/lib/auth/tokenStore');

      expect(loadSession()).toBeNull();
    });

    it('loadSession returns null when required fields are missing', async () => {
      const storage = new MemoryStorage();
      vi.stubGlobal('window', { sessionStorage: storage });
      storage.setItem('astradesk_admin_oidc_session', JSON.stringify({ scope: 'openid' }));

      const { loadSession } = await import('@/lib/auth/tokenStore');

      expect(loadSession()).toBeNull();
    });
  });

  describe('decodeIdTokenClaims', () => {
    it('decodes a well-formed JWT payload without verifying its signature', async () => {
      const { decodeIdTokenClaims } = await import('@/lib/auth/tokenStore');
      const payload = { sub: 'user-1', name: 'Ada Lovelace', email: 'ada@example.com' };
      const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
      const fakeJwt = `header.${encodedPayload}.signature`;

      expect(decodeIdTokenClaims(fakeJwt)).toEqual(payload);
    });

    it('returns null for a malformed token', async () => {
      const { decodeIdTokenClaims } = await import('@/lib/auth/tokenStore');
      expect(decodeIdTokenClaims('not-a-jwt')).toBeNull();
    });
  });
});
