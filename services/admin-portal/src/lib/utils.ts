// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/src/lib/utils.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/src/lib/utils.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import { type ClassValue, clsx } from 'clsx';

// Lightweight className concat helper used across `src/` code. We avoid pulling in
// `tailwind-merge` here to keep the build simple in environments where that
// package may not be installed. Using `clsx` is sufficient for our usage.
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}
