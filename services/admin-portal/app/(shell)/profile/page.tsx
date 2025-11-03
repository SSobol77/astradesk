'use client';

import type { FormEvent } from 'react';
import { useCallback, useMemo, useState } from 'react';
import Badge from '@/components/primitives/Badge';
import Button from '@/components/primitives/Button';
import Card from '@/components/primitives/Card';
import Modal from '@/components/primitives/Modal';
import { Form, FormField, Input, Select } from '@/components/primitives/Form';
import { useToast } from '@/hooks/useToast';

type Session = {
  id: string;
  device: string;
  location: string;
  lastActive: string;
  current: boolean;
};

type UserProfile = {
  name: string;
  email: string;
  role: string;
  timezone: string;
  locale: string;
  lastLogin: string;
  mfaEnabled: boolean;
  sessions: Session[];
};

type NotificationPreference = {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
};

const INITIAL_USER: UserProfile = {
  name: 'Jordan Daniels',
  email: 'admin@example.com',
  role: 'Administrator',
  timezone: 'UTC',
  locale: 'en-US',
  lastLogin: '2024-03-04T09:32:00Z',
  mfaEnabled: true,
  sessions: [
    { id: 'web-1', device: 'Chrome · macOS', location: 'San Francisco, US', lastActive: '2 hours ago', current: true },
    { id: 'web-2', device: 'Safari · iOS', location: 'San Francisco, US', lastActive: 'Yesterday', current: false },
  ],
};

const INITIAL_NOTIFICATIONS: NotificationPreference[] = [
  { key: 'runs', label: 'Run status summaries', description: 'Send a digest when runs finish or fail.', enabled: true },
  { key: 'policies', label: 'Policy publish alerts', description: 'Notify when a policy is promoted to production.', enabled: false },
  { key: 'secrets', label: 'Secret rotation reminders', description: 'Warn before credentials expire.', enabled: true },
];

export default function ProfilePage() {
  const [user, setUser] = useState<UserProfile>(INITIAL_USER);
  const [notifications, setNotifications] = useState<NotificationPreference[]>(INITIAL_NOTIFICATIONS);

  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [securityModalOpen, setSecurityModalOpen] = useState(false);
  const [preferencesModalOpen, setPreferencesModalOpen] = useState(false);

  const [profileDraft, setProfileDraft] = useState(() => ({
    name: INITIAL_USER.name,
    email: INITIAL_USER.email,
    locale: INITIAL_USER.locale,
    timezone: INITIAL_USER.timezone,
  }));
  const [securityDraft, setSecurityDraft] = useState(() => ({
    mfaEnabled: INITIAL_USER.mfaEnabled,
  }));
  const [notificationDraft, setNotificationDraft] = useState<NotificationPreference[]>(INITIAL_NOTIFICATIONS);

  const { push } = useToast();

  const profileSaveDisabled = useMemo(() => {
    const name = profileDraft.name.trim();
    const email = profileDraft.email.trim();
    const hasChanges =
      name !== user.name ||
      email !== user.email ||
      profileDraft.locale !== user.locale ||
      profileDraft.timezone !== user.timezone;
    return !name || !email || !hasChanges;
  }, [profileDraft, user]);

  const securitySaveDisabled = securityDraft.mfaEnabled === user.mfaEnabled;

  const notificationsSaveDisabled = useMemo(() => {
    return !notificationDraft.some((item) => {
      const existing = notifications.find((entry) => entry.key === item.key);
      return existing?.enabled !== item.enabled;
    });
  }, [notificationDraft, notifications]);

  const openProfileModal = () => {
    setProfileDraft({
      name: user.name,
      email: user.email,
      locale: user.locale,
      timezone: user.timezone,
    });
    setProfileModalOpen(true);
  };

  const openSecurityModal = () => {
    setSecurityDraft({ mfaEnabled: user.mfaEnabled });
    setSecurityModalOpen(true);
  };

  const openPreferencesModal = () => {
    setNotificationDraft(notifications);
    setPreferencesModalOpen(true);
  };

  const handleProfileSave = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setUser((current) => ({
      ...current,
      name: profileDraft.name.trim(),
      email: profileDraft.email.trim(),
      locale: profileDraft.locale,
      timezone: profileDraft.timezone,
    }));
    setProfileModalOpen(false);
    push({ title: 'Profile updated', description: 'Account metadata saved locally.', variant: 'success' });
  };

  const handleSecuritySave = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setUser((current) => ({
      ...current,
      mfaEnabled: securityDraft.mfaEnabled,
    }));
    setSecurityModalOpen(false);
    push({ title: 'Security preferences updated', description: 'MFA state synced locally.', variant: 'success' });
  };

  const handleNotificationSave = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setNotifications(notificationDraft);
    setPreferencesModalOpen(false);
    push({ title: 'Notification preferences saved', variant: 'success' });
  };

  const signOutSession = useCallback(
    (id: string) => {
      setUser((current) => ({
        ...current,
        sessions: current.sessions.filter((session) => session.id !== id),
      }));
      push({ title: 'Session ended', description: 'The selected session was signed out.', variant: 'info' });
    },
    [push],
  );

  const localizedLastLogin = useMemo(
    () => new Date(user.lastLogin).toLocaleString(user.locale, { timeZone: user.timezone }),
    [user.lastLogin, user.locale, user.timezone],
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Profile</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your AstraDesk administrator identity, security posture, and personal preferences.
        </p>
      </div>

      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Account</h2>
            <p className="text-sm text-slate-500">Primary metadata associated with your admin account.</p>
          </div>
          <Button type="button" variant="secondary" onClick={openProfileModal}>
            Edit profile
          </Button>
        </div>

        <dl className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Name</dt>
            <dd className="mt-1 text-sm text-slate-900">{user.name}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Email</dt>
            <dd className="mt-1 text-sm text-slate-900">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Role</dt>
            <dd className="mt-1 flex items-center gap-2 text-sm text-slate-900">
              {user.role}
              <Badge variant="neutral">RBAC</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Last login</dt>
            <dd className="mt-1 text-sm text-slate-900">{localizedLastLogin}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Locale</dt>
            <dd className="mt-1 text-sm text-slate-900">{user.locale}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Timezone</dt>
            <dd className="mt-1 text-sm text-slate-900">{user.timezone}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Security</h2>
            <p className="text-sm text-slate-500">
              Review MFA status and manage signed-in sessions. Changes sync instantly across the control plane.
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={openSecurityModal}>
            Manage security
          </Button>
        </div>

        <div className="mt-6 space-y-6">
          <div className="flex items-start justify-between rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div>
              <p className="text-sm font-medium text-slate-900">Multi-factor authentication</p>
              <p className="mt-1 text-sm text-slate-500">Add or reset WebAuthn keys to keep access locked down.</p>
            </div>
            <Badge variant={user.mfaEnabled ? 'success' : 'warn'}>
              {user.mfaEnabled ? 'Enabled' : 'Action required'}
            </Badge>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Active sessions</p>
            <ul className="mt-3 space-y-2">
              {user.sessions.map((session) => (
                <li
                  key={session.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600"
                >
                  <div>
                    <p className="font-medium text-slate-900">{session.device}</p>
                    <p className="text-xs text-slate-500">
                      {session.location} · Last active {session.lastActive}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {session.current ? <Badge variant="success">Current session</Badge> : null}
                    <Button
                      type="button"
                      variant="ghost"
                      className="text-sm text-rose-600"
                      onClick={() => signOutSession(session.id)}
                      disabled={session.current}
                    >
                      Sign out
                    </Button>
                  </div>
                </li>
              ))}
              {user.sessions.length === 0 ? (
                <li className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500">
                  No active sessions.
                </li>
              ) : null}
            </ul>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Notifications</h2>
            <p className="text-sm text-slate-500">
              Toggle which operational events land in your inbox. Email delivery respects organization defaults.
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={openPreferencesModal}>
            Update preferences
          </Button>
        </div>

        <ul className="mt-6 space-y-4">
          {notifications.map((item) => (
            <li key={item.key} className="rounded-lg border border-slate-200 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-900">{item.label}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.description}</p>
                </div>
                <Badge variant={item.enabled ? 'success' : 'warn'}>{item.enabled ? 'Subscribed' : 'Disabled'}</Badge>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Modal
        title="Edit profile"
        isOpen={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
        primaryActionLabel="Save changes"
        onPrimaryAction={() => submitFormById('profile-form')}
        isPrimaryDisabled={profileSaveDisabled}
      >
        <Form
          className="mt-0 space-y-4"
          onSubmit={handleProfileSave}
          id="profile-form"
        >
          <FormField label="Name">
            <Input
              value={profileDraft.name}
              onChange={(event) => setProfileDraft((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </FormField>
          <FormField label="Email">
            <Input
              type="email"
              value={profileDraft.email}
              onChange={(event) => setProfileDraft((current) => ({ ...current, email: event.target.value }))}
              required
            />
          </FormField>
          <FormField label="Locale">
            <Select
              value={profileDraft.locale}
              onChange={(event) => setProfileDraft((current) => ({ ...current, locale: event.target.value }))}
            >
              <option value="en-US">English (US)</option>
              <option value="en-GB">English (UK)</option>
              <option value="pl-PL">Polski</option>
              <option value="zh-CN">中文（简体）</option>
            </Select>
          </FormField>
          <FormField label="Timezone">
            <Select
              value={profileDraft.timezone}
              onChange={(event) => setProfileDraft((current) => ({ ...current, timezone: event.target.value }))}
            >
              <option value="UTC">UTC</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="America/New_York">America/New_York</option>
              <option value="Europe/Warsaw">Europe/Warsaw</option>
              <option value="Asia/Shanghai">Asia/Shanghai</option>
            </Select>
          </FormField>
        </Form>
      </Modal>

      <Modal
        title="Manage security"
        isOpen={securityModalOpen}
        onClose={() => setSecurityModalOpen(false)}
        primaryActionLabel="Save"
        onPrimaryAction={() => submitFormById('security-form')}
        isPrimaryDisabled={securitySaveDisabled}
      >
        <Form
          className="mt-0 space-y-4"
          onSubmit={handleSecuritySave}
          id="security-form"
        >
          <FormField label="Multi-factor authentication">
            <label className="flex items-center gap-3 text-sm text-slate-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                checked={securityDraft.mfaEnabled}
                onChange={(event) => setSecurityDraft({ mfaEnabled: event.target.checked })}
              />
              Require WebAuthn or TOTP during sign-in.
            </label>
          </FormField>
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Sessions</p>
            <ul className="space-y-2">
              {user.sessions.map((session) => (
                <li
                  key={session.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600"
                >
                  <div>
                    <p className="font-medium text-slate-900">{session.device}</p>
                    <p className="text-xs text-slate-500">
                      {session.location} · Last active {session.lastActive}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    className="text-sm text-rose-600"
                    onClick={() => signOutSession(session.id)}
                    disabled={session.current}
                  >
                    Sign out
                  </Button>
                </li>
              ))}
              {user.sessions.length === 0 ? (
                <li className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500">
                  No active sessions.
                </li>
              ) : null}
            </ul>
          </div>
        </Form>
      </Modal>

      <Modal
        title="Notification preferences"
        isOpen={preferencesModalOpen}
        onClose={() => setPreferencesModalOpen(false)}
        primaryActionLabel="Save"
        onPrimaryAction={() => submitFormById('notifications-form')}
        isPrimaryDisabled={notificationsSaveDisabled}
      >
        <Form
          className="mt-0 space-y-4"
          onSubmit={handleNotificationSave}
          id="notifications-form"
        >
          <ul className="space-y-4">
            {notificationDraft.map((item) => (
              <li key={item.key} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{item.label}</p>
                    <p className="mt-1 text-sm text-slate-500">{item.description}</p>
                  </div>
                  <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      checked={item.enabled}
                      onChange={(event) =>
                        setNotificationDraft((current) =>
                          current.map((entry) =>
                            entry.key === item.key ? { ...entry, enabled: event.target.checked } : entry,
                          ),
                        )
                      }
                    />
                    {preferenceStatusLabel(item.enabled)}
                  </label>
                </div>
              </li>
            ))}
          </ul>
        </Form>
      </Modal>
    </div>
  );
}

function preferenceStatusLabel(enabled: boolean) {
  return enabled ? 'Subscribed' : 'Disabled';
}

function submitFormById(formId: string) {
  const form = document.getElementById(formId) as HTMLFormElement | null;
  form?.requestSubmit();
}
