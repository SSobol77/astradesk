'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo } from 'react';
import Button from '@/components/primitives/Button';
import { getBreadcrumbs, getQuickCreateLinks } from '@/lib/guards';
import { useCommandPalette } from '@/components/search/CommandPalette';

export default function Topbar() {
  const pathname = usePathname();
  const breadcrumbs = useMemo(() => getBreadcrumbs(pathname), [pathname]);
  const quickCreates = useMemo(() => getQuickCreateLinks(), []);
  const { open: openCommandPalette, openQuickActions } = useCommandPalette();

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
                JD
              </span>
              <span>Admin</span>
            </summary>
            <ul className="absolute right-0 mt-2 min-w-[10rem] rounded-xl border border-slate-200 bg-white p-2 text-sm shadow-xl">
              <li>
                <Link href="/profile" className="block rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100">
                  Profile
                </Link>
              </li>
              <li>
                <Link href="#sign-out" className="block rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100">
                  Sign out
                </Link>
              </li>
            </ul>
          </details>
        </div>
      </div>
    </header>
  );
}
