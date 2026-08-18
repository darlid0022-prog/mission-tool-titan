import unittest

from mission.full_mission import (
    EarthSaturnTitanMissionResult,
    compute_earth_saturn_titan_mission,
)
from mission.models import Leg, TrajectoryResult

EARTH_ARRIVAL_EPOCH = 12_537.181818181829
SATURN_ARRIVAL_V_INFINITY_M_S = 6_490.744714263188
SATURN_PERIAPSIS_RADIUS_M = 62_330_000.0
PERIAPSIS_PROVENANCE = "PyKEP Saturn radius 60,330 km + capture altitude 2,000 km"


def earth_saturn_leg() -> Leg:
    return Leg(
        origin="Earth",
        destination="Saturn",
        trajectory=TrajectoryResult(
            departure_mjd2000=10_345.0,
            arrival_mjd2000=EARTH_ARRIVAL_EPOCH,
            tof_years=6.0,
            v_inf_depart=10_432.306468285773,
            v_inf_arrival=SATURN_ARRIVAL_V_INFINITY_M_S,
            method="lambert",
        ),
    )


class TestEarthSaturnTitanMission(unittest.TestCase):
    def test_one_call_returns_full_mission_and_two_separate_studies(self):
        result = compute_earth_saturn_titan_mission(
            earth_saturn_leg(),
            saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
            saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
        )

        self.assertIsInstance(result, EarthSaturnTitanMissionResult)
        self.assertEqual(result.mission.name, "Earth -> Saturn -> Titan")
        self.assertEqual(
            [(leg.origin, leg.destination) for leg in result.mission.legs],
            [("Earth", "Saturn"), ("Saturn", "Saturn"), ("Saturn", "Titan")],
        )
        self.assertEqual(result.saturn_arrival_staging.origin_state, "Saturn hyperbolic arrival")
        self.assertEqual(result.saturn_titan_transfer.destination, "Titan")
        self.assertEqual(
            result.connected_first_order.saturn_hyperbola.specific_energy_j_kg,
            SATURN_ARRIVAL_V_INFINITY_M_S**2 / 2.0,
        )
        self.assertEqual(
            result.connected_first_order.saturn_capture.periapsis_radius_m,
            150_000_000.0,
        )
        self.assertEqual(
            result.connected_first_order.saturn_capture.apoapsis_radius_m,
            1_221_870_000.0,
        )

    def test_phases_share_arrival_speed_staging_radius_and_epochs(self):
        source_leg = earth_saturn_leg()
        result = compute_earth_saturn_titan_mission(
            source_leg,
            saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
            saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
        )
        earth_leg, staging_leg, titan_leg = result.mission.legs
        assert earth_leg.trajectory is not None
        assert staging_leg.trajectory is not None
        assert titan_leg.trajectory is not None

        self.assertIs(earth_leg, source_leg)
        self.assertEqual(
            result.saturn_arrival_staging.arrival_v_infinity_m_s,
            earth_leg.trajectory.v_inf_arrival,
        )
        self.assertEqual(
            result.saturn_arrival_staging.staging_radius_m,
            result.saturn_titan_transfer.saturn_staging_radius_m,
        )
        self.assertEqual(staging_leg.trajectory.departure_mjd2000, EARTH_ARRIVAL_EPOCH)
        self.assertEqual(
            titan_leg.trajectory.departure_mjd2000,
            staging_leg.trajectory.arrival_mjd2000,
        )

    def test_adapted_delta_v_and_titan_v_infinity_remain_distinct(self):
        result = compute_earth_saturn_titan_mission(
            earth_saturn_leg(),
            saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
            saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
        )
        staging_trajectory = result.mission.legs[1].trajectory
        titan_trajectory = result.mission.legs[2].trajectory
        assert staging_trajectory is not None
        assert titan_trajectory is not None

        self.assertEqual(
            staging_trajectory.delta_v,
            result.saturn_arrival_staging.total_delta_v_m_s,
        )
        self.assertEqual(titan_trajectory.delta_v, result.saturn_titan_transfer.total_delta_v_m_s)
        self.assertEqual(
            titan_trajectory.v_inf_arrival,
            result.saturn_titan_transfer.v_infinity_titan_m_s,
        )
        self.assertNotEqual(titan_trajectory.delta_v, titan_trajectory.v_inf_arrival)

    def test_unknown_epochs_remain_unknown_without_breaking_leg_order(self):
        leg = earth_saturn_leg()
        assert leg.trajectory is not None
        leg.trajectory.arrival_mjd2000 = None

        result = compute_earth_saturn_titan_mission(
            leg,
            saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
            saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
        )

        for phase in result.mission.legs[1:]:
            assert phase.trajectory is not None
            self.assertIsNone(phase.trajectory.departure_mjd2000)
            self.assertIsNone(phase.trajectory.arrival_mjd2000)

    def test_rejects_earth_saturn_arrival_before_departure(self):
        leg = earth_saturn_leg()
        assert leg.trajectory is not None
        leg.trajectory.arrival_mjd2000 = leg.trajectory.departure_mjd2000 - 1.0

        with self.assertRaisesRegex(ValueError, "arrival epoch must not precede"):
            compute_earth_saturn_titan_mission(
                leg,
                saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
                saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
            )

    def test_rejects_incompatible_or_incomplete_earth_saturn_leg(self):
        with self.assertRaisesRegex(TypeError, "must be a Leg"):
            compute_earth_saturn_titan_mission(
                object(),
                saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
                saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
            )

        wrong_route = Leg(origin="Earth", destination="Titan")
        with self.assertRaisesRegex(ValueError, "connect Earth to Saturn"):
            compute_earth_saturn_titan_mission(
                wrong_route,
                saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
                saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
            )

        missing_v_infinity = Leg(
            origin="Earth",
            destination="Saturn",
            trajectory=TrajectoryResult(),
        )
        with self.assertRaisesRegex(ValueError, "arrival v-infinity"):
            compute_earth_saturn_titan_mission(
                missing_v_infinity,
                saturn_periapsis_radius_m=SATURN_PERIAPSIS_RADIUS_M,
                saturn_periapsis_radius_provenance=PERIAPSIS_PROVENANCE,
            )


if __name__ == "__main__":
    unittest.main()
