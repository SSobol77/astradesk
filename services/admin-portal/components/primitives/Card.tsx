import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

type CardProps = HTMLAttributes<HTMLDivElement>;

export default function Card({ className, ...rest }: CardProps) {
  return <div className={clsx('rounded-xl border border-slate-200 bg-white p-6 shadow-sm', className)} {...rest} />;
}
