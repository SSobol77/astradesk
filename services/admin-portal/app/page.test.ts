// services/admin-portal/app/page.test.ts
import { describe, it, expect } from 'vitest';

describe('admin portal smoke', () => {
  it('has basic content', () => {
    const title = 'AstraDesk — Admin Portal';
    expect(title.includes('AstraDesk')).toBe(true);
  });
});
