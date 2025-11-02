'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import DataTable from '@/components/data/DataTable';
import Card from '@/components/primitives/Card';
import Button from '@/components/primitives/Button';
import { openApiClient } from '@/api/client';
import type { DomainPack } from '@/api/types';
import { useToast } from '@/hooks/useToast';

export default function DomainPacksClient({ packs }: { packs: DomainPack[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [isActioning, setActioning] = useState<string | null>(null);

  const handleInstall = async (pack: DomainPack) => {
    if (!pack.name) return;
    setActioning(pack.name);
    try {
      await openApiClient.domainPacks.install(pack.name);
      push({ title: `Install triggered for ${pack.name}`, variant: 'success' });
      router.refresh();
    } catch (error) {
      console.error('Install domain pack failed', error);
      push({ title: 'Failed to install domain pack', variant: 'error' });
    } finally {
      setActioning(null);
    }
  };

  const handleUninstall = async (pack: DomainPack) => {
    if (!pack.name) return;
    const confirmed = window.confirm(`Uninstall ${pack.name}?`);
    if (!confirmed) return;
    setActioning(pack.name);
    try {
      await openApiClient.domainPacks.uninstall(pack.name);
      push({ title: `Uninstall triggered for ${pack.name}`, variant: 'info' });
      router.refresh();
    } catch (error) {
      console.error('Uninstall domain pack failed', error);
      push({ title: 'Failed to uninstall domain pack', variant: 'error' });
    } finally {
      setActioning(null);
    }
  };

  return (
    <Card>
      <h2 className="text-lg font-semibold text-slate-900">Domain Packs</h2>
      <p className="text-sm text-slate-500">GET /domain-packs</p>
      <div className="mt-4">
        <DataTable
          columns={[
            { key: 'name', header: 'Name' },
            { key: 'version', header: 'Version' },
            { key: 'status', header: 'Status' },
            {
              key: 'actions',
              header: 'Actions',
              render: (pack: DomainPack) => (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={isActioning === pack.name}
                    onClick={() => handleInstall(pack)}
                  >
                    Install
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={isActioning === pack.name}
                    onClick={() => handleUninstall(pack)}
                  >
                    Uninstall
                  </Button>
                </div>
              ),
            },
          ]}
          data={packs}
          emptyState={<p>No domain packs available.</p>}
        />
      </div>
    </Card>
  );
}
