import unittest

from mission.full_mission import compute_earth_saturn_titan_mission
from mission.gravity_assist import compute_cassini_historical_tour
from mission.models import Leg, TrajectoryResult
from mission.trajectory_plot import (
    CAMERA_PRESETS,
    DEFAULT_VIEW_PRESET,
    build_scene_figure,
    build_scene_table,
    scene_figure_to_standalone_html,
)
from mission.trajectory_scene import segments_from_cassini_tour, segments_from_saturn_system_scene
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


class TestBuildSceneFigureWithDirectSaturnSystemSegments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scene = build_complete_mission_scene(_earth_saturn_titan_mission(), samples=24)
        cls.segments = segments_from_saturn_system_scene(scene)

    def test_one_trace_per_segment(self):
        figure = build_scene_figure(self.segments, unit_label="km")
        self.assertEqual(len(figure.data), len(self.segments))
        self.assertEqual({trace.name for trace in figure.data}, {s.name for s in self.segments})

    def test_every_camera_preset_renders_without_error(self):
        for preset in CAMERA_PRESETS:
            with self.subTest(preset=preset):
                figure = build_scene_figure(self.segments, unit_label="km", view_preset=preset)
                self.assertEqual(figure.layout.scene.camera.eye.x, CAMERA_PRESETS[preset]["eye"]["x"])

    def test_axis_titles_use_the_supplied_unit_label(self):
        figure = build_scene_figure(self.segments, unit_label="km")
        self.assertIn("(km)", figure.layout.scene.xaxis.title.text)

    def test_real_scale_widens_the_size_gap_between_saturn_and_titan(self):
        readable = build_scene_figure(self.segments, unit_label="km", real_scale=False)
        scaled = build_scene_figure(self.segments, unit_label="km", real_scale=True)
        readable_sizes = {trace.name: trace.marker.size for trace in readable.data if trace.marker}
        scaled_sizes = {trace.name: trace.marker.size for trace in scaled.data if trace.marker}
        # Readable mode uses each landmark's own fixed display size, unrelated
        # to real radius. Saturn's real radius (~60,268 km) is much larger
        # than Titan's (~2,575 km, a ~23x ratio); real-scale mode must reflect
        # that in the marker-size ratio far more than the readable ratio does.
        readable_ratio = readable_sizes["Saturn"] / readable_sizes["Titan encounter"]
        scaled_ratio = scaled_sizes["Saturn"] / scaled_sizes["Titan encounter"]
        self.assertGreater(scaled_ratio, readable_ratio)
        # Saturn (the largest sourced body in this segment set) anchors the
        # real-scale range at the maximum legible marker size.
        self.assertEqual(scaled_sizes["Saturn"], 26)

    def test_rejects_an_unknown_view_preset(self):
        with self.assertRaisesRegex(ValueError, "view_preset"):
            build_scene_figure(self.segments, unit_label="km", view_preset="Nowhere")

    def test_rejects_an_empty_segment_tuple(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            build_scene_figure((), unit_label="km")


class TestBuildSceneFigureWithCassiniTourSegments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.segments = segments_from_cassini_tour(compute_cassini_historical_tour())

    def test_default_preset_is_global(self):
        self.assertEqual(DEFAULT_VIEW_PRESET, "Global")
        figure = build_scene_figure(self.segments, unit_label="AU")
        self.assertEqual(figure.layout.scene.camera.eye.x, CAMERA_PRESETS["Global"]["eye"]["x"])

    def test_hover_template_surfaces_optional_fields_when_present(self):
        figure = build_scene_figure(self.segments, unit_label="AU")
        insertion_trace = next(t for t in figure.data if t.name == "Saturn insertion")
        self.assertIn("Delta-v:", insertion_trace.hovertemplate)
        self.assertIn("Duration:", insertion_trace.hovertemplate)

    def test_same_segments_render_regardless_of_which_mission_produced_them(self):
        """The generic builder must not special-case direct vs. gravity-assist data."""
        figure = build_scene_figure(self.segments, unit_label="AU")
        self.assertEqual(len(figure.data), len(self.segments))


class TestBuildSceneTable(unittest.TestCase):
    def test_table_row_count_matches_total_segment_points(self):
        segments = segments_from_cassini_tour(compute_cassini_historical_tour())
        table = build_scene_table(segments)
        self.assertEqual(len(table), sum(len(segment.x) for segment in segments))
        self.assertEqual(
            list(table.columns),
            [
                "Segment",
                "Type",
                "Origin",
                "Destination",
                "Point index",
                "x",
                "y",
                "z",
                "Departure date",
                "Arrival date",
                "Duration (days)",
                "Delta-v (m/s)",
            ],
        )

    def test_rejects_non_segment_input(self):
        with self.assertRaisesRegex(TypeError, "TrajectorySegment"):
            build_scene_table((object(),))


class TestStandaloneHtmlExport(unittest.TestCase):
    def test_exports_a_self_contained_offline_capable_html_document(self):
        segments = segments_from_cassini_tour(compute_cassini_historical_tour())
        figure = build_scene_figure(segments, unit_label="AU")
        html = scene_figure_to_standalone_html(figure)

        self.assertIsInstance(html, str)
        self.assertIn("<html", html.lower())
        # Every <script> tag must be inline (no src=...) - a src= attribute
        # would mean the export depends on a network fetch to render.
        script_tags = [
            line
            for line in html.split("<script")[1:]
            if "src=" in line.split(">", 1)[0]
        ]
        self.assertEqual(script_tags, [])
        # The figure's own data must actually be embedded, not just the library.
        self.assertIn("Saturn insertion", html)

    def test_rejects_a_non_figure_argument(self):
        with self.assertRaisesRegex(TypeError, "plotly"):
            scene_figure_to_standalone_html(object())


if __name__ == "__main__":
    unittest.main()
