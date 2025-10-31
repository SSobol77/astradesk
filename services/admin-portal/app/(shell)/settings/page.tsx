import SettingsClient from './SettingsClient';
import { openApiClient } from '@/api/client';
import type { Setting } from '@/api/types';

async function fetchSettings() {
  const [integrations, localization, platform] = await Promise.all([
    openApiClient.settings.list('integrations'),
    openApiClient.settings.list('localization'),
    openApiClient.settings.list('platform'),
  ]);

  return { integrations, localization, platform } satisfies {
    integrations: Setting[];
    localization: Setting[];
    platform: Setting[];
  };
}

export default async function SettingsPage() {
  const settings = await fetchSettings();

  return <SettingsClient {...settings} />;
}
