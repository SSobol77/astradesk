// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/tests/unit/filters.serializer.test.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Verifies AstraDesk behavior for the associated component.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import { describe, expect, it } from 'vitest';
import { getQueryParamsFor } from '@/lib/guards';

describe('Filter metadata', () => {
  it('only exposes allowed /runs filters', () => {
    const filters = getQueryParamsFor('runs', 'list');
    const keys = filters.map((filter) => filter.key);
    expect(keys).toEqual(['agentId', 'status', 'from', 'to']);
  });

  it('only exposes allowed /audit filters', () => {
    const filters = getQueryParamsFor('audit', 'list');
    const keys = filters.map((filter) => filter.key);
    expect(keys).toEqual(['userId', 'action', 'resource', 'from', 'to']);
  });
});
