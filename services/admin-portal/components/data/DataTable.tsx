import type { ReactNode } from 'react';
import Card from '@/components/primitives/Card';
import Pagination from './Pagination';

export type TableColumn<T> = {
  key: keyof T | string;
  header: string;
  render?: (item: T) => ReactNode;
};

export type DataTableProps<T> = {
  title?: string;
  description?: string;
  columns: TableColumn<T>[];
  data?: T[];
  emptyState?: ReactNode;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
};

export default function DataTable<T>({
  title,
  description,
  columns,
  data = [],
  emptyState,
  pagination,
}: DataTableProps<T>) {
  return (
    <Card className="p-0">
      <div className="border-b border-slate-200 px-6 py-4">
        {title ? <h2 className="text-base font-semibold text-slate-900">{title}</h2> : null}
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {columns.map((column) => (
                <th key={String(column.key)} className="px-6 py-3 font-semibold">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white text-slate-700">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-6 py-10 text-center text-sm text-slate-500">
                  {emptyState ?? 'No records yet.'}
                </td>
              </tr>
            ) : (
              data.map((item, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-slate-50">
                  {columns.map((column) => (
                    <td key={String(column.key)} className="px-6 py-3">
                      {column.render ? column.render(item) : (item as Record<string, ReactNode>)[column.key as string]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {pagination ? (
        <div className="border-t border-slate-200 px-6 py-4">
          <Pagination {...pagination} />
        </div>
      ) : null}
    </Card>
  );
}
