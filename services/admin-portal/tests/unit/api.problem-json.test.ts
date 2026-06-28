// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/tests/unit/api.problem-json.test.ts
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

import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { ApiError } from '@/lib/api';

const mockFetch = vi.fn();

vi.stubGlobal('fetch', mockFetch);

describe('apiFetch problem+json handling', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:4000';
    process.env.ASTRADESK_API_TOKEN = '';
    vi.resetModules();
    mockFetch.mockReset();
  });

  it('throws ApiError with problem detail message', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 422,
      headers: {
        get: () => 'application/problem+json',
      },
      json: async () => ({ detail: 'Invalid payload' }),
      text: async () => '',
    });

    const { apiFetch } = await import('@/lib/api');

    await expect(
      apiFetch({
        path: '/agents',
        method: 'POST',
        body: {},
      }),
    ).rejects.toMatchObject({
      message: 'Invalid payload',
      status: 422,
    } as ApiError);
  });
});
