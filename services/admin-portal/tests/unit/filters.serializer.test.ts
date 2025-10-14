import { describe, expect, it } from 'vitest';
import { getQueryParamsFor } from '@/lib/guards';

describe('Filter metadata', () => {
  it('only exposes allowed /runs filters', () => {
    const filters = getQueryParamsFor('runs', 'list');
    const keys = filters.map((filter) => filter.key);
    expect(keys).toEqual(['agent', 'intent', 'status', 'from', 'to']);
  });

  it('only exposes allowed /audit filters', () => {
    const filters = getQueryParamsFor('audit', 'list');
    const keys = filters.map((filter) => filter.key);
    expect(keys).toEqual(['user', 'action', 'resource', 'from', 'to']);
  });
});
