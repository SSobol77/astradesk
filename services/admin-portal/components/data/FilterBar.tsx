'use client';

import { useState } from 'react';
import Button from '@/components/primitives/Button';
import { Input, Select } from '@/components/primitives/Form';

export type FilterType = 'text' | 'select' | 'date';

export type FilterConfig = {
  key: string;
  label: string;
  type?: FilterType;
  placeholder?: string;
  options?: { label: string; value: string }[];
};

type FilterBarProps = {
  filters: FilterConfig[];
  onChange?: (values: Record<string, string>) => void;
  initialValues?: Record<string, string>;
};

export default function FilterBar({ filters, onChange, initialValues }: FilterBarProps) {
  const [values, setValues] = useState<Record<string, string>>(initialValues ?? {});

  if (filters.length === 0) {
    return null;
  }

  const updateValue = (key: string, value: string) => {
    const next = { ...values, [key]: value };
    setValues(next);
    onChange?.(next);
  };

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      {filters.map((filter) => {
        const value = values[filter.key] ?? '';
        if (filter.type === 'select' && filter.options) {
          return (
            <div key={filter.key} className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {filter.label}
              </label>
              <Select
                value={value}
                onChange={(event) => updateValue(filter.key, event.target.value)}
              >
                <option value="">All</option>
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
          );
        }

        const inputType = filter.type === 'date' ? 'date' : 'text';

        return (
          <div key={filter.key} className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {filter.label}
            </label>
            <Input
              type={inputType}
              value={value}
              placeholder={filter.placeholder}
              onChange={(event) => updateValue(filter.key, event.target.value)}
            />
          </div>
        );
      })}
      <Button
        type="button"
        variant="ghost"
        onClick={() => {
          setValues({});
          onChange?.({});
        }}
      >
        Clear
      </Button>
    </div>
  );
}
