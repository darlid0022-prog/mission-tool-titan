import math
from datetime import date

import pytest

from mission.leg_solver import compute_lambert_leg

LAUNCH_START = date(2026, 6, 1)
LAUNCH_END = date(2027, 6, 1)


@pytest.mark.parametrize(
    ("destination", "tof_min_years", "tof_max_years", "tof_step_days"),
    (
        ("Mercury", 0.2, 0.6, 20.0),
        ("Venus", 0.3, 0.8, 30.0),
        ("Mars", 0.5, 1.2, 30.0),
        ("Jupiter", 1.5, 3.5, 90.0),
        ("Uranus", 5.0, 12.0, 180.0),
        ("Neptune", 8.0, 16.0, 180.0),
    ),
    ids=("mercury", "venus", "mars", "jupiter", "uranus", "neptune"),
)
def test_earth_to_new_planet_lambert_grid_is_non_empty_and_physical(
    destination: str,
    tof_min_years: float,
    tof_max_years: float,
    tof_step_days: float,
) -> None:
    results = compute_lambert_leg(
        "Earth",
        destination,
        LAUNCH_START,
        LAUNCH_END,
        n_departures=3,
        tof_min_years=tof_min_years,
        tof_max_years=tof_max_years,
        tof_step_days=tof_step_days,
    )

    assert results
    for result in results:
        assert result.v_inf_depart is not None
        assert result.v_inf_arrival is not None
        assert result.tof_years is not None
        assert result.departure_mjd2000 is not None
        assert result.arrival_mjd2000 is not None

        assert math.isfinite(result.v_inf_depart)
        assert math.isfinite(result.v_inf_arrival)
        assert result.v_inf_depart >= 0.0
        assert result.v_inf_arrival >= 0.0
        assert result.v_inf_depart < 1_000_000.0
        assert result.v_inf_arrival < 1_000_000.0
        assert result.tof_years > 0.0
        assert result.departure_mjd2000 < result.arrival_mjd2000
