import Card from '@/components/primitives/Card';
import { Tabs } from '@/components/primitives/Tabs';
import JsonViewer from '@/components/misc/JsonViewer';
import { openApiClient } from '@/openapi/openapi-client';
import type { Flow, FlowDryRunResult, FlowValidation } from '@/openapi/openapi-types';
import { notFound } from 'next/navigation';

async function getFlow(id: string): Promise<Flow | null> {
  try {
    return await openApiClient.flows.get(id);
  } catch (error) {
    console.error('Failed to load flow', error);
    return null;
  }
}

async function getValidation(id: string): Promise<FlowValidation | null> {
  try {
    return await openApiClient.flows.validate(id);
  } catch (error) {
    console.error('Flow validation failed', error);
    return null;
  }
}

async function getDryRun(id: string): Promise<FlowDryRunResult | null> {
  try {
    return await openApiClient.flows.dryRun(id);
  } catch (error) {
    console.error('Flow dry run failed', error);
    return null;
  }
}

async function getLog(id: string): Promise<string[]> {
  try {
    return await openApiClient.flows.log(id);
  } catch (error) {
    console.error('Flow log fetch failed', error);
    return [];
  }
}

type FlowDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function FlowDetailPage({ params }: FlowDetailPageProps) {
  const { id } = await params;

  const [flow, validation, dryRun, log] = await Promise.all([
    getFlow(id),
    getValidation(id),
    getDryRun(id),
    getLog(id),
  ]);

  if (!flow) {
    notFound();
  }

  return (
    <Tabs
      tabs={[
        {
          key: 'yaml',
          label: 'YAML View',
          content: (
            <Card className="bg-slate-900 text-slate-100">
              <pre className="max-h-[500px] overflow-auto text-xs leading-5">
                {flow.yaml}
              </pre>
            </Card>
          ),
        },
        {
          key: 'validation',
          label: 'Validation',
          content: (
            <Card>
              <h3 className="text-base font-semibold text-slate-900">POST /flows/{id}:validate</h3>
              {validation ? (
                <div className="mt-4 text-sm text-slate-700">
                  <p>Status: {validation.valid ? 'Valid' : 'Invalid'}</p>
                  {validation.errors?.length ? (
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {validation.errors.map((err, index) => (
                        <li key={index}>{err}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-500">Run validation to populate results.</p>
              )}
            </Card>
          ),
        },
        {
          key: 'dryrun',
          label: 'Dry Run',
          content: (
            <Card>
              <h3 className="text-base font-semibold text-slate-900">POST /flows/{id}:dryrun</h3>
              {dryRun ? (
                <ul className="mt-4 space-y-3 text-sm text-slate-700">
                  {dryRun.steps.map((step, index) => (
                    <li key={index} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>{step.name}</span>
                        <span className="uppercase">{step.status}</span>
                      </div>
                      {step.output ? (
                        <JsonViewer value={step.output} />
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 text-sm text-slate-500">Execute a dry run to view step outputs.</p>
              )}
            </Card>
          ),
        },
        {
          key: 'log',
          label: 'Log',
          content: (
            <Card>
              <h3 className="text-base font-semibold text-slate-900">GET /flows/{id}/log</h3>
              {log.length ? (
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {log.map((line, index) => (
                    <li key={index} className="font-mono text-xs text-slate-600">
                      {line}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 text-sm text-slate-500">No log entries yet.</p>
              )}
            </Card>
          ),
        },
      ]}
    />
  );
}
