'use client';

import type { FormHTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

export function Form({ className, ...rest }: FormHTMLAttributes<HTMLFormElement>) {
  return <form className={clsx('space-y-6', className)} {...rest} />;
}

export function FormField({
  label,
  description,
  children,
  error,
}: {
  label: string;
  description?: string;
  children: ReactNode;
  error?: string;
}) {
  return (
    <div className="space-y-2">
      <div>
        <label className="text-sm font-medium text-slate-700">{label}</label>
        {description ? <p className="text-xs text-slate-500">{description}</p> : null}
      </div>
      {children}
      {error ? <p className="text-xs text-rose-600">{error}</p> : null}
    </div>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500"
      {...props}
    />
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500"
      {...props}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500"
      {...props}
    />
  );
}
