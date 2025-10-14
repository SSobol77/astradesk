import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export const metadata: Metadata = {
  title: 'AstraDesk Admin',
  description: 'Operational control center for AstraDesk platform.',
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-50">
      <body className="min-h-full antialiased text-slate-900">{children}</body>
    </html>
  );
}
