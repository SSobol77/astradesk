// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/callback/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/callback/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import type { Route } from 'next';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { handleCallback } from '@/lib/auth/oidcClient';

const loginRoute = '/login' as Route;

/**
 * Target of `NEXT_PUBLIC_OIDC_REDIRECT_URI`. Outside the `(shell)` route
 * group deliberately, so it is not wrapped by `RequireAuth` — that would
 * redirect back to `/login` before the code exchange ever runs.
 */
export default function CallbackPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    handleCallback(window.location.href)
      .then(({ returnTo }) => {
        if (!cancelled) {
          window.location.assign(returnTo);
        }
      })
      .catch((callbackError: unknown) => {
        if (!cancelled) {
          console.error('OIDC callback failed', callbackError);
          setError(callbackError instanceof Error ? callbackError.message : 'Sign-in failed.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 px-6 text-center">
      <h1 className="text-xl font-semibold text-slate-900">AstraDesk Admin</h1>
      {error ? (
        <>
          <p className="max-w-md text-sm text-rose-600">{error}</p>
          <Link href={loginRoute} className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
            Return to sign in
          </Link>
        </>
      ) : (
        <p className="text-sm text-slate-500">Completing sign-in…</p>
      )}
    </div>
  );
}
