"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { RUN_QUERY, withRun } from "@/lib/run";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/cases", label: "Recovery cases" },
  { href: "/simulate", label: "Simulation" },
  { href: "/model", label: "Model" },
  { href: "/policy", label: "Policy" },
];

export function NavLinks() {
  const pathname = usePathname();
  const params = useSearchParams();
  const runId = params.get(RUN_QUERY);

  return (
    <nav className="mt-10 flex flex-col gap-1" aria-label="Primary">
      {NAV.map((item) => {
        const active =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={withRun(item.href, runId)}
            className={`rounded-sm px-2.5 py-2 text-sm ${
              active
                ? "bg-white/10 text-paper-raised"
                : "text-sand/80 hover:bg-white/5 hover:text-paper-raised"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
