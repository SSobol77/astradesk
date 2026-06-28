// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/rbac/page.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/rbac/page.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import Card from '@/components/primitives/Card';
import { Tabs } from '@/components/primitives/Tabs';
import { openApiClient } from '@/api/client';
import type { User } from '@/api/types';
import UsersTab from './UsersTab';

async function getUsers(): Promise<User[]> {
  try {
    return await openApiClient.rbac.users();
  } catch (error) {
    console.error('Failed to load users', error);
    return [];
  }
}

async function getRoles(): Promise<string[]> {
  try {
    return await openApiClient.rbac.roles();
  } catch (error) {
    console.error('Failed to load roles', error);
    return [];
  }
}

export default async function RbacPage() {
  const [users, roles] = await Promise.all([getUsers(), getRoles()]);

  return (
    <Tabs
      tabs={[
      {
        key: 'users',
        label: 'Users',
        content: (
          <UsersTab users={users} />
        ),
      },
        {
          key: 'roles',
          label: 'Roles',
          content: (
            <Card>
              <h3 className="text-base font-semibold text-slate-900">Roles</h3>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {roles.length ? roles.map((role) => <li key={role}>{role}</li>) : <li>No roles configured.</li>}
              </ul>
            </Card>
          ),
        },
      ]}
    />
  );
}
