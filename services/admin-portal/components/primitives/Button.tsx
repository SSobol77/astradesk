'use client';

import clsx from 'clsx';
import type { ButtonHTMLAttributes, DetailedHTMLProps } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

type ButtonProps = DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const styles: Record<ButtonVariant, string> = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-500 focus-visible:ring-indigo-500',
  secondary: 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100 focus-visible:ring-indigo-500',
  ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 focus-visible:ring-indigo-500',
  danger: 'bg-rose-600 text-white hover:bg-rose-500 focus-visible:ring-rose-500',
};

export default function Button({
  variant = 'primary',
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        styles[variant],
        className,
      )}
      {...rest}
    />
  );
}
