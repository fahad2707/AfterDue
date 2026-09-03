"use client";

import { useState } from "react";

import { apiGet, apiPost } from "@/lib/api/http";
import { formatLiftPp, formatPaiseINR } from "@/lib/format/money";
import { actionLabel } from "@/lib/format/policy";
import type { ModelAnalysis, RecoveryCaseDetail } from "@/types/api";

type Explanation = {
  summary: string;
  why_case_exists: string;
  recommended_action_explanation: string;
  policy_constraints: string[];
  economic_reasoning: string;
  uncertainty_note: string;
  synthetic_disclaimer: string;
};

type PlanResponse = {
  recommended_action: string;
  expected_incremental_recovery_paise: number;
  estimated_uplift: number;
  deterministic_explanation: Explanation;
  llm_explanation: Explanation | null;
  explanation_source: string;
  model_analysis: ModelAnalysis | null;
  synthetic: boolean;
};

type ExecuteResponse = {
  agent_run_id: string;
  status: string;
  stop_reason: string | null;
  recommended_action: string;
  validated_action: string | null;
  attempt_number: number;
  trace: Array<{ event_type: string; stop_reason?: string; details?: Record<string, unknown> }>;
  action: {
    outcome: string | null;
    amount_recovered_paise: number;
    status: string;
  } | null;
  simulated: boolean;
};

type AskResponse = {
  answer: string;
  source: string;
  grounding: string[];
  insufficient_information: boolean;
};

const CHIPS = [
  "Why was this case created?",
  "Why was this action selected?",
  "What blocked manual charge?",
  "How was expected incremental recovery calculated?",
];

const TRACE_STEPS: Array<{ event: string; label: string }> = [
  { event: "POLICY_EVALUATED", label: "Policy checked" },
  { event: "MODEL_ANALYZED", label: "Model analyzed" },
  { event: "ACTION_PROPOSED", label: "Action proposed" },
  { event: "ACTION_VALIDATION_STARTED", label: "Validator started" },
  { event: "POLICY_REVALIDATED", label: "Policy revalidated" },
  { event: "ACTION_VALIDATED", label: "Action validated" },
  { event: "ACTION_BLOCKED", label: "Action blocked" },
  { event: "ACTION_EXECUTED", label: "Action executed (simulated)" },
  { event: "OUTCOME_OBSERVED", label: "Outcome observed" },
  { event: "CASE_CLOSED", label: "Case closed" },
  { event: "AGENT_STOPPED", label: "Stopped" },
  { event: "AGENT_ESCALATED", label: "Escalated" },
];

export function AgentWorkbench({
  detail,
}: {
  detail: RecoveryCaseDetail;
}) {
  const analysis = detail.model_analysis ?? detail.case.model_analysis;
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [llm, setLlm] = useState<Explanation | null>(null);
  const [llmSource, setLlmSource] = useState<string | null>(null);
  const [execution, setExecution] = useState<ExecuteResponse | null>(null);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recommended = plan?.recommended_action ?? analysis?.selected_action;
  const ev = plan?.expected_incremental_recovery_paise ?? analysis?.expected_incremental_recovery_paise;
  const lift = plan?.estimated_uplift ?? analysis?.estimated_uplift;
  const why = llm ?? plan?.deterministic_explanation;

  async function loadPlan() {
    setBusy("plan");
    setError(null);
    try {
      const data = await apiPost<PlanResponse>(
        `/api/agent/cases/${encodeURIComponent(detail.case.case_id)}/plan`,
        { prefer_llm: false },
      );
      setPlan(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plan failed.");
    } finally {
      setBusy(null);
    }
  }

  async function generateLlm() {
    setBusy("llm");
    setError(null);
    try {
      const data = await apiGet<{ explanation: Explanation; source: string }>(
        `/api/recovery-cases/${encodeURIComponent(detail.case.case_id)}/explanation?mode=llm`,
      );
      setLlm(data.explanation);
      setLlmSource(data.source);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explanation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function execute() {
    setBusy("execute");
    setError(null);
    try {
      if (!plan) await loadPlan();
      const data = await apiPost<ExecuteResponse>(
        `/api/agent/cases/${encodeURIComponent(detail.case.case_id)}/execute`,
        { prefer_llm: false },
      );
      setExecution(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Execution failed.");
    } finally {
      setBusy(null);
    }
  }

  async function ask(question: string) {
    setBusy("ask");
    setError(null);
    try {
      const data = await apiPost<AskResponse>(
        `/api/recovery-cases/${encodeURIComponent(detail.case.case_id)}/ask`,
        { question, prefer_llm: false },
      );
      setAnswer(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-line bg-paper-raised p-5">
        <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          What AfterDue recommends
        </h3>
        <p className="mt-3 text-lg font-medium capitalize">
          {recommended ? actionLabel(recommended) : "Plan to see the recommended action"}
        </p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Expected incremental recovery
            </dt>
            <dd className="mt-1 font-mono text-xl tabular">
              {ev == null ? "—" : formatPaiseINR(ev)}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Estimated intervention lift
            </dt>
            <dd className="mt-1 font-mono text-xl tabular">
              {lift == null ? "—" : formatLiftPp(lift)}
            </dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadPlan()}
            disabled={busy !== null}
            className="rounded-sm bg-ink px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-paper-raised disabled:opacity-60"
          >
            {busy === "plan" ? "Planning…" : "Plan (no execution)"}
          </button>
        </div>
      </section>

      <section className="rounded-md border border-line bg-sand/40 p-5">
        <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Why this action?
        </h3>
        {why ? (
          <div className="mt-3 space-y-3 text-sm leading-6">
            <p>{why.recommended_action_explanation}</p>
            <p>{why.economic_reasoning}</p>
            {why.policy_constraints.map((line) => (
              <p key={line}>{line}</p>
            ))}
            <p className="text-ink-soft">{why.uncertainty_note}</p>
            <p className="font-mono text-[11px] text-ink-soft">
              Source: {llmSource ?? plan?.explanation_source ?? "deterministic"}
            </p>
          </div>
        ) : (
          <p className="mt-3 text-sm text-ink-soft">
            Plan the case to see the deterministic explanation. Claude is not
            called on page load.
          </p>
        )}
        <button
          type="button"
          onClick={() => void generateLlm()}
          disabled={busy !== null}
          className="mt-4 rounded-sm border border-line px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em]"
        >
          {busy === "llm" ? "Generating…" : "Generate AI explanation"}
        </button>
      </section>

      <section className="rounded-md border border-line bg-paper-raised p-5">
        <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          What the agent did · simulated execution
        </h3>
        <p className="mt-2 text-sm font-medium text-forest">
          SIMULATED EXECUTION — NO REAL PAYMENT WILL BE ATTEMPTED
        </p>
        <button
          type="button"
          onClick={() => void execute()}
          disabled={busy !== null}
          className="mt-4 rounded-sm bg-forest px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-paper-raised disabled:opacity-60"
        >
          {busy === "execute" ? "Running…" : "Run simulated recovery"}
        </button>
        {execution ? (
          <div className="mt-5 space-y-3">
            <p className="text-sm">
              Status {execution.status}
              {execution.validated_action
                ? ` · validated ${actionLabel(execution.validated_action)}`
                : ""}
              {execution.stop_reason ? ` · stop ${execution.stop_reason}` : ""}
            </p>
            {execution.action?.outcome ? (
              <p className="font-mono text-sm">
                Outcome {execution.action.outcome}
                {execution.action.amount_recovered_paise
                  ? ` · ${formatPaiseINR(execution.action.amount_recovered_paise)}`
                  : ""}
              </p>
            ) : null}
            <ol className="mt-3 space-y-0">
              <li className="text-sm">Observed case</li>
              {TRACE_STEPS.filter((step) =>
                execution.trace.some((row) => row.event_type === step.event),
              ).map((step) => (
                <li key={step.event} className="text-sm">
                  <span className="block text-ink-soft">↓</span>
                  {step.label}
                  <span className="ml-2 font-mono text-[11px] text-ink-soft">
                    {step.event}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        ) : null}
      </section>

      <section className="rounded-md border border-line p-5">
        <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Ask AfterDue about this decision
        </h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => void ask(chip)}
              disabled={busy !== null}
              className="rounded-sm border border-line px-2.5 py-1.5 text-xs"
            >
              {chip}
            </button>
          ))}
        </div>
        {answer ? (
          <p className="mt-4 text-sm leading-6">
            {answer.answer}
            <span className="mt-2 block font-mono text-[11px] text-ink-soft">
              {answer.source}
            </span>
          </p>
        ) : null}
      </section>

      {error ? <p className="text-sm text-ink-soft">{error}</p> : null}
    </div>
  );
}
