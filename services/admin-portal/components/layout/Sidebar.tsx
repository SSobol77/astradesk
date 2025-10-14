'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard' },
  { href: '/agents', label: 'Agents' },
  { href: '/intent-graph', label: 'Intent Graph' },
  { href: '/flows', label: 'Flows' },
  { href: '/datasets', label: 'Datasets' },
  { href: '/tools', label: 'Tools & Connectors' },
  { href: '/secrets', label: 'Keys & Secrets' },
  { href: '/runs', label: 'Runs & Logs' },
  { href: '/jobs', label: 'Jobs & Schedules' },
  { href: '/rbac', label: 'Users & Roles' },
  { href: '/policies', label: 'Policies' },
  { href: '/audit', label: 'Audit Trail' },
  { href: '/settings', label: 'Settings' },
] as const;

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col"
      aria-label="Primary"
    >
      <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white">
          AD
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">AstraDesk</p>
          <p className="text-xs text-slate-500">Admin Panel</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-6">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    'flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2',
                    isActive
                      ? 'bg-indigo-50 text-indigo-600'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                  )}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
