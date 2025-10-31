import KpiCard from '@/components/charts/KpiCard';
import Card from '@/components/primitives/Card';
import { formatCurrency, formatLatency, formatNumber } from '@/lib/format';
import { openApiClient } from '@/api/client';
import type { HealthStatus, UsageMetrics, RecentError } from '@/api/types';
import Link from 'next/link';

async function getUsage(): Promise<UsageMetrics | null> {
  try {
    return await openApiClient.dashboard.getUsage();
  } catch (error) {
    console.error('Failed to load usage metrics', error);
    return null;
  }
}

async function getHealth(): Promise<HealthStatus | null> {
  try {
    return await openApiClient.dashboard.getHealth();
  } catch (error) {
    console.error('Failed to load health status', error);
    return null;
  }
}

async function getRecentErrors(limit: number): Promise<RecentError[]> {
  try {
    return await openApiClient.dashboard.getRecentErrors({ limit });
  } catch (error) {
    console.error('Failed to load recent errors', error);
    return [];
  }
}

export default async function DashboardPage() {
  const [usage, health, errors] = await Promise.all([getUsage(), getHealth(), getRecentErrors(10)]);

  const totalRequests = formatNumber(usage?.total_requests ?? 0);
  const totalCost = formatCurrency(usage?.cost_usd ?? 0);
  const p95Latency = formatLatency(usage?.latency_p95_ms ?? 0);
  const healthEntries = health ? Object.entries(health.components ?? {}) : [];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-3">
        <KpiCard title="Total Requests" value={totalRequests} />
        <KpiCard title="LLM Cost (USD)" value={totalCost} />
        <KpiCard title="P95 Latency (ms)" value={p95Latency} />
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900">System Health</h2>
              <p className="text-sm text-slate-500">Derived from GET /health</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {healthEntries.length ? (
              <ul className="divide-y divide-slate-200 text-sm text-slate-700">
                {healthEntries.map(([componentName, componentStatus]) => (
                  <li key={componentName} className="flex items-center justify-between py-2">
                    <span>{componentName}</span>
                    <span className="capitalize text-slate-500">{componentStatus}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No component data yet.</p>
            )}
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Recent Errors</h2>
              <p className="text-sm text-slate-500">GET /errors/recent?limit=10</p>
            </div>
            <Link
              href="/runs"
              className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
            >
              View Runs
            </Link>
          </div>
          <div className="mt-4 space-y-2">
            {errors.length ? (
              <ul className="space-y-2 text-sm text-rose-600">
                {errors.map((errorItem) => (
                  <li key={`${errorItem.trace_id}-${errorItem.timestamp}`} className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2">
                    <span className="block text-xs text-rose-400">{new Date(errorItem.timestamp).toLocaleString()}</span>
                    <span>{errorItem.message}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No errors reported.</p>
            )}
          </div>
        </Card>
      </section>
    </div>
  );
}
