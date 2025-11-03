'use client';

import { useState } from 'react';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import { Form, FormField, Input, Select } from '@/components/primitives/Form';
import Button from '@/components/primitives/Button';
import type { User } from '@/api/types';
import { openApiClient } from '@/api/client';
import { useToast } from '@/hooks/useToast';
import { useRouter } from 'next/navigation';
import { useConfirm } from '@/hooks/useConfirm';
import { ApiError } from '@/lib/api';

const ROLE_OPTIONS: Array<User['role']> = ['admin', 'operator', 'viewer'];

export default function UsersTab({ users }: { users: User[] }) {
  const router = useRouter();
  const { push } = useToast();
  const { confirm, ConfirmDialog } = useConfirm();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<NonNullable<User['role']>>('viewer' as NonNullable<User['role']>);
  const [isSubmitting, setSubmitting] = useState(false);

  const handleInvite = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      push({ 
        title: 'Email is required',
        description: 'Please provide a valid email address',
        variant: 'error'
      });
      return;
    }
    
    setSubmitting(true);
    try {
      await openApiClient.rbac.create({ 
        email: trimmedEmail, 
        role
      });
      
      push({ 
        title: 'User invited successfully',
        description: `Invitation sent to ${trimmedEmail} with ${role} role`,
        variant: 'success'
      });

      setEmail('');
      router.refresh();
    } catch (error) {
      console.error('Invite user failed:', error);
      push({
        title: 'Failed to invite user',
        description: error instanceof ApiError ? error.problem?.detail : 'Network error occurred',
        variant: 'error'
      });
    } finally {
      setSubmitting(false);
    }
    
  };

  const handleView = async (user: User) => {
    if (!user.id) return;
    try {
      const detail = await openApiClient.rbac.get(user.id);
      push({ title: 'User detail', description: JSON.stringify(detail, null, 2), variant: 'info' });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        push({ title: 'User not found', variant: 'warn' });
        return;
      }
      push({ title: 'Failed to fetch user', variant: 'error' });
    }
  };

  const handleUpdateRole = async (user: User) => {
    if (!user.id) return;
  const nextRole = globalThis.prompt?.('Set role (admin, operator, viewer)', user.role ?? 'viewer');
    if (!nextRole) return;
    if (!ROLE_OPTIONS.includes(nextRole as User['role'])) {
      push({ title: 'Invalid role', variant: 'error' });
      return;
    }
    try {
      await openApiClient.rbac.updateRole(user.id, nextRole as User['role']);
      push({ title: 'Role updated', variant: 'success' });
      router.refresh();
    } catch (error) {
      push({ title: 'Failed to update role', variant: 'error' });
    }
  };

  const handleResetMfa = async (user: User) => {
    if (!user.id) return;
    try {
      await openApiClient.rbac.resetMfa(user.id);
      push({ title: 'MFA reset requested', variant: 'info' });
    } catch (error) {
      push({ title: 'Failed to reset MFA', variant: 'error' });
    }
  };

  const handleDelete = async (user: User) => {
    if (!user.id) return;
    // Use the shared confirmation hook for a consistent modal UX
    const confirmed = await confirm({
      title: 'Remove user',
      message: `Remove user "${user.email ?? user.id}"?`,
      confirmText: 'Remove',
      cancelText: 'Cancel',
    });
    if (!confirmed) return;
    try {
      await openApiClient.rbac.delete(user.id);
      push({ title: 'User removed', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete user failed:', error);
      push({ title: 'Failed to delete user', variant: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      {ConfirmDialog}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900">Invite User</h3>
            <p className="text-sm text-slate-500">POST /users</p>
          </div>
        </div>
        <Form className="mt-4" onSubmit={handleInvite}>
          <FormField label="Email">
            <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </FormField>
          <FormField label="Role">
            <Select value={role} onChange={(event) => setRole(event.target.value as NonNullable<User['role']>)}>
              {ROLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </FormField>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              Invite
            </Button>
          </div>
        </Form>
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900">Users</h3>
            <p className="text-sm text-slate-500">GET /users</p>
          </div>
        </div>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: 'email', header: 'Email' },
              { key: 'role', header: 'Role' },
              { key: 'id', header: 'User ID' },
              {
                key: 'actions',
                header: 'Actions',
                render: (userRow: User) => (
                  <div className="flex flex-wrap gap-2">
                    <button type="button" className="text-indigo-600 hover:underline" onClick={() => handleView(userRow)}>
                      View
                    </button>
                    <button type="button" className="text-indigo-600 hover:underline" onClick={() => handleUpdateRole(userRow)}>
                      Update Role
                    </button>
                    <button type="button" className="text-indigo-600 hover:underline" onClick={() => handleResetMfa(userRow)}>
                      Reset MFA
                    </button>
                    <button type="button" className="text-rose-600 hover:underline" onClick={() => handleDelete(userRow)}>
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
            data={users}
            emptyState={<p>No users invited yet.</p>}
          />
        </div>
      </Card>
    </div>
  );
}
