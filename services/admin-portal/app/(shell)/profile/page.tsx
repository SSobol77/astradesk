import Card from '@/components/primitives/Card';
import Badge from '@/components/primitives/Badge';
import Button from '@/components/primitives/Button';

const MOCK_USER = {
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

const MOCK_NOTIFICATIONS = [
  { key: 'runs', label: 'Run status summaries', description: 'Send a digest when runs finish or fail.', enabled: true },
  { key: 'policies', label: 'Policy publish alerts', description: 'Notify when a policy is promoted to production.', enabled: false },
  { key: 'secrets', label: 'Secret rotation reminders', description: 'Warn before credentials expire.', enabled: true },
];

export default function ProfilePage() {
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
          <Button type="button" variant="secondary" disabled>
            Edit profile
          </Button>
        </div>

        <dl className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Name</dt>
            <dd className="mt-1 text-sm text-slate-900">{MOCK_USER.name}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Email</dt>
            <dd className="mt-1 text-sm text-slate-900">{MOCK_USER.email}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Role</dt>
            <dd className="mt-1 flex items-center gap-2 text-sm text-slate-900">
              {MOCK_USER.role}
              <Badge variant="neutral">RBAC</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Last login</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {new Date(MOCK_USER.lastLogin).toLocaleString(MOCK_USER.locale, { timeZone: MOCK_USER.timezone })}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Locale</dt>
            <dd className="mt-1 text-sm text-slate-900">{MOCK_USER.locale}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Timezone</dt>
            <dd className="mt-1 text-sm text-slate-900">UTC</dd>
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
          <Button type="button" variant="secondary" disabled>
            Manage security
          </Button>
        </div>

        <div className="mt-6 space-y-6">
          <div className="flex items-start justify-between rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div>
              <p className="text-sm font-medium text-slate-900">Multi-factor authentication</p>
              <p className="mt-1 text-sm text-slate-500">
                Add or reset webauthn keys to keep access locked down.
              </p>
            </div>
            <Badge variant={MOCK_USER.mfaEnabled ? 'success' : 'warn'}>
              {MOCK_USER.mfaEnabled ? 'Enabled' : 'Action required'}
            </Badge>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Active sessions</p>
            <ul className="mt-3 space-y-2">
              {MOCK_USER.sessions.map((session) => (
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
                    <Button type="button" variant="ghost" className="text-sm text-rose-600" disabled>
                      Sign out
                    </Button>
                  </div>
                </li>
              ))}
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
          <Button type="button" variant="secondary" disabled>
            Update preferences
          </Button>
        </div>

        <ul className="mt-6 space-y-4">
          {MOCK_NOTIFICATIONS.map((item) => (
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
    </div>
  );
}
