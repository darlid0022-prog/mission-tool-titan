import math
import unittest

from mission.full_mission import compute_earth_saturn_titan_mission
from mission.gravity_assist import compute_cassini_historical_tour
from mission.models import Leg, TrajectoryResult
from mission.trajectory_scene import (
    SEGMENT_TYPE_FLYBY,
    SEGMENT_TYPE_INSERTION,
    SEGMENT_TYPE_LANDMARK,
    SEGMENT_TYPE_ORBIT_REFERENCE,
    SEGMENT_TYPE_TRANSFER,
    SegmentStyle,
    TrajectorySegment,
    segments_from_cassini_tour,
    segments_from_saturn_system_scene,
)
from mission.trajectory_visualization import build_complete_mission_scene


def _earth_saturn_titan_mission():
    leg = Leg(
        origin="Earth",
        destination="Saturn",
        trajectory=TrajectoryResult(
            departure_mjd2000=9_681.181818181818,
            arrival_mjd2000=12_537.181818181829,
            tof_years=7.82,
            v_inf_depart=10_432.306468285773,
            v_inf_arrival=6_490.744714263188,
            method="lambert",
        ),
    )
    return compute_earth_saturn_titan_mission(
        leg,
        saturn_periapsis_radius_m=62_330_000.0,
        saturn_periapsis_radius_provenance="Regression fixture.",
        saturn_staging_radius_m=600_000_000.0,
        titan_capture_altitude_m=1_500_000.0,
    )


class TestTrajectorySegmentValidation(unittest.TestCase):
    def _valid_kwargs(self) -> dict:
        return dict(
            id="seg-1",
            name="Test leg",
            type=SEGMENT_TYPE_TRANSFER,
            origin_body="Earth",
            destination_body="Saturn",
            x=(0.0, 1.0),
            y=(0.0, 1.0),
            z=(0.0, 1.0),
        )

    def test_accepts_a_minimal_valid_segment(self):
        segment = TrajectorySegment(**self._valid_kwargs())
        self.assertEqual(segment.type, SEGMENT_TYPE_TRANSFER)
        self.assertFalse(segment.is_point)
        self.assertIsNone(segment.departure_date)
        self.assertIsNone(segment.delta_v_m_s)

    def test_single_point_segment_is_a_landmark_capable_shape(self):
        kwargs = self._valid_kwargs()
        kwargs.update(type=SEGMENT_TYPE_LANDMARK, x=(1.0,), y=(2.0,), z=(3.0,))
        segment = TrajectorySegment(**kwargs)
        self.assertTrue(segment.is_point)

    def test_rejects_empty_id(self):
        kwargs = self._valid_kwargs()
        kwargs["id"] = ""
        with self.assertRaisesRegex(ValueError, "id must be"):
            TrajectorySegment(**kwargs)

    def test_rejects_unknown_type(self):
        kwargs = self._valid_kwargs()
        kwargs["type"] = "not_a_real_type"
        with self.assertRaisesRegex(ValueError, "type must be one of"):
            TrajectorySegment(**kwargs)

    def test_rejects_mismatched_coordinate_lengths(self):
        kwargs = self._valid_kwargs()
        kwargs["y"] = (0.0,)
        with self.assertRaisesRegex(ValueError, "equal length"):
            TrajectorySegment(**kwargs)

    def test_rejects_non_finite_coordinates(self):
        kwargs = self._valid_kwargs()
        kwargs["x"] = (0.0, math.inf)
        with self.assertRaisesRegex(ValueError, "finite"):
            TrajectorySegment(**kwargs)

    def test_rejects_negative_duration_or_delta_v(self):
        kwargs = self._valid_kwargs()
        kwargs["duration_days"] = -1.0
        with self.assertRaisesRegex(ValueError, "duration_days"):
            TrajectorySegment(**kwargs)

        kwargs = self._valid_kwargs()
        kwargs["delta_v_m_s"] = -1.0
        with self.assertRaisesRegex(ValueError, "delta_v_m_s"):
            TrajectorySegment(**kwargs)

    def test_optional_fields_round_trip(self):
        kwargs = self._valid_kwargs()
        kwargs.update(
            departure_date="2026-06-01 00:00 UTC",
            arrival_date="2027-01-01 00:00 UTC",
            duration_days=214.0,
            delta_v_m_s=1234.5,
            style=SegmentStyle(color="#123456", width=9, dash="dot", marker_size=8),
            metadata={"note": "example"},
        )
        segment = TrajectorySegment(**kwargs)
        self.assertEqual(segment.departure_date, "2026-06-01 00:00 UTC")
        self.assertEqual(segment.duration_days, 214.0)
        self.assertEqual(segment.delta_v_m_s, 1234.5)
        self.assertEqual(segment.style.color, "#123456")
        self.assertEqual(segment.metadata["note"], "example")

    def test_style_rejects_non_positive_width_or_marker_size(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            SegmentStyle(color="#000000", width=0)


class TestSaturnSystemSceneAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission_result = _earth_saturn_titan_mission()
        cls.scene = build_complete_mission_scene(cls.mission_result, samples=32)
        cls.segments = segments_from_saturn_system_scene(cls.scene)

    def test_returns_one_segment_per_saturn_curve_plus_two_landmarks(self):
        self.assertEqual(len(self.segments), len(self.scene.saturn_curves) + 2)

    def test_curve_coordinates_are_copied_without_modification(self):
        by_name = {segment.name: segment for segment in self.segments}
        for curve in self.scene.saturn_curves:
            segment = by_name[curve.name]
            self.assertEqual(segment.x, curve.x)
            self.assertEqual(segment.y, curve.y)
            self.assertEqual(segment.z, curve.z)

    def test_titan_transfer_and_titan_orbit_are_typed_correctly(self):
        by_name = {segment.name: segment for segment in self.segments}
        self.assertEqual(by_name["Saturn → Titan transfer"].type, SEGMENT_TYPE_TRANSFER)
        self.assertEqual(by_name["Saturn → Titan transfer"].destination_body, "Titan")
        self.assertEqual(by_name["Titan orbit"].type, SEGMENT_TYPE_ORBIT_REFERENCE)
        self.assertIn(by_name["Saturn arrival ellipse"].type, (SEGMENT_TYPE_INSERTION,))

    def test_landmarks_are_single_point_segments_with_real_radii_where_known(self):
        landmarks = [segment for segment in self.segments if segment.is_point]
        self.assertEqual(len(landmarks), 2)
        names = {segment.name for segment in landmarks}
        self.assertEqual(names, {"Saturn", "Titan encounter"})
        for segment in landmarks:
            self.assertIn("true_radius_m", segment.metadata)
            self.assertIsInstance(segment.metadata["true_radius_m"], float)
            self.assertGreater(segment.metadata["true_radius_m"], 0.0)

    def test_titan_encounter_landmark_matches_titan_transfer_curve_endpoint(self):
        by_name = {segment.name: segment for segment in self.segments}
        transfer = by_name["Saturn → Titan transfer"]
        landmark = by_name["Titan encounter"]
        self.assertEqual(landmark.x[0], transfer.x[-1])
        self.assertEqual(landmark.y[0], transfer.y[-1])
        self.assertEqual(landmark.z[0], transfer.z[-1])


class TestCassiniTourAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tour = compute_cassini_historical_tour()
        cls.segments = segments_from_cassini_tour(cls.tour)

    def test_returns_one_line_segment_per_leg_plus_unique_landmarks(self):
        line_segments = [segment for segment in self.segments if not segment.is_point]
        landmark_segments = [segment for segment in self.segments if segment.is_point]
        self.assertEqual(len(line_segments), 5)
        # Earth, Venus (x2 dates), Venus (x2 dates), Earth, Jupiter, Saturn:
        # every waypoint has a distinct (body, epoch) landmark, none deduplicated
        # across different epochs at the same body.
        self.assertEqual(len(landmark_segments), 6)

    def test_last_leg_is_the_propulsive_insertion_with_positive_delta_v(self):
        insertion = self.segments[0]
        for segment in self.segments:
            if segment.type == SEGMENT_TYPE_INSERTION:
                insertion = segment
        self.assertEqual(insertion.type, SEGMENT_TYPE_INSERTION)
        self.assertEqual(insertion.origin_body, "Jupiter")
        self.assertEqual(insertion.destination_body, "Saturn")
        self.assertIsNotNone(insertion.delta_v_m_s)
        self.assertGreater(insertion.delta_v_m_s, 0.0)

    def test_flyby_legs_report_zero_delta_v(self):
        flybys = [segment for segment in self.segments if segment.type == SEGMENT_TYPE_FLYBY]
        self.assertEqual(len(flybys), 4)
        for segment in flybys:
            self.assertEqual(segment.delta_v_m_s, 0.0)

    def test_leg_endpoints_match_the_tour_positions_exactly(self):
        line_segments = [segment for segment in self.segments if not segment.is_point]
        for segment, leg in zip(line_segments, self.tour, strict=True):
            self.assertEqual(segment.x, (leg.departure_position_m[0], leg.arrival_position_m[0]))
            self.assertEqual(segment.y, (leg.departure_position_m[1], leg.arrival_position_m[1]))
            self.assertEqual(segment.z, (leg.departure_position_m[2], leg.arrival_position_m[2]))

    def test_dates_and_durations_are_populated_from_the_tour(self):
        line_segments = [segment for segment in self.segments if not segment.is_point]
        for segment in line_segments:
            self.assertIsNotNone(segment.departure_date)
            self.assertIsNotNone(segment.arrival_date)
            self.assertIsNotNone(segment.duration_days)
            self.assertGreater(segment.duration_days, 0.0)

    def test_rejects_a_tour_with_the_wrong_number_of_legs(self):
        with self.assertRaisesRegex(ValueError, "five"):
            segments_from_cassini_tour(self.tour[:3])


if __name__ == "__main__":
    unittest.main()
