import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

type BadgeVariant = 'success' | 'warn' | 'danger' | 'neutral';

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
};

const styles: Record<BadgeVariant, string> = {
  success: 'bg-emerald-100 text-emerald-700',
  warn: 'bg-amber-100 text-amber-700',
  danger: 'bg-rose-100 text-rose-700',
  neutral: 'bg-slate-100 text-slate-700',
};

export default function Badge({ variant = 'neutral', className, ...rest }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium',
        styles[variant],
        className,
      )}
      {...rest}
    />
  );
}
