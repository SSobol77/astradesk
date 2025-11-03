'use client';

import { useState } from 'react';
import type { TableColumn } from '@/components/data/DataTable';
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

const ROLE_OPTIONS = ['admin', 'operator', 'viewer'] as const;
type Role = typeof ROLE_OPTIONS[number];

export default function UsersTab({ users }: { users: User[] }) {
  const router = useRouter();
  const { push } = useToast();
  const { confirm } = useConfirm();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<Role>('viewer');
  const [submitting, setSubmitting] = useState(false);

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

  const handleRoleUpdate = async (userId: string | undefined, newRole: Role) => {
    if (!userId) {
      push({ title: 'Invalid user', variant: 'error' });
      return;
    }

    try {
      await openApiClient.rbac.updateRole(userId, newRole);
      push({ title: 'Role updated', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Update role failed:', error);
      push({
        title: 'Failed to update role',
        description: error instanceof ApiError ? error.problem?.detail : 'Network error occurred',
        variant: 'error'
      });
    }
  };

  const handleDelete = async (userId: string | undefined, userEmail?: string) => {
    if (!userId) {
      push({ title: 'Invalid user', variant: 'error' });
      return;
    }

    try {
      const confirmed = await confirm({
        title: 'Remove user',
        message: `Are you sure you want to remove user ${userEmail || userId}?`,
        confirmText: 'Remove',
        cancelText: 'Cancel',
      });
      
      if (!confirmed) {
        return;
      }

      await openApiClient.rbac.delete(userId);
      push({ title: 'User removed', variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Delete user failed:', error);
      push({
        title: 'Failed to delete user',
        description: error instanceof ApiError ? error.problem?.detail : 'Network error occurred',
        variant: 'error'
      });
    }
  };

  const columns: Array<TableColumn<User>> = [
    {
      key: 'email',
      header: 'Email',
      render: (user) => user.email || user.id
    },
    {
      key: 'role',
      header: 'Role',
      render: (user) => (
        <Select
          value={user.role}
          onChange={(e) => handleRoleUpdate(user.id, e.target.value as Role)}
          className="w-32"
        >
          {ROLE_OPTIONS.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </Select>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (user) => (
        <Button
          variant="ghost"
          className="text-sm px-2 py-1"
          onClick={() => handleDelete(user.id, user.email)}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="mb-8">
        <Card>
          <Form onSubmit={handleInvite}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Email">
                <Input
                  type="email"
                  name="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </FormField>
              <FormField label="Role">
                <Select
                  name="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                >
                  {ROLE_OPTIONS.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </Select>
              </FormField>
            </div>
            <div className="mt-4 flex justify-end">
              <Button type="submit" disabled={submitting}>
                {submitting ? 'Inviting...' : 'Invite User'}
              </Button>
            </div>
          </Form>
        </Card>
      </div>

      <DataTable
        columns={columns}
        data={users}
      />
    </>
  );
}