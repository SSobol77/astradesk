// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/app/(shell)/layout.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/app/(shell)/layout.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

import type { ReactNode } from 'react';
import Footer from '@/components/layout/Footer';
import Sidebar from '@/components/layout/Sidebar';
import Topbar from '@/components/layout/Topbar';
import ToastViewport from '@/components/primitives/Toast';
import { ToastProvider } from '@/hooks/useToast';
import { CommandPaletteProvider } from '@/components/search/CommandPalette';

export default function ShellLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ToastProvider>
      <CommandPaletteProvider>
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
      </CommandPaletteProvider>
    </ToastProvider>
  );
}
