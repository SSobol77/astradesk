import fs from 'node:fs/promises';
import path from 'node:path';
import DomainPacksClient, { type DomainPackAssetMap, type DomainPackInfo } from './DomainPacksClient';
import { openApiClient } from '@/api/client';
import type { DomainPack } from '@/api/types';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const PROJECT_ROOT = path.resolve(process.cwd(), '..', '..');
const PACKAGES_DIR = path.join(PROJECT_ROOT, 'packages');
const DOMAIN_PREFIX = 'domain-';
async function readDirectoryEntries(dir: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(dir);
    return entries.filter((entry) => !entry.startsWith('.')).sort();
  } catch (error) {
    return [];
  }
}

async function readPyprojectMetadata(pyprojectPath: string): Promise<{
  packageName?: string;
  version?: string;
  description?: string;
}> {
  try {
    const content = await fs.readFile(pyprojectPath, 'utf8');
    const getValue = (key: string) => {
      const regex = new RegExp(`^\\s*${key}\\s*=\\s*['\"]([^'\"]+)['\"]`, 'm');
      const match = content.match(regex);
      return match ? match[1] : undefined;
    };
    return {
      packageName: getValue('name'),
      version: getValue('version'),
      description: getValue('description'),
    };
  } catch (error) {
    return {};
  }
}

function formatTitleFromSlug(slug: string): string {
  const core = slug.replace(/^domain-/, '').replace(/-/g, ' ').trim();
  if (!core) {
    return 'Domain Pack';
  }
  const capitalised = core
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  return `${capitalised} Domain Pack`;
}

async function readLocalDomainPacks(): Promise<DomainPackInfo[]> {
  let directoryEntries: Array<{ name: string; isDirectory: boolean }> = [];
  try {
    const entries = await fs.readdir(PACKAGES_DIR, { withFileTypes: true });
    directoryEntries = entries.map((entry) => ({ name: entry.name, isDirectory: entry.isDirectory() }));
  } catch (error) {
    console.error('Failed to read packages directory', error);
    return [];
  }

  const domainDirectories = directoryEntries.filter(
    (entry) => entry.isDirectory && entry.name.startsWith(DOMAIN_PREFIX),
  );

  const packs = await Promise.all(
    domainDirectories.map(async ({ name }) => {
      const packPath = path.join(PACKAGES_DIR, name);
      const pyprojectPath = path.join(packPath, 'pyproject.toml');
      const metadata = await readPyprojectMetadata(pyprojectPath);

      const assets: DomainPackAssetMap = {
        agents: await readDirectoryEntries(path.join(packPath, 'agents')),
        flows: await readDirectoryEntries(path.join(packPath, 'flows')),
        tools: await readDirectoryEntries(path.join(packPath, 'tools')),
        policies: await readDirectoryEntries(path.join(packPath, 'policies')),
      };

      return {
        slug: name,
        title: formatTitleFromSlug(name),
        packageName: metadata.packageName ?? name,
        localVersion: metadata.version,
        description: metadata.description,
        remoteVersion: undefined,
        status: 'available' as DomainPackInfo['status'],
        assets,
      } satisfies DomainPackInfo;
    }),
  );

  return packs.sort((a, b) => a.title.localeCompare(b.title));
}

async function getRemoteDomainPacks(): Promise<DomainPack[]> {
  const hostname = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!hostname) {
    return [];
  }
  if (hostname.includes('simulation.local')) {
    return [];
  }
  try {
    return await openApiClient.domainPacks.list();
  } catch (error) {
    console.error('Failed to fetch domain packs from API', error);
    return [];
  }
}

function mergeDomainPackData(local: DomainPackInfo[], remote: DomainPack[]): DomainPackInfo[] {
  const remoteMap = new Map<string, DomainPack>();
  remote.forEach((pack) => {
    if (pack.name) {
      remoteMap.set(pack.name, pack);
    }
  });

  const matchedRemoteNames = new Set<string>();

  const enrichedLocal = local.map((pack) => {
    const candidateNames = new Set<string>();
    candidateNames.add(pack.slug);
    candidateNames.add(pack.slug.replace(/-/g, '_'));
    if (pack.slug.startsWith(DOMAIN_PREFIX)) {
      candidateNames.add(`astradesk-${pack.slug}`);
      candidateNames.add(`astradesk_${pack.slug.replace(/-/g, '_')}`);
    } else {
      candidateNames.add(`${DOMAIN_PREFIX}${pack.slug}`);
    }
    if (pack.packageName) {
      candidateNames.add(pack.packageName);
      candidateNames.add(pack.packageName.replace(/_/g, '-'));
      candidateNames.add(pack.packageName.replace(/-/g, '_'));
    }

    const remoteMatch = Array.from(candidateNames)
      .map((candidate) => remoteMap.get(candidate))
      .find((value) => value !== undefined);

    if (remoteMatch?.name) {
      matchedRemoteNames.add(remoteMatch.name);
    }

    return {
      ...pack,
      remoteVersion: remoteMatch?.version ?? pack.remoteVersion,
      status: remoteMatch?.status ?? pack.status,
    } satisfies DomainPackInfo;
  });

  const missingRemote = remote.filter((pack) => pack.name && !matchedRemoteNames.has(pack.name));

  const remoteOnly: DomainPackInfo[] = missingRemote.map((pack) => {
    const slug = pack.name ?? 'domain-pack';
    return {
      slug,
      title: formatTitleFromSlug(slug),
      packageName: pack.name ?? slug,
      localVersion: undefined,
      remoteVersion: pack.version,
      description: undefined,
      status: (pack.status as DomainPackInfo['status']) ?? 'installed',
      assets: { agents: [], flows: [], tools: [], policies: [] },
    } satisfies DomainPackInfo;
  });

  const combined = [...enrichedLocal, ...remoteOnly];
  combined.sort((a, b) => a.title.localeCompare(b.title));
  return combined;
}

export default async function DomainPacksPage() {
  const [localPacks, remotePacks] = await Promise.all([readLocalDomainPacks(), getRemoteDomainPacks()]);
  const packs = mergeDomainPackData(localPacks, remotePacks);
  return <DomainPacksClient packs={packs} />;
}
