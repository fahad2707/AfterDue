import { SimulateConsole } from "@/components/simulate/SimulateConsole";

export default async function SimulatePage({
  searchParams,
}: {
  searchParams: Promise<{ run?: string }>;
}) {
  const { run } = await searchParams;
  return <SimulateConsole initialRunId={run ?? null} />;
}
