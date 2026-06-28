// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/components/misc/JsonViewer.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/components/misc/JsonViewer.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';

export default function JsonViewer({ value }: { value: unknown }) {
  return (
    <Card className="overflow-x-auto bg-slate-900 text-slate-100">
      <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-[#2978B3]">
        {JSON.stringify(value, null, 2)}
      </pre>
    </Card>
  );
}
