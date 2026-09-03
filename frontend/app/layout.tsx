import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";

import { ConsoleShell } from "@/components/console/ConsoleShell";
import "./globals.css";

const sans = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AfterDue — Post-halt revenue intelligence",
  description:
    "Post-halt subscription revenue intelligence. Synthetic prototype for Razorpay AI Buildathon Track 03. Not an official Razorpay product.",
};

export const dynamic = "force-dynamic";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sans.variable} h-full antialiased`}>
      <body className={`${sans.className} min-h-full bg-paper text-ink`}>
        <Suspense fallback={<div className="min-h-screen bg-paper" />}>
          <ConsoleShell>{children}</ConsoleShell>
        </Suspense>
      </body>
    </html>
  );
}
