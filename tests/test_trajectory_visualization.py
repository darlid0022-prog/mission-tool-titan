import math
import unittest

from mission.full_mission import compute_earth_saturn_titan_mission
from mission.gravity_assist import compute_cassini_historical_tour
from mission.models import Leg, TrajectoryResult
from mission.trajectory_plot import (
    build_cassini_historical_figure,
    build_complete_mission_figure,
    build_complete_mission_table,
)
from mission.trajectory_visualization import (
    build_complete_mission_scene,
    build_mission_animation_timeline,
    interpolate_spacecraft_position,
)


class TestCompleteMissionVisualization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        earth_saturn_leg = Leg(
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
        cls.mission_result = compute_earth_saturn_titan_mission(
            earth_saturn_leg,
            saturn_periapsis_radius_m=62_330_000.0,
            saturn_periapsis_radius_provenance="Regression fixture.",
            saturn_staging_radius_m=600_000_000.0,
            titan_capture_altitude_m=1_500_000.0,
        )
        cls.scene = build_complete_mission_scene(cls.mission_result, samples=48)
        cls.timeline = build_mission_animation_timeline(cls.scene, cls.mission_result)

    def test_scene_contains_complete_two_scale_chain(self):
        self.assertEqual(
            tuple(curve.name for curve in self.scene.heliocentric_curves),
            (
                "Earth orbit",
                "Earth → Saturn Lambert transfer",
                "Saturn orbit",
            ),
        )
        self.assertEqual(
            tuple(curve.name for curve in self.scene.saturn_curves),
            (
                "Saturn arrival ellipse",
                "Saturn staging orbit",
                "Saturn → Titan transfer",
                "Titan orbit",
            ),
        )
        for curve in (*self.scene.heliocentric_curves, *self.scene.saturn_curves):
            self.assertEqual(len(curve.x), 48)
            self.assertTrue(all(math.isfinite(value) for value in (*curve.x, *curve.y, *curve.z)))

    def test_saturn_geometry_preserves_model_radii(self):
        curves = {curve.name: curve for curve in self.scene.saturn_curves}
        expected = {
            "Saturn staging orbit": (600_000.0, 600_000.0),
            "Titan orbit": (1_221_870.0, 1_221_870.0),
            "Saturn arrival ellipse": (62_330.0, 600_000.0),
            "Saturn → Titan transfer": (600_000.0, 1_221_870.0),
        }
        for name, (minimum, maximum) in expected.items():
            with self.subTest(curve=name):
                radii = [
                    math.sqrt(x * x + y * y + z * z)
                    for x, y, z in zip(
                        curves[name].x,
                        curves[name].y,
                        curves[name].z,
                        strict=True,
                    )
                ]
                self.assertAlmostEqual(min(radii), minimum, delta=1e-6)
                self.assertAlmostEqual(max(radii), maximum, delta=1e-6)

    def test_plotly_figure_has_one_trace_per_curve_and_two_3d_scenes(self):
        figure = build_complete_mission_figure(self.scene)

        self.assertEqual(len(figure.data), 12)
        self.assertEqual(
            {trace.name for trace in figure.data},
            {
                "Earth orbit",
                "Earth → Saturn Lambert transfer",
                "Saturn orbit",
                "Saturn arrival ellipse",
                "Saturn staging orbit",
                "Saturn → Titan transfer",
                "Titan orbit",
                "Sun",
                "Earth departure",
                "Saturn arrival",
                "Saturn",
                "Titan encounter",
            },
        )
        self.assertEqual(figure.layout.scene.aspectmode, "data")
        self.assertEqual(figure.layout.scene2.aspectmode, "data")

    def test_rejects_too_few_samples(self):
        with self.assertRaisesRegex(ValueError, "at least"):
            build_complete_mission_scene(self.mission_result, samples=10)

    def test_animation_endpoints_match_known_transfer_states(self):
        launch = interpolate_spacecraft_position(self.timeline, 0.0)
        titan_arrival = interpolate_spacecraft_position(
            self.timeline,
            self.timeline.total_duration_days,
        )
        lambert = self.scene.heliocentric_curves[1]
        titan_transfer = self.scene.saturn_curves[2]

        for actual, expected in zip(
            (launch.x, launch.y, launch.z),
            (lambert.x[0], lambert.y[0], lambert.z[0]),
            strict=True,
        ):
            self.assertAlmostEqual(actual, expected, delta=1e-12)
        for actual, expected in zip(
            (titan_arrival.x, titan_arrival.y, titan_arrival.z),
            (titan_transfer.x[-1], titan_transfer.y[-1], titan_transfer.z[-1]),
            strict=True,
        ):
            self.assertAlmostEqual(actual, expected, delta=1e-6)

    def test_animation_phase_transitions_switch_display_frames(self):
        earth_end = self.timeline.earth_saturn_duration_days
        staging_end = earth_end + self.timeline.saturn_staging_duration_days
        cases = (
            (0.0, "Earth → Saturn transfer", "heliocentric"),
            (earth_end, "Saturn arrival → staging", "saturn_centred"),
            (staging_end, "Saturn → Titan transfer", "saturn_centred"),
        )
        for elapsed_days, expected_phase, expected_frame in cases:
            with self.subTest(elapsed_days=elapsed_days):
                position = interpolate_spacecraft_position(self.timeline, elapsed_days)
                self.assertEqual(position.phase_name, expected_phase)
                self.assertEqual(position.frame, expected_frame)

    def test_animated_figure_adds_one_marker_to_the_active_panel(self):
        earth_end = self.timeline.earth_saturn_duration_days
        staging_end = earth_end + self.timeline.saturn_staging_duration_days
        cases = (
            (0.0, "scene"),
            (earth_end, "scene2"),
            (staging_end, "scene2"),
        )
        for elapsed_days, expected_scene in cases:
            with self.subTest(elapsed_days=elapsed_days):
                position = interpolate_spacecraft_position(self.timeline, elapsed_days)
                figure = build_complete_mission_figure(self.scene, position)

                self.assertEqual(len(figure.data), 13)
                marker = figure.data[-1]
                self.assertEqual(marker.name, "Spacecraft — current position")
                self.assertEqual(marker.scene, expected_scene)


class TestCassiniHistoricalVisualization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tour = compute_cassini_historical_tour()
        cls.figure = build_cassini_historical_figure(cls.tour)

    def test_has_five_distinct_legend_entries(self):
        self.assertEqual(
            [trace.name for trace in self.figure.data],
            ["Venus 1", "Venus 2", "Earth", "Jupiter", "Saturn insertion"],
        )
        self.assertTrue(self.figure.layout.showlegend)
        self.assertEqual(len({trace.line.dash for trace in self.figure.data}), 5)

    def test_uses_exact_tour_endpoint_positions(self):
        import pykep as pk

        for trace, segment in zip(self.figure.data, self.tour, strict=True):
            expected = (segment.departure_position_m, segment.arrival_position_m)
            self.assertEqual(
                tuple(trace.x), tuple(position[0] / pk.AU for position in expected)
            )
            self.assertEqual(
                tuple(trace.y), tuple(position[1] / pk.AU for position in expected)
            )
            self.assertEqual(
                tuple(trace.z), tuple(position[2] / pk.AU for position in expected)
            )

    def test_hover_carries_real_dates_events_and_altitudes(self):
        for trace, segment in zip(self.figure.data, self.tour, strict=True):
            self.assertIn("Date:", trace.hovertemplate)
            self.assertIn("Flyby body / event:", trace.hovertemplate)
            self.assertIn("Flyby altitude:", trace.hovertemplate)
            self.assertEqual(trace.customdata[0][1], trace.customdata[1][1])
            self.assertEqual(
                trace.customdata[1][2],
                segment.result.periapsis_altitude_m / 1_000.0,
            )
        self.assertEqual(self.figure.data[-1].customdata[-1][1], "insertion")


class TestCompleteMissionTable(unittest.TestCase):
    """Accessible data-table alternative to the 3D chart (see pages/trajectory_3d.py)."""

    @classmethod
    def setUpClass(cls):
        earth_saturn_leg = Leg(
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
        mission_result = compute_earth_saturn_titan_mission(
            earth_saturn_leg,
            saturn_periapsis_radius_m=62_330_000.0,
            saturn_periapsis_radius_provenance="Regression fixture.",
            saturn_staging_radius_m=600_000_000.0,
            titan_capture_altitude_m=1_500_000.0,
        )
        cls.scene = build_complete_mission_scene(mission_result, samples=48)
        cls.figure = build_complete_mission_figure(cls.scene)
        cls.table = build_complete_mission_table(cls.figure)

    def test_table_row_count_matches_the_chart_exactly(self):
        self.assertEqual(len(self.table), sum(len(trace.x) for trace in self.figure.data))
        # 7 curves x 48 samples, plus 5 single-point landmark markers.
        self.assertEqual(len(self.table), 7 * 48 + 5)

    def test_table_columns_are_labeled_with_units(self):
        self.assertEqual(
            list(self.table.columns),
            ["Element", "Type", "Panel", "Point index", "x", "y", "z", "Unit"],
        )

    def test_every_curve_and_marker_element_is_present(self):
        self.assertEqual(
            set(self.table["Element"]),
            {trace.name for trace in self.figure.data},
        )
        self.assertEqual(set(self.table["Type"]), {"Curve", "Marker"})

    def test_panels_carry_their_own_reference_frame_and_unit(self):
        heliocentric = self.table[self.table["Element"] == "Earth orbit"]
        saturn_panel = self.table[self.table["Element"] == "Titan orbit"]
        self.assertTrue((heliocentric["Unit"] == "AU").all())
        self.assertTrue(heliocentric["Panel"].str.contains("Heliocentric").all())
        self.assertTrue((saturn_panel["Unit"] == "km").all())
        self.assertTrue(saturn_panel["Panel"].str.contains("Saturn system").all())

    def test_table_values_match_the_curve_trace_exactly(self):
        trace = next(t for t in self.figure.data if t.name == "Earth orbit")
        rows = self.table[self.table["Element"] == "Earth orbit"].reset_index(drop=True)
        self.assertEqual(len(rows), len(trace.x))
        self.assertEqual(rows.loc[0, "x"], trace.x[0])
        self.assertEqual(rows.loc[0, "y"], trace.y[0])
        self.assertEqual(rows.loc[0, "z"], trace.z[0])
        self.assertEqual(rows.loc[len(rows) - 1, "x"], trace.x[-1])

    def test_rejects_a_non_figure_argument(self):
        with self.assertRaisesRegex(TypeError, "must be a plotly"):
            build_complete_mission_table(object())


if __name__ == "__main__":
    unittest.main()
