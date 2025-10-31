import type { Breadcrumb, QuickCreateLink } from '@/lib/types';
import { pathsMap } from '@/api/operations-map';
import type { QueryParamMeta } from '@/api/operations-map';

const quickCreateConfig: Array<
  { resource: keyof typeof pathsMap; operation: string } & QuickCreateLink
> = [
  { resource: 'agents', operation: 'create', label: 'New Agent', pathname: '/agents', query: { create: '1' } },
  { resource: 'flows', operation: 'create', label: 'New Flow', pathname: '/flows', query: { create: '1' } },
  { resource: 'datasets', operation: 'create', label: 'New Dataset', pathname: '/datasets', query: { create: '1' } },
  { resource: 'tools', operation: 'create', label: 'New Connector', pathname: '/tools', query: { create: '1' } },
  { resource: 'secrets', operation: 'create', label: 'New Secret', pathname: '/secrets', query: { create: '1' } },
  { resource: 'jobs', operation: 'create', label: 'New Job', pathname: '/jobs', query: { create: '1' } },
  {
    resource: 'rbac',
    operation: 'create',
    label: 'Invite User',
    pathname: '/rbac',
    query: { tab: 'users', invite: '1' },
  },
  { resource: 'policies', operation: 'create', label: 'Create Policy', pathname: '/policies', query: { create: '1' } },
];

const breadcrumbMap: Array<{ test: RegExp; crumbs: Breadcrumb[] }> = [
  { test: /^\/$/, crumbs: [{ href: '/', label: 'Dashboard' }] },
  { test: /^\/agents$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/agents', label: 'Agents' }] },
  {
    test: /^\/agents\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/agents', label: 'Agents' },
      { href: '#', label: 'Agent detail' },
    ],
  },
  { test: /^\/intent-graph$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/intent-graph', label: 'Intent Graph' }] },
  { test: /^\/flows$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/flows', label: 'Flows' }] },
  {
    test: /^\/flows\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/flows', label: 'Flows' },
      { href: '#', label: 'Flow detail' },
    ],
  },
  { test: /^\/datasets$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/datasets', label: 'Datasets' }] },
  {
    test: /^\/datasets\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/datasets', label: 'Datasets' },
      { href: '#', label: 'Dataset detail' },
    ],
  },
  { test: /^\/tools$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/tools', label: 'Tools & Connectors' }] },
  {
    test: /^\/tools\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/tools', label: 'Tools & Connectors' },
      { href: '#', label: 'Connector detail' },
    ],
  },
  { test: /^\/secrets$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/secrets', label: 'Keys & Secrets' }] },
  { test: /^\/runs$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/runs', label: 'Runs & Logs' }] },
  {
    test: /^\/runs\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/runs', label: 'Runs & Logs' },
      { href: '#', label: 'Run detail' },
    ],
  },
  { test: /^\/jobs$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/jobs', label: 'Jobs & Schedules' }] },
  {
    test: /^\/jobs\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/jobs', label: 'Jobs & Schedules' },
      { href: '#', label: 'Job detail' },
    ],
  },
  { test: /^\/rbac$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/rbac', label: 'Users & Roles' }] },
  { test: /^\/policies$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/policies', label: 'Policies' }] },
  {
    test: /^\/policies\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/policies', label: 'Policies' },
      { href: '#', label: 'Policy detail' },
    ],
  },
  { test: /^\/audit$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/audit', label: 'Audit Trail' }] },
  {
    test: /^\/audit\//,
    crumbs: [
      { href: '/', label: 'Dashboard' },
      { href: '/audit', label: 'Audit Trail' },
      { href: '#', label: 'Audit detail' },
    ],
  },
  { test: /^\/settings$/, crumbs: [{ href: '/', label: 'Dashboard' }, { href: '/settings', label: 'Settings' }] },
];

export function hasOperation<Resource extends keyof typeof pathsMap>(
  resource: Resource,
  operation: keyof (typeof pathsMap)[Resource] | string,
) {
  const descriptor = pathsMap[resource] as Record<string, unknown>;
  return Boolean(descriptor?.[operation as string]);
}

export function getQuickCreateLinks(): QuickCreateLink[] {
  return quickCreateConfig
    .filter((item) => hasOperation(item.resource, item.operation))
    .map(({ label, pathname, query }) => ({ label, pathname, query }));
}

export function getBreadcrumbs(pathname: string): Breadcrumb[] {
  const entry = breadcrumbMap.find((item) => item.test.test(pathname));
  return entry?.crumbs ?? [{ href: '/', label: 'Dashboard' }];
}

export function getQueryParamsFor<Resource extends keyof typeof pathsMap>(
  resource: Resource,
  operation: keyof (typeof pathsMap)[Resource] | string,
): QueryParamMeta[] {
  const descriptor = (pathsMap[resource] as Record<string, { query?: QueryParamMeta[] }>)[operation as string];
  return (descriptor?.query as QueryParamMeta[] | undefined) ?? [];
}
