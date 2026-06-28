// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/src/components/primitives/Button.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/src/components/primitives/Button.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

// Re-export the non-src Button implementation located under `components/primitives`.
// This avoids pulling in extra runtime/dev dependencies (like class-variance-authority)
// into the TypeScript type-checker when the project is configured to include both
// `src/` and `components/` in the compile scope.
export { default } from '@/components/primitives/Button';
