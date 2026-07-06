// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/hooks/useAuth.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/hooks/useAuth.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import type { ReactNode } from 'react';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { isOidcConfigured } from '@/lib/auth/config';
import { startLogin, logout as oidcLogout, refreshSession } from '@/lib/auth/oidcClient';
import { decodeIdTokenClaims, isSessionValid, loadSession } from '@/lib/auth/tokenStore';
import { isSimulationModeEnabled } from '@/lib/simulation';

/**
 * `unconfigured` and `unauthenticated` are both non-privileged states that
 * `components/auth/RequireAuth.tsx` treats identically (redirect to
 * `/login`) — a deployment that forgot to set `NEXT_PUBLIC_OIDC_*` must fail
 * closed, not fall through to an implicitly-trusted state.
 */
export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'unconfigured' | 'simulated';

type AuthContextValue = {
  status: AuthStatus;
  accessToken: string | null;
  displayName: string | null;
  login: (returnTo?: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function resolveDisplayName(idToken: string | undefined): string | null {
  if (!idToken) {
    return null;
  }
  const claims = decodeIdTokenClaims(idToken);
  const name = claims?.name ?? claims?.email;
  return typeof name === 'string' ? name : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);

  const evaluate = useCallback(() => {
    if (isSimulationModeEnabled()) {
      setStatus('simulated');
      setAccessToken(null);
      setDisplayName(null);
      return;
    }
    if (!isOidcConfigured()) {
      setStatus('unconfigured');
      setAccessToken(null);
      setDisplayName(null);
      return;
    }
    const session = loadSession();
    if (isSessionValid(session)) {
      setStatus('authenticated');
      setAccessToken(session.accessToken);
      setDisplayName(resolveDisplayName(session.idToken));
      return;
    }
    setStatus('unauthenticated');
    setAccessToken(null);
    setDisplayName(null);
  }, []);

  useEffect(() => {
    evaluate();
  }, [evaluate]);

  // Proactively refresh the access token shortly before it expires so an
  // in-progress admin session does not suddenly start failing API calls.
  useEffect(() => {
    if (status !== 'authenticated') {
      return undefined;
    }
    const session = loadSession();
    if (!session) {
      return undefined;
    }
    const refreshInMs = Math.max(session.expiresAt - Date.now() - 60_000, 5_000);
    const timer = window.setTimeout(() => {
      void refreshSession().then((refreshed) => {
        if (refreshed) {
          setAccessToken(refreshed.accessToken);
          setDisplayName(resolveDisplayName(refreshed.idToken));
        } else {
          evaluate();
        }
      });
    }, refreshInMs);
    return () => window.clearTimeout(timer);
  }, [status, evaluate]);

  const login = useCallback(async (returnTo?: string) => {
    await startLogin(returnTo ?? window.location.pathname);
  }, []);

  const logout = useCallback(async () => {
    await oidcLogout();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, accessToken, displayName, login, logout }),
    [status, accessToken, displayName, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
