import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { Suspense } from "react";

import { ConsoleShell } from "@/components/console/ConsoleShell";
import "./globals.css";

const sans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "RECLAIM — Revenue Recovery OS",
  description:
    "Post-halt subscription revenue recovery. Synthetic simulation, not production data.",
};

export const dynamic = "force-dynamic";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full bg-paper text-ink">
        <Suspense fallback={<div className="min-h-screen bg-paper" />}>
          <ConsoleShell>{children}</ConsoleShell>
        </Suspense>
      </body>
    </html>
  );
}
