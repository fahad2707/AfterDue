import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next regenerates AGENTS.md / CLAUDE.md on every dev boot; RECLAIM keeps its
  // engineering notes in docs/ instead.
  agentRules: false,
};

export default nextConfig;
