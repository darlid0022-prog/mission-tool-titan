"""Delta-v grid for a classic departure-date x arrival-date porkchop plot.

Computation layer only - no plotting/page code here (a separate task adds
the Streamlit visualization). Reuses the existing Lambert-solving primitive
(mission/leg_solver.py's solve_lambert_v_infinities - the same one
compute_lambert_leg uses) and the existing propulsive delta-v formulas
(mission/physics.py's delta_v_injection/delta_v_capture - the same ones
trajectory.py's Earth -> planet engine uses) rather than re-deriving either.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

import pykep as pk

from . import physics
from .bodies import resolve_body
from .leg_solver import solve_lambert_v_infinities

DEFAULT_DEPARTURE_STEP_DAYS = 5.0
DEFAULT_ARRIVAL_STEP_DAYS = 5.0
DEFAULT_LEO_ALTITUDE_M = 250_000.0
DEFAULT_CAPTURE_ALTITUDE_M = 2_000_000.0
SECONDS_PER_DAY = 86_400.0


def _to_mjd2000(value) -> float:
    """Accept a pk.epoch, datetime, date, or a bare MJD2000 number.

    The bare-number case matches how epochs already flow through this
    codebase (e.g. TrajectoryResult.departure_mjd2000), so a caller chaining
    an already-computed epoch straight into a window boundary doesn't need
    to round-trip it through a date first.
    """
    if isinstance(value, bool):
        raise TypeError("Unsupported date type: bool.")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, pk.epoch):
        return value.mjd2000
    if isinstance(value, datetime):
        return pk.epoch(value.strftime("%Y-%m-%d %H:%M:%S")).mjd2000
    if isinstance(value, date):
        return pk.epoch(value.strftime("%Y-%m-%d 00:00:00")).mjd2000
    raise TypeError(
        f"Unsupported date type: {type(value)!r}. Expected a datetime.date/datetime, "
        "pk.epoch, or a bare MJD2000 number."
    )


def _epoch_grid(window_start, window_end, step_days: float) -> list[float]:
    start_mjd2000 = _to_mjd2000(window_start)
    end_mjd2000 = _to_mjd2000(window_end)
    if end_mjd2000 < start_mjd2000:
        raise ValueError("A date window's end must not precede its start.")
    if not math.isfinite(step_days) or step_days <= 0.0:
        raise ValueError("step_days must be a finite, positive number of days.")

    epochs = []
    epoch = start_mjd2000
    # Tolerance guards against the exact end date being dropped by float
    # accumulation error (mirrors compute_lambert_leg's tof_years grid).
    while epoch <= end_mjd2000 + 1e-9:
        epochs.append(epoch)
        epoch += step_days
    return epochs


@dataclass(frozen=True)
class PorkchopGrid:
    """Total propulsive delta-v over an independent departure x arrival date grid.

    `delta_v_grid_m_s[i][j]` is the departure-injection + arrival-capture
    delta-v (m/s) for `departure_epochs_mjd2000[i]` -> `arrival_epochs_mjd2000[j]`,
    or NaN where that pair has no valid transfer (arrival not after departure,
    or the Lambert solver did not converge for that geometry/time-of-flight).
    """

    origin: str
    destination: str
    departure_epochs_mjd2000: tuple[float, ...]
    arrival_epochs_mjd2000: tuple[float, ...]
    delta_v_grid_m_s: tuple[tuple[float, ...], ...]
    leo_altitude_m: float
    capture_altitude_m: float

    def __post_init__(self) -> None:
        if not self.departure_epochs_mjd2000 or not self.arrival_epochs_mjd2000:
            raise ValueError("departure_epochs_mjd2000 and arrival_epochs_mjd2000 must be non-empty.")
        if len(self.delta_v_grid_m_s) != len(self.departure_epochs_mjd2000):
            raise ValueError("delta_v_grid_m_s must have one row per departure epoch.")
        for row in self.delta_v_grid_m_s:
            if len(row) != len(self.arrival_epochs_mjd2000):
                raise ValueError(
                    "Every delta_v_grid_m_s row must have one value per arrival epoch."
                )

    @property
    def valid_cell_count(self) -> int:
        """Number of grid cells with a converged, physically valid transfer."""
        return sum(1 for row in self.delta_v_grid_m_s for value in row if math.isfinite(value))

    @property
    def total_cell_count(self) -> int:
        return len(self.departure_epochs_mjd2000) * len(self.arrival_epochs_mjd2000)


def minimum_delta_v(grid: PorkchopGrid) -> tuple[float, float, float] | None:
    """Return `(delta_v_m_s, departure_mjd2000, arrival_mjd2000)` at the grid's minimum.

    None if every cell is invalid (NaN) - e.g. the two windows never allow a
    departure-before-arrival pair.
    """
    if not isinstance(grid, PorkchopGrid):
        raise TypeError("grid must be a PorkchopGrid.")

    best: tuple[float, float, float] | None = None
    for departure_mjd2000, row in zip(grid.departure_epochs_mjd2000, grid.delta_v_grid_m_s, strict=True):
        for arrival_mjd2000, delta_v in zip(grid.arrival_epochs_mjd2000, row, strict=True):
            if not math.isfinite(delta_v):
                continue
            if best is None or delta_v < best[0]:
                best = (delta_v, departure_mjd2000, arrival_mjd2000)
    return best


def compute_porkchop_grid(
    destination: str,
    departure_window_start,
    departure_window_end,
    arrival_window_start,
    arrival_window_end,
    *,
    origin: str = "Earth",
    departure_step_days: float = DEFAULT_DEPARTURE_STEP_DAYS,
    arrival_step_days: float = DEFAULT_ARRIVAL_STEP_DAYS,
    leo_altitude_m: float = DEFAULT_LEO_ALTITUDE_M,
    capture_altitude_m: float = DEFAULT_CAPTURE_ALTITUDE_M,
) -> PorkchopGrid:
    """Compute the total delta-v (departure injection + arrival capture) grid.

    For every (departure epoch, arrival epoch) pair drawn independently from
    the two stepped date windows, solves one zero-revolution Lambert transfer
    (mission/leg_solver.py's solve_lambert_v_infinities - the same primitive
    compute_lambert_leg's departure x time-of-flight grid uses) and converts
    its v-infinity values to propulsive delta-v with the same
    physics.delta_v_injection/delta_v_capture formulas trajectory.py's
    Earth -> planet engine already uses.

    A pair with arrival not strictly after departure, or for which the
    Lambert solver does not converge (a geometrically impossible or
    degenerate transfer), is marked NaN in the returned grid instead of
    raising or aborting the rest of the grid.

    `departure_window_start`/`_end` and `arrival_window_start`/`_end` each
    accept a `datetime.date`, `datetime.datetime`, or `pykep.epoch`.
    """
    origin_body = resolve_body(origin)
    destination_body = resolve_body(destination)
    if not origin_body.supports_lambert:
        raise NotImplementedError(
            f"Lambert transfer modeling from {origin_body.name} is intentionally not implemented yet."
        )
    if not destination_body.supports_lambert:
        raise NotImplementedError(
            f"Lambert transfer modeling to {destination_body.name} is intentionally not implemented yet."
        )
    if origin_body.pykep_body is None or destination_body.pykep_body is None:
        raise NotImplementedError(
            "Both origin and destination need a PyKEP-backed radius to size the "
            "injection/capture orbit."
        )

    departure_epochs = _epoch_grid(departure_window_start, departure_window_end, departure_step_days)
    arrival_epochs = _epoch_grid(arrival_window_start, arrival_window_end, arrival_step_days)

    mu_origin = origin_body.get_mu_self()
    mu_destination = destination_body.get_mu_self()
    mu_central_body = origin_body.get_mu_central_body()
    r_leo = origin_body.pykep_body.get_radius() + float(leo_altitude_m)
    r_capture = destination_body.pykep_body.get_radius() + float(capture_altitude_m)

    # Destination ephemeris only depends on the arrival epoch: sample each
    # arrival column once and reuse it across every departure row, instead of
    # one PyKEP ephemeris call per grid cell.
    destination_states = {
        arrival_mjd2000: destination_body.eph(arrival_mjd2000) for arrival_mjd2000 in arrival_epochs
    }

    grid: list[tuple[float, ...]] = []
    for departure_mjd2000 in departure_epochs:
        r0, v_origin = origin_body.eph(departure_mjd2000)
        row: list[float] = []
        for arrival_mjd2000 in arrival_epochs:
            tof_seconds = (arrival_mjd2000 - departure_mjd2000) * SECONDS_PER_DAY
            if tof_seconds <= 0.0:
                row.append(float("nan"))
                continue

            r1, v_destination = destination_states[arrival_mjd2000]
            solved = solve_lambert_v_infinities(
                r0, r1, tof_seconds, mu_central_body, v_origin, v_destination
            )
            if solved is None:
                row.append(float("nan"))
                continue

            v_inf_depart, v_inf_arrival = solved
            departure_delta_v = physics.delta_v_injection(v_inf_depart, mu_origin, r_leo)
            arrival_delta_v = physics.delta_v_capture(v_inf_arrival, mu_destination, r_capture)
            row.append(departure_delta_v + arrival_delta_v)
        grid.append(tuple(row))

    return PorkchopGrid(
        origin=origin_body.name,
        destination=destination_body.name,
        departure_epochs_mjd2000=tuple(departure_epochs),
        arrival_epochs_mjd2000=tuple(arrival_epochs),
        delta_v_grid_m_s=tuple(grid),
        leo_altitude_m=float(leo_altitude_m),
        capture_altitude_m=float(capture_altitude_m),
    )
