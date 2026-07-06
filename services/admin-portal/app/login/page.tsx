// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/login/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/login/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Button from '@/components/primitives/Button';
import { useAuth } from '@/hooks/useAuth';

function LoginContent() {
  const { status, login } = useAuth();
  const searchParams = useSearchParams();
  const [isRedirecting, setRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const returnTo = searchParams.get('returnTo') || '/';

  useEffect(() => {
    if (status === 'authenticated' || status === 'simulated') {
      window.location.assign(returnTo);
    }
  }, [status, returnTo]);

  const handleLogin = async () => {
    setError(null);
    setRedirecting(true);
    try {
      await login(returnTo);
    } catch (loginError) {
      console.error('Failed to start OIDC login', loginError);
      setError(loginError instanceof Error ? loginError.message : 'Failed to start sign-in.');
      setRedirecting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-6 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">AstraDesk Admin</h1>
      {status === 'unconfigured' ? (
        <p className="max-w-md text-sm text-rose-600">
          Single sign-on is not configured for this deployment. Set{' '}
          <code>NEXT_PUBLIC_OIDC_ISSUER</code>, <code>NEXT_PUBLIC_OIDC_CLIENT_ID</code>, and{' '}
          <code>NEXT_PUBLIC_OIDC_REDIRECT_URI</code> to enable admin login.
        </p>
      ) : (
        <p className="max-w-md text-sm text-slate-500">
          Sign in with your organization&apos;s identity provider to access the admin console.
        </p>
      )}
      {error ? <p className="max-w-md text-sm text-rose-600">{error}</p> : null}
      <Button type="button" onClick={handleLogin} disabled={isRedirecting || status === 'unconfigured'}>
        {isRedirecting ? 'Redirecting…' : 'Sign in'}
      </Button>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}
