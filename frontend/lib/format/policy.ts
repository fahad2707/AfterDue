export type ProvenanceKey =
  | "DOCUMENTED_PLATFORM_BEHAVIOR"
  | "PRODUCT_DESIGN_ASSUMPTION"
  | "SAFETY_GUARDRAIL"
  | string;

export function provenanceLabel(value: ProvenanceKey): string {
  switch (value) {
    case "DOCUMENTED_PLATFORM_BEHAVIOR":
      return "Documented platform behavior";
    case "PRODUCT_DESIGN_ASSUMPTION":
      return "Prototype policy assumption";
    case "SAFETY_GUARDRAIL":
      return "Safety guardrail";
    default:
      return value.replaceAll("_", " ").toLowerCase();
  }
}

export function actionLabel(action: string): string {
  return action.replaceAll("_", " ");
}

export function policyStatusLabel(status: string): string {
  switch (status) {
    case "eligible":
      return "Eligible";
    case "restricted":
      return "Restricted";
    case "escalation_required":
      return "Escalation required";
    case "stopped":
      return "Stopped";
    case "review_required":
      return "Review required";
    default:
      return status;
  }
}

export function strategyLabel(name: string): string {
  if (name === "naive") return "Naive";
  if (name === "rule_based") return "Rule-based";
  if (name === "reclaim") return "RECLAIM";
  return name;
}
