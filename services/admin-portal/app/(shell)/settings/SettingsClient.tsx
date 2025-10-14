'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { Form, FormField, Textarea } from '@/components/primitives/Form';
import { Tabs } from '@/components/primitives/Tabs';
import { useToast } from '@/hooks/useToast';
import { openApiClient } from '@/openapi/openapi-client';
import type { SettingsGroup } from '@/openapi/openapi-types';

function asPretty(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

export default function SettingsClient({
  integrations,
  localization,
  platform,
}: {
  integrations: SettingsGroup;
  localization: SettingsGroup;
  platform: SettingsGroup;
}) {
  const { push } = useToast();

  const [integrationJson, setIntegrationJson] = useState(asPretty(integrations.value));
  const [localizationJson, setLocalizationJson] = useState(asPretty(localization.value));
  const [platformJson, setPlatformJson] = useState(asPretty(platform.value));
  const [isSaving, setIsSaving] = useState(false);

  const save = async (type: 'integrations' | 'localization' | 'platform') => {
    try {
      setIsSaving(true);
      const payload = JSON.parse(
        type === 'integrations' ? integrationJson : type === 'localization' ? localizationJson : platformJson,
      );
      if (type === 'integrations') {
        await openApiClient.settings.updateIntegrations({ ...integrations, value: payload });
      } else if (type === 'localization') {
        await openApiClient.settings.updateLocalization({ ...localization, value: payload });
      } else {
        await openApiClient.settings.updatePlatform({ ...platform, value: payload });
      }
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
              <FormField label="Integration Config" description="GET/PUT /settings/integrations">
                <Textarea
                  rows={12}
                  value={integrationJson}
                  onChange={(event) => setIntegrationJson(event.target.value)}
                />
              </FormField>
              <Button type="button" onClick={() => save('integrations')} disabled={isSaving}>
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
              <FormField label="Localization Config" description="GET/PUT /settings/localization">
                <Textarea
                  rows={12}
                  value={localizationJson}
                  onChange={(event) => setLocalizationJson(event.target.value)}
                />
              </FormField>
              <Button type="button" onClick={() => save('localization')} disabled={isSaving}>
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
              <FormField label="Platform Config" description="GET/PUT /settings/platform">
                <Textarea
                  rows={12}
                  value={platformJson}
                  onChange={(event) => setPlatformJson(event.target.value)}
                />
              </FormField>
              <Button type="button" onClick={() => save('platform')} disabled={isSaving}>
                Save Changes
              </Button>
            </Form>
          ),
        },
      ]}
    />
  );
}
