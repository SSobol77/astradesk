// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/auth/oidcClient.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/auth/oidcClient.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

/**
 * Front-channel OIDC Authorization Code + PKCE flow orchestration (ISSUE 021).
 *
 * A generic, dependency-free equivalent of `@auth0/auth0-react` for a
 * public-client SPA: no client secret is ever held or sent (PKCE replaces
 * it), and every step works against any standards-compliant OIDC provider
 * discovered via `lib/auth/discovery.ts`, not just Auth0.
 */

import { requireOidcConfig } from '@/lib/auth/config';
import { discoverOidcMetadata } from '@/lib/auth/discovery';
import { generateCodeChallenge, generateCodeVerifier, generateRandomToken } from '@/lib/auth/pkce';
import { clearSession, decodeIdTokenClaims, loadSession, saveSession } from '@/lib/auth/tokenStore';
import type { AuthSession } from '@/lib/auth/tokenStore';
import { oidcEnv } from '@/lib/env';

const FLOW_STATE_KEY = 'astradesk_admin_oidc_flow';

type PendingFlow = {
  codeVerifier: string;
  state: string;
  nonce: string;
  returnTo: string;
};

type TokenResponse = {
  access_token: string;
  id_token?: string;
  refresh_token?: string;
  expires_in?: number;
  scope?: string;
};

function assertBrowser(fnName: string): void {
  if (typeof window === 'undefined') {
    throw new Error(`${fnName} can only be called in the browser`);
  }
}

/** Redirects the browser to the identity provider's authorization endpoint. */
export async function startLogin(returnTo: string = '/'): Promise<void> {
  assertBrowser('startLogin');
  const config = requireOidcConfig();
  const metadata = await discoverOidcMetadata(config.issuer);

  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);
  const state = generateRandomToken();
  const nonce = generateRandomToken();

  const pending: PendingFlow = { codeVerifier, state, nonce, returnTo };
  window.sessionStorage.setItem(FLOW_STATE_KEY, JSON.stringify(pending));

  const url = new URL(metadata.authorization_endpoint);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('client_id', config.clientId);
  url.searchParams.set('redirect_uri', config.redirectUri);
  url.searchParams.set('scope', config.scope);
  url.searchParams.set('state', state);
  url.searchParams.set('nonce', nonce);
  url.searchParams.set('code_challenge', codeChallenge);
  url.searchParams.set('code_challenge_method', 'S256');
  if (config.audience) {
    url.searchParams.set('audience', config.audience);
  }

  window.location.assign(url.toString());
}

async function exchangeToken(
  tokenEndpoint: string,
  params: Record<string, string>,
): Promise<AuthSession> {
  const response = await fetch(tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params).toString(),
  });
  if (!response.ok) {
    throw new Error(`OIDC token exchange failed: HTTP ${response.status}`);
  }
  const body = (await response.json()) as TokenResponse;
  if (!body.access_token) {
    throw new Error('OIDC token endpoint response did not include an access_token.');
  }
  return {
    accessToken: body.access_token,
    idToken: body.id_token,
    refreshToken: body.refresh_token,
    expiresAt: Date.now() + (body.expires_in ?? 3600) * 1000,
    scope: body.scope,
  };
}

/**
 * Completes the Authorization Code exchange after the IdP redirects back to
 * `NEXT_PUBLIC_OIDC_REDIRECT_URI`. Validates `state` to guard against CSRF
 * before ever calling the token endpoint.
 */
export async function handleCallback(callbackUrl: string): Promise<{ returnTo: string }> {
  assertBrowser('handleCallback');
  const config = requireOidcConfig();

  const raw = window.sessionStorage.getItem(FLOW_STATE_KEY);
  if (!raw) {
    throw new Error('No pending OIDC login flow found for this callback.');
  }
  window.sessionStorage.removeItem(FLOW_STATE_KEY);
  const pending = JSON.parse(raw) as PendingFlow;

  const parsed = new URL(callbackUrl);
  const providerError = parsed.searchParams.get('error');
  if (providerError) {
    const description = parsed.searchParams.get('error_description');
    throw new Error(`OIDC provider returned an error: ${providerError}${description ? ` (${description})` : ''}`);
  }

  const code = parsed.searchParams.get('code');
  const state = parsed.searchParams.get('state');
  if (!code || !state) {
    throw new Error('OIDC callback is missing the "code" or "state" parameter.');
  }
  if (state !== pending.state) {
    throw new Error('OIDC "state" mismatch on callback; discarding (possible CSRF attempt).');
  }

  const metadata = await discoverOidcMetadata(config.issuer);
  const session = await exchangeToken(metadata.token_endpoint, {
    grant_type: 'authorization_code',
    code,
    redirect_uri: config.redirectUri,
    client_id: config.clientId,
    code_verifier: pending.codeVerifier,
  });

  if (session.idToken) {
    const claims = decodeIdTokenClaims(session.idToken);
    if (claims?.nonce !== pending.nonce) {
      throw new Error('OIDC ID token "nonce" mismatch on callback; discarding (possible replay attempt).');
    }
  }

  saveSession(session);
  return { returnTo: pending.returnTo || '/' };
}

/**
 * Silently exchanges a refresh token for a new access token. Returns `null`
 * (and clears the stored session) on any failure — callers must treat that
 * as "session ended", not retry with a stale token.
 */
export async function refreshSession(): Promise<AuthSession | null> {
  const current = loadSession();
  if (!current?.refreshToken) {
    return null;
  }
  try {
    const config = requireOidcConfig();
    const metadata = await discoverOidcMetadata(config.issuer);
    const session = await exchangeToken(metadata.token_endpoint, {
      grant_type: 'refresh_token',
      refresh_token: current.refreshToken,
      client_id: config.clientId,
    });
    saveSession(session);
    return session;
  } catch {
    clearSession();
    return null;
  }
}

/**
 * Clears the local session and, when the provider supports RP-initiated
 * logout (`end_session_endpoint`), redirects there so the IdP's own session
 * is terminated too — otherwise a subsequent login could silently succeed
 * without re-prompting for credentials.
 */
export async function logout(): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  const session = loadSession();
  clearSession();

  if (!oidcEnv.issuer) {
    window.location.assign('/login');
    return;
  }

  try {
    const metadata = await discoverOidcMetadata(oidcEnv.issuer);
    if (metadata.end_session_endpoint) {
      const url = new URL(metadata.end_session_endpoint);
      if (session?.idToken) {
        url.searchParams.set('id_token_hint', session.idToken);
      }
      if (oidcEnv.clientId) {
        url.searchParams.set('client_id', oidcEnv.clientId);
      }
      const postLogoutRedirectUri = oidcEnv.postLogoutRedirectUri ?? `${window.location.origin}/login`;
      url.searchParams.set('post_logout_redirect_uri', postLogoutRedirectUri);
      window.location.assign(url.toString());
      return;
    }
  } catch {
    // Discovery failed; fall through to a local-only sign-out.
  }
  window.location.assign('/login');
}
