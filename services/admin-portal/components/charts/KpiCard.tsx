// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/components/charts/KpiCard.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/components/charts/KpiCard.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import Badge from '@/components/primitives/Badge';

export type KpiCardProps = {
  title: string;
  value: string;
  deltaLabel?: string;
  status?: 'healthy' | 'degraded' | 'down';
};

const STATUS_BADGE: Record<NonNullable<KpiCardProps['status']>, { label: string; variant: Parameters<typeof Badge>[0]['variant'] }> = {
  healthy: { label: 'Healthy', variant: 'success' },
  degraded: { label: 'Degraded', variant: 'warn' },
  down: { label: 'Down', variant: 'danger' },
};

export default function KpiCard({ title, value, deltaLabel, status }: KpiCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
          {deltaLabel ? <p className="mt-1 text-xs text-slate-500">{deltaLabel}</p> : null}
        </div>
        {status ? <Badge variant={STATUS_BADGE[status].variant}>{STATUS_BADGE[status].label}</Badge> : null}
      </div>
    </Card>
  );
}
