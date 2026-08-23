"""Simulated executor. Uses the M3 oracle. No real money movement."""

from app.domain.enums import ActionType
from app.simulator.oracle import OracleCase, OracleOutcome, OutcomeOracle


class SimulatedExecutor:
    def execute(self, oracle_case: OracleCase, action: ActionType, run_seed: int) -> OracleOutcome:
        return OutcomeOracle(run_seed).decide(oracle_case, action)
