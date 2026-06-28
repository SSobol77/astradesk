// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/lib/types.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/lib/types.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import type { Route } from 'next';

export type Breadcrumb = {
  label: string;
  href: Route | '#';
};

export type QuickCreateLink = {
  label: string;
  pathname: Route;
  query?: Record<string, string>;
};
