// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/components/misc/EmptyState.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/components/misc/EmptyState.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import Button from '@/components/primitives/Button';

export type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export default function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <Card className="flex flex-col items-center justify-center text-center">
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-600">{description}</p>
      {actionLabel ? (
        <Button className="mt-4" onClick={onAction}
        >
          {actionLabel}
        </Button>
      ) : null}
    </Card>
  );
}
