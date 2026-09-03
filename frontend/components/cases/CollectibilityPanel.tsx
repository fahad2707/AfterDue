"use client";

import { useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { collectibilityTone, StatusBadge } from "@/components/ui/Badge";
import { formatPaiseINR } from "@/lib/format/money";
import type { Invoice, RecoveryCase } from "@/types/api";

function reasonLabel(codes: string[] | undefined): string {
  if (!codes || codes.length === 0) return "—";
  return codes.join(", ").replaceAll("_", " ").toLowerCase();
}

function serviceLabel(value: string | undefined): string {
  return (value ?? "unknown").replaceAll("_", " ");
}

export function CollectibilityPanel({
  caseRow,
  invoices,
}: {
  caseRow: RecoveryCase;
  invoices: Invoice[];
}) {
  const historical = caseRow.historical_unpaid_amount_paise ?? caseRow.backlog_amount_paise;
  const collectible = caseRow.collectible_amount_paise ?? caseRow.backlog_amount_paise;
  const excluded = caseRow.not_collectible_amount_paise ?? 0;
  const review = caseRow.review_required_amount_paise ?? 0;
  const rows = [...invoices].sort(
    (a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime(),
  );
  const delivered = invoices.filter((i) => i.service_delivery_status === "delivered").length;
  const suspended = invoices.filter((i) => i.service_delivery_status === "suspended").length;
  const unknown = invoices.filter(
    (i) => i.service_delivery_status === "unknown" || i.service_delivery_status === "partially_delivered",
  ).length;
  const bits: string[] = [];
  if (delivered) {
    bits.push(
      `${delivered} billing period${delivered === 1 ? "" : "s"} had confirmed service delivery.`,
    );
  }
  if (suspended) {
    bits.push(
      `${suspended} billing period${suspended === 1 ? "" : "s"} had service suspended.`,
    );
  }
  if (unknown) {
    bits.push(
      `${unknown} billing period${unknown === 1 ? "" : "s"} need merchant review.`,
    );
  }

  const reduce = useReducedMotion();
  const complete = rows.length + 2;
  const [step, setStep] = useState(-1);
  const [started, setStarted] = useState(false);
  const [replayed, setReplayed] = useState(false);
  const rootRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const key = `afterdue_classify_${caseRow.case_id}`;
    const node = rootRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        let played = false;
        try {
          played = sessionStorage.getItem(key) === "1";
        } catch {
          played = true;
        }
        if (played) {
          setReplayed(true);
          return;
        }
        try {
          sessionStorage.setItem(key, "1");
        } catch {
          /* ignore quota / private mode */
        }
        setStarted(true);
        setStep(0);
      },
      { threshold: 0.22 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [caseRow.case_id]);

  useEffect(() => {
    if (!started || step < 0 || step >= complete) return;
    const timer = window.setTimeout(() => setStep((current) => current + 1), 140);
    return () => window.clearTimeout(timer);
  }, [complete, started, step]);

  const displayStep = reduce || replayed ? complete : step;
  const showHistorical = displayStep >= 0;
  const showTotals = displayStep >= complete;

  return (
    <section ref={rootRef} data-testid="collectibility-panel">
      <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        What is collectible
      </h3>
      <div className="rounded-md border border-line bg-paper-raised px-4 py-5">
        <div className="grid items-end gap-3 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
          <div
            className={`rounded-md border border-line px-4 py-4 ${
              showHistorical ? "ad-resolve" : "opacity-40"
            }`}
          >
            <p className="figure text-3xl font-medium tracking-tight">
              {formatPaiseINR(historical)}
            </p>
            <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
              Historical unpaid
            </p>
          </div>
          <p
            className="hidden pb-6 text-center text-xs uppercase tracking-[0.16em] text-ink-soft lg:block"
            aria-hidden="true"
          >
            {showTotals ? "→" : "·"}
          </p>
          <div
            className={`rounded-md border border-good/25 bg-good-soft/70 px-4 py-4 ${
              showTotals ? "ad-resolve" : "opacity-40"
            }`}
          >
            <p className="figure text-3xl font-medium tracking-tight text-good">
              {formatPaiseINR(collectible)}
            </p>
            <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
              Collectible
            </p>
            <p className="mt-1 text-xs text-ink-soft">Enters optimization</p>
          </div>
        </div>

        {rows.length > 0 ? (
          <ul className="mt-5 space-y-2">
            {rows.map((invoice, index) => {
              const visible = displayStep >= index + 1;
              const tone = collectibilityTone(invoice.collectibility_status);
              return (
                <li
                  key={invoice.invoice_id}
                  className={`flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 rounded-md border px-3 py-2.5 ${
                    visible ? "ad-stagger border-line bg-surface-elevated" : "border-transparent opacity-30"
                  }`}
                >
                  <p className="figure text-lg font-medium">
                    {formatPaiseINR(invoice.amount_paise)}
                  </p>
                  <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                    {invoice.billing_cycle} · {serviceLabel(invoice.service_delivery_status)}
                  </p>
                  <StatusBadge tone={visible ? tone : "neutral"}>
                    {visible
                      ? serviceLabel(invoice.collectibility_status)
                      : "Classifying"}
                  </StatusBadge>
                </li>
              );
            })}
          </ul>
        ) : null}

        <dl
          className={`mt-5 grid gap-3 sm:grid-cols-2 ${
            showTotals ? "ad-resolve" : "opacity-40"
          }`}
        >
          <div className="rounded-md border border-attention/20 bg-amber-soft/50 px-3 py-3">
            <dd className="figure text-xl font-medium">{formatPaiseINR(review)}</dd>
            <dt className="mt-1 text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Review required
            </dt>
            <dd className="mt-1">
              <StatusBadge tone="attention">Not collectible yet</StatusBadge>
            </dd>
          </div>
          <div className="rounded-md border border-line bg-excluded-soft px-3 py-3">
            <dd className="figure text-xl font-medium text-excluded">
              {formatPaiseINR(excluded)}
            </dd>
            <dt className="mt-1 text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Excluded
            </dt>
            <dd className="mt-1">
              <StatusBadge tone="excluded">Not a receivable</StatusBadge>
            </dd>
          </div>
        </dl>

        <p className="mt-4 text-sm leading-6 text-ink-soft">
          {bits.join(" ") ||
            reasonLabel(invoices.flatMap((invoice) => invoice.collectibility_reason_codes ?? []))}
        </p>
        <p className="mt-2 text-sm leading-6 text-ink">
          Invoice existence is not collectibility. {formatPaiseINR(historical)} historical
          unpaid resolves to {formatPaiseINR(collectible)} collectible. Review-required and
          excluded amounts never enter optimization.
        </p>
      </div>
    </section>
  );
}
