// services/admin-portal/app/layout.tsx

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css"; // Importujemy globalne style

const inter = Inter({ subsets: ["latin"] });

// Definiujemy metadane dla całej aplikacji (np. tytuł w zakładce przeglądarki)
export const metadata: Metadata = {
  title: "AstraDesk Admin Portal",
  description: "Administration and monitoring panel for AstraDesk AI agents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* Tutaj Next.js "wstrzyknie" zawartość Twojej strony (page.tsx) */}
        {children}
      </body>
    </html>
  );
}
