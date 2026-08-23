import { apiGet } from "@/lib/api/http";
import type { PolicyConfig } from "@/types/api";

export function getPolicyConfig() {
  return apiGet<PolicyConfig>("/api/policy/config");
}
