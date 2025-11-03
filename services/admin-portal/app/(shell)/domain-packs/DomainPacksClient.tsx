'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import { useToast } from '@/hooks/useToast';

export type DomainPackAssetMap = {
  agents: string[];
  flows: string[];
  tools: string[];
  policies: string[];
};

export type DomainPackInfo = {
  slug: string;
  title: string;
  packageName: string;
  localVersion?: string;
  remoteVersion?: string;
  description?: string;
  status: 'available' | 'installed' | 'error' | 'disabled';
  assets: DomainPackAssetMap;
};

const STATUS_LABEL: Record<DomainPackInfo['status'], string> = {
  available: 'Available (not installed)',
  installed: 'Installed',
  error: 'Error',
  disabled: 'Disabled',
};

export default function DomainPacksClient({ packs }: { packs: DomainPackInfo[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [isActioning, setActioning] = useState<string | null>(null);

  const handleInstall = async (pack: DomainPackInfo) => {
    setActioning(pack.slug);
    try {
      await openApiClient.domainPacks.install(pack.slug);
      push({ title: `Install triggered for ${pack.title}`, variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Install domain pack failed', error);
      push({ title: 'Failed to install domain pack', variant: 'error' });
    } finally {
      setActioning(null);
    }
  };

  const handleUninstall = async (pack: DomainPackInfo) => {
  const confirmed = globalThis.confirm?.(`Uninstall ${pack.title}?`);
    if (!confirmed) return;
    setActioning(pack.slug);
    try {
      await openApiClient.domainPacks.uninstall(pack.slug);
      push({ title: `Uninstall triggered for ${pack.title}`, variant: 'info' });
      router.refresh();
    } catch (error) {
      console.error('Uninstall domain pack failed', error);
      push({ title: 'Failed to uninstall domain pack', variant: 'error' });
    } finally {
      setActioning(null);
    }
  };

  return (
    <DataTable
      title="Domain Packs"
      description="Local packages + GET /domain-packs"
      columns={[
        {
          key: 'title',
          header: 'Name',
          render: (pack: DomainPackInfo) => (
            <div>
              <div className="font-medium text-slate-900">{pack.title}</div>
              <div className="text-xs text-slate-500">{pack.packageName}</div>
              {pack.description ? <p className="mt-1 text-xs text-slate-500">{pack.description}</p> : null}
            </div>
          ),
        },
        {
          key: 'localVersion',
          header: 'Local Version',
          render: (pack: DomainPackInfo) => pack.localVersion ?? '—',
        },
        {
          key: 'remoteVersion',
          header: 'Installed Version',
          render: (pack: DomainPackInfo) => pack.remoteVersion ?? '—',
        },
        {
          key: 'agents',
          header: 'Agents',
          render: (pack: DomainPackInfo) => pack.assets.agents.length,
        },
        {
          key: 'flows',
          header: 'Flows',
          render: (pack: DomainPackInfo) => pack.assets.flows.length,
        },
        {
          key: 'tools',
          header: 'Tools',
          render: (pack: DomainPackInfo) => pack.assets.tools.length,
        },
        {
          key: 'policies',
          header: 'Policies',
          render: (pack: DomainPackInfo) => pack.assets.policies.length,
        },
        {
          key: 'status',
          header: 'Status',
          render: (pack: DomainPackInfo) => STATUS_LABEL[pack.status] ?? pack.status ?? 'Unknown',
        },
        {
          key: 'actions',
          header: 'Actions',
          render: (pack: DomainPackInfo) => {
            const isInstalled = pack.status === 'installed';
            const disableInstall = isActioning === pack.slug || isInstalled;
            const disableUninstall = isActioning === pack.slug || !isInstalled;
            return (
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={disableInstall}
                  onClick={() => handleInstall(pack)}
                >
                  Install
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={disableUninstall}
                  onClick={() => handleUninstall(pack)}
                >
                  Uninstall
                </Button>
              </div>
            );
          },
        },
      ]}
      data={packs}
      emptyState={<p>No domain packs available.</p>}
    />
  );
}
