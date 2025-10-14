const dateFormatter = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

export function formatDate(value?: string | null) {
  if (!value) return '—';
  return dateFormatter.format(new Date(value));
}

export function formatCurrency(value?: number | null) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatLatency(value?: number | null) {
  if (typeof value !== 'number') return '—';
  return `${value.toFixed(0)} ms`;
}

export function formatNumber(value?: number | null) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat('en-US').format(value);
}
