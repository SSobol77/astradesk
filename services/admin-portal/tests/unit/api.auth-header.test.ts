// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/tests/unit/api.auth-header.test.ts
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

import { beforeEach, describe, expect, it, vi } from 'vitest';

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

const mockFetch = vi.fn();

vi.stubGlobal('fetch', mockFetch);

function mockOkResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    headers: { get: () => 'application/json' },
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

describe('apiFetch Authorization header resolution (ISSUE 021)', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:4000';
    process.env.ASTRADESK_API_TOKEN = '';
    vi.resetModules();
    vi.unstubAllGlobals();
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockReset();
    mockFetch.mockResolvedValue(mockOkResponse({ ok: true }));
  });

  it('omits Authorization when there is no server token and no browser session', async () => {
    const { apiFetch } = await import('@/lib/api');

    await apiFetch({ path: '/agents', method: 'GET' });

    const [, init] = mockFetch.mock.calls[0] as [unknown, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('uses the server-side ASTRADESK_API_TOKEN when no browser session exists (SSR path)', async () => {
    process.env.ASTRADESK_API_TOKEN = 'server-machine-token';

    const { apiFetch } = await import('@/lib/api');
    await apiFetch({ path: '/agents', method: 'GET' });

    const [, init] = mockFetch.mock.calls[0] as [unknown, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer server-machine-token');
  });

  it("prefers the signed-in user's OIDC access token over the server token", async () => {
    process.env.ASTRADESK_API_TOKEN = 'server-machine-token';
    vi.stubGlobal('window', { sessionStorage: new MemoryStorage() });

    const { saveSession } = await import('@/lib/auth/tokenStore');
    saveSession({ accessToken: 'user-oidc-token', expiresAt: Date.now() + 60_000 });

    const { apiFetch } = await import('@/lib/api');
    await apiFetch({ path: '/agents', method: 'GET' });

    const [, init] = mockFetch.mock.calls[0] as [unknown, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer user-oidc-token');
  });

  it('does not send a stale/expired OIDC token — falls through instead of proceeding privileged', async () => {
    vi.stubGlobal('window', { sessionStorage: new MemoryStorage() });

    const { saveSession } = await import('@/lib/auth/tokenStore');
    saveSession({ accessToken: 'expired-token', expiresAt: Date.now() - 1 });

    const { apiFetch } = await import('@/lib/api');
    await apiFetch({ path: '/agents', method: 'GET' });

    const [, init] = mockFetch.mock.calls[0] as [unknown, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });
});
