export const GUIDE_STORAGE_KEY = "afterdue_guide_seen";
export const GUIDE_QUERY = "guide";
export const GUIDE_CHANGE_EVENT = "afterdue-guide-change";

export type GuideStep = {
  id: string;
  title: string;
  body: string;
  href: string;
};

export const GUIDE_STEPS: GuideStep[] = [
  {
    id: "nav-overview",
    title: "Start on Overview",
    body: "This is the five-second read: leftover unpaid revenue, what is collectible, what needs review, and what was recovered.",
    href: "/",
  },
  {
    id: "overview-metrics",
    title: "Unpaid is not collectible",
    body: "Historical unpaid invoices can still exist after halt. Only the collectible amount enters recovery. Review-required money is not treated as recoverable.",
    href: "/",
  },
  {
    id: "nav-cases",
    title: "Open Recovery cases",
    body: "This queue is leftover post-halt debt. Click Recovery cases, then click any row — the whole line opens the case, not just the customer name.",
    href: "/cases",
  },
  {
    id: "case-table",
    title: "Click anywhere on a row",
    body: "Hover a case and the full row highlights. Click it to see why the case exists, what is collectible, what policy allows, and what AfterDue recommends.",
    href: "/cases",
  },
  {
    id: "nav-simulate",
    title: "Simulation is not live money",
    body: "Generate a synthetic world and run Naive, Rule-based, and AfterDue. Execution here is simulated. No real payment is attempted.",
    href: "/simulate",
  },
  {
    id: "nav-evaluation",
    title: "Evaluation stays honest",
    body: "Compare strategies on the same synthetic world. Ties and losses are reported as-is. AfterDue is not retuned to look better.",
    href: "/evaluation",
  },
  {
    id: "nav-model",
    title: "Model estimates, then diagnostics",
    body: "Business estimates come first: without intervention, with intervention, lift, and expected incremental recovery. Brier and AUC sit underneath.",
    href: "/model",
  },
  {
    id: "nav-policy",
    title: "Policy explains every block",
    body: "If manual charge is blocked, the reason and provenance are here — documented platform behavior, product design assumption, or safety guardrail.",
    href: "/policy",
  },
];

function emitGuideChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(GUIDE_CHANGE_EVENT));
}

export function subscribeGuide(onStoreChange: () => void): () => void {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(GUIDE_CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(GUIDE_CHANGE_EVENT, onStoreChange);
  };
}

export function guideSeen(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage.getItem(GUIDE_STORAGE_KEY) === "true";
  } catch {
    return true;
  }
}

export function markGuideSeen(): void {
  try {
    window.localStorage.setItem(GUIDE_STORAGE_KEY, "true");
  } catch {
    /* ignore */
  }
  emitGuideChange();
}

export function clearGuideSeen(): void {
  try {
    window.localStorage.removeItem(GUIDE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
  emitGuideChange();
}
