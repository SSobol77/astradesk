// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/tests/unit/auth.config.test.ts
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

const REQUIRED_ENV = {
  NEXT_PUBLIC_API_BASE_URL: 'http://localhost:4000',
  NEXT_PUBLIC_SIMULATION_MODE: '',
};

function clearOidcEnv(): void {
  delete process.env.NEXT_PUBLIC_OIDC_ISSUER;
  delete process.env.NEXT_PUBLIC_OIDC_CLIENT_ID;
  delete process.env.NEXT_PUBLIC_OIDC_AUDIENCE;
  delete process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI;
  delete process.env.NEXT_PUBLIC_OIDC_SCOPE;
  delete process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI;
}

describe('OIDC config (ISSUE 021)', () => {
  beforeEach(() => {
    vi.resetModules();
    Object.assign(process.env, REQUIRED_ENV);
    clearOidcEnv();
  });

  it('reports unconfigured when no NEXT_PUBLIC_OIDC_* variables are set', async () => {
    const { isOidcConfigured } = await import('@/lib/auth/config');
    expect(isOidcConfigured()).toBe(false);
  });

  it('reports unconfigured when only some required variables are set', async () => {
    process.env.NEXT_PUBLIC_OIDC_ISSUER = 'https://issuer.example.com/';
    const { isOidcConfigured } = await import('@/lib/auth/config');
    expect(isOidcConfigured()).toBe(false);
  });

  it('reports configured once issuer, client id, and redirect uri are all set', async () => {
    process.env.NEXT_PUBLIC_OIDC_ISSUER = 'https://issuer.example.com/';
    process.env.NEXT_PUBLIC_OIDC_CLIENT_ID = 'test-client';
    process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI = 'http://localhost:3000/callback';

    const { isOidcConfigured } = await import('@/lib/auth/config');

    expect(isOidcConfigured()).toBe(true);
  });

  it('requireOidcConfig throws with a descriptive, non-secret-leaking message when unconfigured', async () => {
    const { requireOidcConfig } = await import('@/lib/auth/config');
    expect(() => requireOidcConfig()).toThrow(/NEXT_PUBLIC_OIDC_ISSUER/);
  });

  it('requireOidcConfig reflects exactly the configured environment values, never a hardcoded default', async () => {
    process.env.NEXT_PUBLIC_OIDC_ISSUER = 'https://tenant.example-idp.com/';
    process.env.NEXT_PUBLIC_OIDC_CLIENT_ID = 'abc123';
    process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI = 'https://admin.example.com/callback';
    process.env.NEXT_PUBLIC_OIDC_AUDIENCE = 'https://api.example.com';

    const { requireOidcConfig } = await import('@/lib/auth/config');
    const config = requireOidcConfig();

    expect(config).toEqual({
      issuer: 'https://tenant.example-idp.com/',
      clientId: 'abc123',
      redirectUri: 'https://admin.example.com/callback',
      audience: 'https://api.example.com',
      scope: 'openid profile email',
      postLogoutRedirectUri: undefined,
    });
  });
});
