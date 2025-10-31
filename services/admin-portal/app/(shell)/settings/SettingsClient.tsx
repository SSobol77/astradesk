'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { Form, FormField, Textarea } from '@/components/primitives/Form';
import { Tabs } from '@/components/primitives/Tabs';
import { useToast } from '@/hooks/useToast';
import { openApiClient } from '@/api/client';
import type { Setting } from '@/api/types';

function asPretty(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

export default function SettingsClient({
  integrations,
  localization,
  platform,
}: {
  integrations: Setting[];
  localization: Setting[];
  platform: Setting[];
}) {
  const { push } = useToast();

  const [integrationSetting, setIntegrationSetting] = useState<Setting>(
    integrations[0] ?? { group: 'integrations', key: 'config', value: {} },
  );
  const [localizationSetting, setLocalizationSetting] = useState<Setting>(
    localization[0] ?? { group: 'localization', key: 'defaults', value: {} },
  );
  const [platformSetting, setPlatformSetting] = useState<Setting>(
    platform[0] ?? { group: 'platform', key: 'timezone', value: { timezone: 'UTC' } },
  );

  const [integrationJson, setIntegrationJson] = useState(asPretty(integrationSetting.value ?? {}));
  const [localizationJson, setLocalizationJson] = useState(asPretty(localizationSetting.value ?? {}));
  const [platformJson, setPlatformJson] = useState(asPretty(platformSetting.value ?? {}));
  const [isSaving, setIsSaving] = useState(false);

  const save = async (
    group: 'integrations' | 'localization' | 'platform',
    current: Setting,
    jsonValue: string,
    onSettingChange: (next: Setting) => void,
    onJsonChange: (next: string) => void,
  ) => {
    try {
      setIsSaving(true);
      const payload = JSON.parse(jsonValue) as Record<string, unknown>;
      const key = current.key ?? 'value';
      const result = await openApiClient.settings.update(group, { key, value: payload });
      onSettingChange(result);
      onJsonChange(asPretty(result.value ?? {}));
      push({ title: 'Settings updated', variant: 'success' });
    } catch (error) {
      push({ title: 'Failed to update settings', variant: 'error' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Tabs
      tabs={[
        {
          key: 'integrations',
          label: 'Integrations',
          content: (
            <Form onSubmit={(event) => event.preventDefault()}>
              <FormField label={`Integration: ${integrationSetting.key ?? 'config'}`} description="GET/PUT /settings/integrations">
                <Textarea
                  rows={12}
                  value={integrationJson}
                  onChange={(event) => setIntegrationJson(event.target.value)}
                />
              </FormField>
              <Button
                type="button"
                onClick={() => save('integrations', integrationSetting, integrationJson, setIntegrationSetting, setIntegrationJson)}
                disabled={isSaving}
              >
                Save Changes
              </Button>
            </Form>
          ),
        },
        {
          key: 'localization',
          label: 'Localization',
          content: (
            <Form onSubmit={(event) => event.preventDefault()}>
              <FormField label={`Localization: ${localizationSetting.key ?? 'defaults'}`} description="GET/PUT /settings/localization">
                <Textarea
                  rows={12}
                  value={localizationJson}
                  onChange={(event) => setLocalizationJson(event.target.value)}
                />
              </FormField>
              <Button
                type="button"
                onClick={() =>
                  save('localization', localizationSetting, localizationJson, setLocalizationSetting, setLocalizationJson)
                }
                disabled={isSaving}
              >
                Save Changes
              </Button>
            </Form>
          ),
        },
        {
          key: 'platform',
          label: 'Platform',
          content: (
            <Form onSubmit={(event) => event.preventDefault()}>
              <FormField label={`Platform: ${platformSetting.key ?? 'platform'}`} description="GET/PUT /settings/platform">
                <Textarea
                  rows={12}
                  value={platformJson}
                  onChange={(event) => setPlatformJson(event.target.value)}
                />
              </FormField>
              <Button
                type="button"
                onClick={() => save('platform', platformSetting, platformJson, setPlatformSetting, setPlatformJson)}
                disabled={isSaving}
              >
                Save Changes
              </Button>
            </Form>
          ),
        },
      ]}
    />
  );
}
