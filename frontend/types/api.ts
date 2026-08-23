export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  app_env: string;
  uptime_seconds: number;
};

export type DependencyStatus = {
  ok: boolean;
  detail: string | null;
};

export type ReadyResponse = {
  ready: boolean;
  checks: Record<string, DependencyStatus>;
};

export type MetaResponse = {
  service: string;
  app_env: string;
  policy_version: string;
  llm_enabled: boolean;
  synthetic: boolean;
};
