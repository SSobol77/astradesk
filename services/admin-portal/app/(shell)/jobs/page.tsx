// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/jobs/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/jobs/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import JobsClient from './JobsClient';
import { openApiClient } from '@/api/client';
import type { DlqItem, Job } from '@/api/types';

async function getJobs(): Promise<Job[]> {
  try {
    return await openApiClient.jobs.list();
  } catch (error) {
    console.error('Failed to load jobs', error);
    return [];
  }
}

async function getDlq(): Promise<DlqItem[]> {
  try {
    return await openApiClient.jobs.dlq();
  } catch (error) {
    console.error('Failed to load DLQ', error);
    return [];
  }
}

export default async function JobsPage() {
  const [jobs, dlq] = await Promise.all([getJobs(), getDlq()]);

  return <JobsClient jobs={jobs} dlq={dlq} />;
}
