import type { ReactNode } from 'react';
import Footer from '@/components/layout/Footer';
import Sidebar from '@/components/layout/Sidebar';
import Topbar from '@/components/layout/Topbar';
import ToastViewport from '@/components/primitives/Toast';
import { ToastProvider } from '@/hooks/useToast';

export default function ShellLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ToastProvider>
      <div className="flex min-h-screen bg-slate-100">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto p-6" aria-label="Main content">
            {children}
          </main>
          <Footer />
        </div>
        <ToastViewport />
      </div>
    </ToastProvider>
  );
}
