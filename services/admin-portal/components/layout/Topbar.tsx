// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/components/layout/Topbar.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/components/layout/Topbar.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo } from 'react';
import Button from '@/components/primitives/Button';
import { getBreadcrumbs, getQuickCreateLinks } from '@/lib/guards';
import { useAuth } from '@/hooks/useAuth';
import { useCommandPalette } from '@/components/search/CommandPalette';

function initialsFor(name: string | null): string {
  if (!name) {
    return 'A';
  }
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part.charAt(0).toUpperCase()).join('') || 'A';
}

export default function Topbar() {
  const pathname = usePathname();
  const breadcrumbs = useMemo(() => getBreadcrumbs(pathname), [pathname]);
  const quickCreates = useMemo(() => getQuickCreateLinks(), []);
  const { open: openCommandPalette, openQuickActions } = useCommandPalette();
  const { status, displayName, logout } = useAuth();

  const handleSignOut = () => {
    void logout();
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <nav aria-label="Breadcrumb" className="text-xs uppercase tracking-wide text-slate-400">
            {breadcrumbs.map((crumb, index) => {
              const isLink = crumb.href !== '#';
              return (
                <span key={`${crumb.label}-${index}`}>
                  {isLink ? (
                    <Link href={crumb.href} className="hover:text-indigo-600">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-slate-500">{crumb.label}</span>
                  )}
                  {index < breadcrumbs.length - 1 ? <span className="mx-2">/</span> : null}
                </span>
              );
            })}
          </nav>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">
            {breadcrumbs[breadcrumbs.length - 1]?.label ?? 'AstraDesk'}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={openCommandPalette}
            className="hidden items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-500 transition-colors hover:border-indigo-300 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 lg:flex"
            aria-label="Open search"
          >
            <span className="font-medium">Search</span>
            <span className="text-slate-300">⌘K</span>
          </button>
          {quickCreates.length > 0 ? (
            <Button type="button" onClick={openQuickActions}>
              New
            </Button>
          ) : null}
          <details className="relative">
            <summary className="flex cursor-pointer items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-white">
                {initialsFor(displayName)}
              </span>
              <span>{displayName ?? (status === 'simulated' ? 'Simulation' : 'Admin')}</span>
            </summary>
            <ul className="absolute right-0 mt-2 min-w-[10rem] rounded-xl border border-slate-200 bg-white p-2 text-sm shadow-xl">
              <li>
                <Link href="/profile" className="block rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100">
                  Profile
                </Link>
              </li>
              <li>
                <button
                  type="button"
                  onClick={handleSignOut}
                  disabled={status === 'simulated'}
                  className="block w-full rounded-lg px-3 py-2 text-left text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Sign out
                </button>
              </li>
            </ul>
          </details>
        </div>
      </div>
    </header>
  );
}
