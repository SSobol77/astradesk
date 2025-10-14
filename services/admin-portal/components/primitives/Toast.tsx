'use client';

import clsx from 'clsx';
import { useToast } from '@/hooks/useToast';

const VARIANT_STYLES = {
  info: 'border-slate-200 bg-white text-slate-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warn: 'border-amber-200 bg-amber-50 text-amber-700',
  error: 'border-rose-200 bg-rose-50 text-rose-700',
} as const;

export default function ToastViewport() {
  const { toasts, dismiss } = useToast();

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={clsx(
            'pointer-events-auto w-80 rounded-xl border px-4 py-3 text-sm shadow-xl',
            VARIANT_STYLES[toast.variant ?? 'info'],
          )}
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold">{toast.title}</p>
              {toast.description ? <p className="mt-1 text-xs text-inherit">{toast.description}</p> : null}
            </div>
            <button
              type="button"
              className="text-xs font-medium text-slate-500 transition hover:text-slate-900"
              onClick={() => dismiss(toast.id)}
            >
              Close
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
