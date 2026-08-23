"""Synthetic financial environment (M3).

Import concrete submodules directly. This package init must stay thin so
`app.models.simulation` can import `SimulationConfig` without pulling the
runner (which imports `SimulationRun` back).
"""

from app.simulator.config import SimulationConfig

__all__ = ["SimulationConfig"]
