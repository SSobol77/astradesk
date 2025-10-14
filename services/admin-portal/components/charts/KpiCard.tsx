import Card from '@/components/primitives/Card';
import Badge from '@/components/primitives/Badge';

export type KpiCardProps = {
  title: string;
  value: string;
  deltaLabel?: string;
  status?: 'healthy' | 'degraded' | 'down';
};

const STATUS_BADGE: Record<NonNullable<KpiCardProps['status']>, { label: string; variant: Parameters<typeof Badge>[0]['variant'] }> = {
  healthy: { label: 'Healthy', variant: 'success' },
  degraded: { label: 'Degraded', variant: 'warn' },
  down: { label: 'Down', variant: 'danger' },
};

export default function KpiCard({ title, value, deltaLabel, status }: KpiCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
          {deltaLabel ? <p className="mt-1 text-xs text-slate-500">{deltaLabel}</p> : null}
        </div>
        {status ? <Badge variant={STATUS_BADGE[status].variant}>{STATUS_BADGE[status].label}</Badge> : null}
      </div>
    </Card>
  );
}
