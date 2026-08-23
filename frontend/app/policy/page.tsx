import { PolicyInspector } from "@/components/policy/PolicyInspector";
import { ErrorState } from "@/components/ui/StateBlock";
import { apiGet } from "@/lib/server-api";
import type { PolicyConfig } from "@/types/api";

export default async function PolicyPage() {
  const result = await apiGet<PolicyConfig>("/api/policy/config");
  if (!result.ok) {
    return (
      <ErrorState
        title="Policy catalog unavailable"
        body="Backend is currently unavailable. Deterministic rules cannot be loaded."
      />
    );
  }
  return <PolicyInspector config={result.data} />;
}
