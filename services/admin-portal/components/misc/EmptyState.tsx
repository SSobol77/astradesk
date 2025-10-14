import Card from '@/components/primitives/Card';
import Button from '@/components/primitives/Button';

export type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export default function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <Card className="flex flex-col items-center justify-center text-center">
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-600">{description}</p>
      {actionLabel ? (
        <Button className="mt-4" onClick={onAction}
        >
          {actionLabel}
        </Button>
      ) : null}
    </Card>
  );
}
