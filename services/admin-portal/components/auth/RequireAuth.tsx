// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/components/auth/RequireAuth.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/components/auth/RequireAuth.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import type { Route } from 'next';
import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

/**
 * Wraps the protected `(shell)` route group (ISSUE 021). Renders nothing of
 * the actual admin UI unless the caller is `authenticated` or the portal is
 * running in `NEXT_PUBLIC_SIMULATION_MODE`. `unconfigured` (OIDC env vars
 * unset) is treated exactly like `unauthenticated` — a misconfigured
 * deployment must fail closed, not silently expose the console.
 */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const blocked = status === 'unauthenticated' || status === 'unconfigured';

  useEffect(() => {
    if (blocked) {
      const encodedReturnTo = encodeURIComponent(pathname || '/');
      router.replace(`/login?returnTo=${encodedReturnTo}` as Route);
    }
  }, [blocked, pathname, router]);

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Checking your session…
      </div>
    );
  }

  if (blocked) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Redirecting to sign in…
      </div>
    );
  }

  return <>{children}</>;
}
