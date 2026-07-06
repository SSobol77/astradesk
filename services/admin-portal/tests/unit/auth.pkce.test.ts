// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/tests/unit/auth.pkce.test.ts
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
import { generateCodeChallenge, generateCodeVerifier, generateRandomToken } from '@/lib/auth/pkce';

describe('PKCE helpers (ISSUE 021)', () => {
  it('generates a URL-safe code verifier with no padding characters', () => {
    const verifier = generateCodeVerifier();
    expect(verifier.length).toBeGreaterThanOrEqual(43);
    expect(verifier).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it('generates distinct code verifiers on each call', () => {
    const first = generateCodeVerifier();
    const second = generateCodeVerifier();
    expect(first).not.toEqual(second);
  });

  it('derives the S256 code challenge matching the RFC 7636 Appendix B test vector', async () => {
    // https://www.rfc-editor.org/rfc/rfc7636#appendix-B
    const verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk';
    const expectedChallenge = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM';

    const challenge = await generateCodeChallenge(verifier);

    expect(challenge).toBe(expectedChallenge);
  });

  it('produces a URL-safe code challenge with no padding characters', async () => {
    const challenge = await generateCodeChallenge(generateCodeVerifier());
    expect(challenge).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it('generates unguessable, distinct state/nonce tokens', () => {
    const a = generateRandomToken();
    const b = generateRandomToken();
    expect(a).not.toEqual(b);
    expect(a.length).toBeGreaterThan(0);
    expect(a).toMatch(/^[A-Za-z0-9_-]+$/);
  });
});
