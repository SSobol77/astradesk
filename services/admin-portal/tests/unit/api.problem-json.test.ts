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
