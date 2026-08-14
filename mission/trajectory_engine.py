from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import TrajectoryResult


@runtime_checkable
class TrajectoryEngine(Protocol):
    """Minimal mission-level interface for computing a trajectory transfer.

    This abstraction stays intentionally small: it describes the mission-domain
    operation without coupling callers to PyKEP or to any specific body pair.
    """

    def compute_trajectory(self, *args, **kwargs) -> TrajectoryResult:
        """Compute a transfer result using the engine's own implementation."""
        ...
