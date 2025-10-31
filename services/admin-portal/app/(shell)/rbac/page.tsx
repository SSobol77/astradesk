import Card from '@/components/primitives/Card';
import DataTable from '@/components/data/DataTable';
import { Tabs } from '@/components/primitives/Tabs';
import { openApiClient } from '@/api/client';
import type { User } from '@/api/types';

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
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-slate-900">Users</h3>
                  <p className="text-sm text-slate-500">GET /users</p>
                </div>
                <a
                  href="/rbac?tab=users&invite=1"
                  className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
                >
                  Invite User
                </a>
              </div>
              <div className="mt-4">
                <DataTable
                  columns={[
                    { key: 'email', header: 'Email' },
                    { key: 'role', header: 'Role' },
                    { key: 'id', header: 'User ID' },
                  ]}
                  data={users}
                  emptyState={<p>No users invited yet.</p>}
                />
              </div>
            </Card>
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
