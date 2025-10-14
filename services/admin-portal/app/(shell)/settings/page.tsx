import SettingsClient from './SettingsClient';
import { openApiClient } from '@/openapi/openapi-client';
import type { SettingsGroup } from '@/openapi/openapi-types';

async function fetchSettings() {
  const [integrations, localization, platform] = await Promise.all([
    openApiClient.settings.integrations(),
    openApiClient.settings.localization(),
    openApiClient.settings.platform(),
  ]);

  return { integrations, localization, platform } satisfies {
    integrations: SettingsGroup;
    localization: SettingsGroup;
    platform: SettingsGroup;
  };
}

export default async function SettingsPage() {
  const settings = await fetchSettings();

  return <SettingsClient {...settings} />;
}
