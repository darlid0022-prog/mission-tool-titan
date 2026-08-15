from __future__ import annotations

from .leg_solver import compute_lambert_leg
from .models import TrajectoryResult
from .trajectory_engine import TrajectoryEngine


class PyKEPTrajectoryEngine:
    """Minimal backend that delegates to the existing Lambert solver."""

    def compute_trajectory(
        self,
        origin: str,
        destination: str,
        launch_start,
        launch_end,
        *,
        n_departures: int = 12,
        tof_min_years: float = 4.0,
        tof_max_years: float = 8.0,
        tof_step_days: float = 15.0,
    ) -> list[TrajectoryResult]:
        """Delegate to the already implemented Lambert leg solver without re-implementing it."""
        return compute_lambert_leg(
            origin,
            destination,
            launch_start,
            launch_end,
            n_departures=n_departures,
            tof_min_years=tof_min_years,
            tof_max_years=tof_max_years,
            tof_step_days=tof_step_days,
        )


def _implements_interface(obj: object) -> bool:
    return isinstance(obj, TrajectoryEngine)
