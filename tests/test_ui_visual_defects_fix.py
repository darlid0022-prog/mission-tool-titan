"""Regression tests for the human-confirmed visual defects on top of d5886c1.

Confirmed defects (Trajectory -> Complete mission trajectory -> interactive
3D view -> Animated): a contextual title truncated on desktop; title, UTC
date, slider, and legend overlapping at ~768px; slider dates overlapping the
legend; Earth departure/Saturn arrival markers crowding the controls.
Mission page, Mass budget: four metrics forced onto one line at ~768px with
truncated labels/values. The mass-ratio metric's label needing to wrap
without an ellipsis. The mobile sidebar leaving a strip of main content
visible around ~406px.

These are static/AppTest checks only, consistent with every other test file
in this session's history - they prove structure (figure layout fields, CSS
rule presence, data invariance) and that the app still renders without
exception. They do NOT prove pixel-perfect visual rendering in a real
browser; that remains a human verification step.
"""

import re
import unittest
from pathlib import Path

from mission.direct_trajectory_animation import build_direct_trajectory_timeline
from mission.launch_search import evaluate_launch_scenario
from mission.trajectory_plot import build_direct_animation_figure, build_scene_figure
from mission.trajectory_scene import segments_from_launch_search
from mission.ui_text import UI_V030_TEXT
from tests.test_app_titan_ui import run_app

ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (ROOT / "mission" / "ui_style.py").read_text()


def _direct_animation_fixture():
    scenario = evaluate_launch_scenario(10_408.0, 12_428.0, sample_count=16)
    source = next(segment for segment in scenario.segments if segment.frame == "heliocentric")
    timeline = build_direct_trajectory_timeline(source, scenario_id=scenario.scenario_id)
    segments = segments_from_launch_search(
        (source,), reference_frame="heliocentric", distance_unit="AU"
    )
    return source, timeline, segments


class TestDirectAnimationLayoutStructure(unittest.TestCase):
    """Correctif 1: the animated figure's own vertical zones must never
    overlap regardless of container width, since the figure's pixel height
    is fixed across breakpoints and only its width is responsive."""

    @classmethod
    def setUpClass(cls):
        cls.source, cls.timeline, cls.segments = _direct_animation_fixture()
        cls.figure = build_direct_animation_figure(cls.segments, cls.timeline)

    def test_no_long_or_per_frame_title_remains(self):
        # The figure carries no title at all now - the trajectory type, date
        # range, and total elapsed time are rendered once in Streamlit above
        # it instead (pages/trajectory_3d.py), so there is nothing left that
        # can be clipped at any width.
        self.assertIsNone(self.figure.layout.title.text)
        for frame in self.figure.frames:
            self.assertIsNone(frame.layout.title.text)

    def test_legend_slider_buttons_bands_are_ordered_and_well_separated(self):
        legend_y = self.figure.layout.legend.y
        slider_y = self.figure.layout.sliders[0].y
        buttons_y = self.figure.layout.updatemenus[0].y
        # All three bands sit below the plot (negative y), each strictly
        # further down than the last, most severe zone last.
        self.assertLess(legend_y, 0)
        self.assertLess(slider_y, legend_y)
        self.assertLess(buttons_y, slider_y)
        # A comfortable minimum gap between adjacent bands - not just
        # "different values" but far enough apart that a wrapped legend row
        # or a slider label cannot plausibly bridge the gap.
        minimum_gap = 0.08
        self.assertGreaterEqual(legend_y - slider_y, minimum_gap)
        self.assertGreaterEqual(slider_y - buttons_y, minimum_gap)

    def test_bottom_margin_reserves_room_for_the_lowest_band(self):
        margin_b = self.figure.layout.margin.b
        height = self.figure.layout.height
        buttons_y = self.figure.layout.updatemenus[0].y
        domain_height = height - self.figure.layout.margin.t - margin_b
        lowest_band_offset_px = abs(buttons_y) * domain_height
        # The margin must comfortably exceed where the lowest band actually
        # sits, or its row would be clipped by the figure's own edge.
        self.assertGreater(margin_b, lowest_band_offset_px + 20)

    def test_slider_labels_carry_both_date_and_elapsed_time(self):
        # Date UTC and elapsed time both remain inside Plotly (the only
        # per-frame-dynamic values), combined into the single slider band
        # rather than a separate title or annotation zone.
        pattern = re.compile(r"\d{4}-\d{2}-\d{2}.*\+[\d,]+ d")
        for step in self.figure.layout.sliders[0].steps:
            self.assertRegex(step.label, pattern)

    def test_auxiliary_position_markers_are_hover_only_not_legend(self):
        # Reduces the legend band to the path plus Earth departure/Saturn
        # arrival - short enough to stay on one line at narrow widths -
        # while every trace (and its data) is still present and hoverable.
        by_name = {trace.name: trace for trace in self.figure.data}
        for hidden_name in (
            "Earth — current ephemeris position",
            "Saturn — current ephemeris position",
            "Spacecraft — sampled position",
        ):
            self.assertIn(hidden_name, by_name)
            self.assertFalse(by_name[hidden_name].showlegend)
        for visible_name in ("Earth departure", "Saturn arrival"):
            self.assertIn(visible_name, by_name)
            self.assertNotEqual(by_name[visible_name].showlegend, False)


class TestDirectAnimationDataUnchanged(unittest.TestCase):
    """Scientific-integrity comparison: presentation-only changes must not
    alter frame count, timestamps, trace count, coordinates, or endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.source, cls.timeline, cls.segments = _direct_animation_fixture()
        cls.figure = build_direct_animation_figure(cls.segments, cls.timeline)

    def test_frame_count_and_names_match_the_timeline_exactly(self):
        self.assertEqual(len(self.figure.frames), len(self.timeline.frames))
        for index, frame in enumerate(self.figure.frames):
            self.assertEqual(frame.name, str(index))

    def test_every_frame_reproduces_the_source_timeline_coordinates(self):
        for index, (frame, instant) in enumerate(zip(self.figure.frames, self.timeline.frames)):
            earth_trace, saturn_trace, spacecraft_trace = frame.data
            self.assertEqual(
                (earth_trace.x[0], earth_trace.y[0], earth_trace.z[0]),
                instant.earth_position_au,
                msg=f"frame {index} Earth position drifted from the timeline",
            )
            self.assertEqual(
                (saturn_trace.x[0], saturn_trace.y[0], saturn_trace.z[0]),
                instant.saturn_position_au,
                msg=f"frame {index} Saturn position drifted from the timeline",
            )
            self.assertEqual(
                (spacecraft_trace.x[0], spacecraft_trace.y[0], spacecraft_trace.z[0]),
                instant.spacecraft_position_au,
                msg=f"frame {index} spacecraft position drifted from the timeline",
            )
            self.assertEqual(spacecraft_trace.customdata[0][0], instant.date_utc)
            self.assertEqual(spacecraft_trace.customdata[0][1], instant.elapsed_days)

    def test_first_and_last_positions_match_the_solved_segment_endpoints(self):
        first, last = self.timeline.frames[0], self.timeline.frames[-1]
        self.assertEqual(
            first.spacecraft_position_au,
            (self.source.x[0], self.source.y[0], self.source.z[0]),
        )
        self.assertEqual(
            last.spacecraft_position_au,
            (self.source.x[-1], self.source.y[-1], self.source.z[-1]),
        )

    def test_reference_frame_and_unit_are_unchanged(self):
        self.assertEqual(self.timeline.reference_frame, "heliocentric")
        self.assertEqual(self.timeline.distance_unit, "AU")
        for segment in self.segments:
            self.assertEqual(segment.metadata["reference_frame"], "heliocentric")
            self.assertEqual(segment.metadata["distance_unit"], "AU")

    def test_trace_count_is_the_segment_count_plus_the_five_added_markers(self):
        self.assertEqual(len(self.figure.data), len(self.segments) + 5)

    def test_timestamps_are_still_strictly_increasing(self):
        epochs = [frame.epoch_mjd2000 for frame in self.timeline.frames]
        self.assertTrue(all(left < right for left, right in zip(epochs, epochs[1:])))


class TestStaticModeUnaffected(unittest.TestCase):
    """Correctif 1 constraint: do not modify Static mode if not necessary -
    build_scene_figure (the Static code path) must be byte-for-byte the same
    figure it was before this fix."""

    def test_static_scene_figure_has_no_animation_layout_pieces(self):
        _, _, segments = _direct_animation_fixture()
        figure = build_scene_figure(segments, unit_label="AU")
        self.assertEqual(tuple(figure.frames), ())
        self.assertEqual(tuple(figure.layout.updatemenus), ())
        self.assertEqual(tuple(figure.layout.sliders), ())

    def test_static_scene_figure_keeps_its_original_legend_and_margins(self):
        _, _, segments = _direct_animation_fixture()
        figure = build_scene_figure(segments, unit_label="AU")
        self.assertEqual(figure.layout.legend.y, -0.08)
        self.assertEqual(figure.layout.margin.t, 40)
        self.assertEqual(figure.layout.margin.b, 0)


class TestTrajectory3DAnimatedContextInStreamlit(unittest.TestCase):
    """The trajectory type, UTC date range, and total elapsed time now
    render once in Streamlit above the figure, in Animated mode only."""

    def test_animated_mode_shows_the_context_exactly_once_and_not_duplicated(self):
        # Regression for the real-world "KeyError:
        # 'trajectory_3d_animated_transfer_label'" - the catalog check below
        # must fail on its own (missing key / wrong type / empty string), and
        # the app.run() below must actually exercise the Animated branch
        # rather than merely grepping the source for the key's name.
        self.assertIn("trajectory_3d_animated_transfer_label", UI_V030_TEXT)
        transfer_label = UI_V030_TEXT["trajectory_3d_animated_transfer_label"]
        self.assertIsInstance(transfer_label, str)
        self.assertTrue(transfer_label.strip())

        app = run_app(page_path="pages/trajectory_3d.py")
        self.assertFalse(app.exception)
        display_mode = next(
            control for control in app.segmented_control if control.label == "Trajectory display"
        )
        self.assertEqual(display_mode.value, "Animated")
        transfer_labels = [md for md in app.markdown if transfer_label in md.value]
        self.assertEqual(len(transfer_labels), 1)
        elapsed_captions = [
            c for c in app.caption if "elapsed" in c.value and "days total" in c.value
        ]
        self.assertEqual(len(elapsed_captions), 1)

    def test_static_mode_does_not_show_the_animated_context(self):
        app = run_app(page_path="pages/trajectory_3d.py")
        display_mode = next(
            control for control in app.segmented_control if control.label == "Trajectory display"
        )
        app = display_mode.set_value("Static").run(timeout=30)
        self.assertFalse(app.exception)
        transfer_label = UI_V030_TEXT["trajectory_3d_animated_transfer_label"]
        transfer_labels = [md for md in app.markdown if transfer_label in md.value]
        self.assertEqual(transfer_labels, [])


class TestMassBudgetResponsiveLayoutCss(unittest.TestCase):
    """Correctif 2/3: CSS structure backing the responsive mass metrics and
    the wrappable mass-ratio label."""

    def test_mass_budget_metrics_row_has_a_two_column_breakpoint_at_48rem(self):
        block_match = re.search(r"@media \(max-width: 48rem\) \{(.*?)\n\}", STYLE_SOURCE, re.DOTALL)
        assert block_match is not None, "expected the existing 48rem mobile breakpoint"
        block = block_match.group(1)
        self.assertIn(".st-key-mass_budget_metrics_row", block)
        self.assertIn("flex-wrap: wrap", block)
        self.assertIn("flex: 1 1 45%", block)

    def test_mass_budget_metrics_row_folds_to_one_column_below_26rem(self):
        block_match = re.search(r"@media \(max-width: 26rem\) \{(.*?)\n\}", STYLE_SOURCE, re.DOTALL)
        assert block_match is not None, "expected a narrow single-column breakpoint"
        block = block_match.group(1)
        self.assertIn(".st-key-mass_budget_metrics_row", block)
        self.assertIn("flex: 1 1 100%", block)

    def test_mass_ratio_label_wraps_without_a_forced_ellipsis(self):
        rule_match = re.search(
            r"\.st-key-mass_ratio_metric \[data-testid=\"stMetricLabel\"\][^{]*\{([^}]*)\}",
            STYLE_SOURCE,
        )
        assert rule_match is not None, "expected a wrap override for the mass-ratio label"
        rule_body = rule_match.group(1)
        self.assertIn("white-space: normal", rule_body)
        self.assertNotIn("ellipsis", rule_body)

    def test_the_ratio_label_text_itself_was_not_shortened(self):
        source = (ROOT / "pages" / "mission_setup.py").read_text()
        self.assertIn("Simplified mass ratio using the full connected Δv", source)


class TestMassBudgetMetricsStillRenderUnchangedValues(unittest.TestCase):
    """AppTest regression: wrapping the metrics in a keyed container for CSS
    targeting must not change what they display."""

    def test_four_mass_metrics_and_the_ratio_metric_render_with_expected_labels(self):
        app = run_app()
        self.assertFalse(app.exception)
        labels = {m.label for m in app.metric}
        for expected in (
            "Instrument mass",
            "Simplified dry mass",
            "Simplified propellant mass",
            "Simplified total wet mass",
            "Simplified mass ratio using the full connected Δv",
        ):
            self.assertIn(expected, labels)


class TestMobileSidebarCoverageCss(unittest.TestCase):
    """Correctif 4: below ~500px the sidebar must fully cover the usable
    area (or fully hide the main content) and stay opaque, with no effect
    on desktop."""

    def test_full_coverage_rule_exists_scoped_to_a_sub_500px_breakpoint(self):
        block_match = re.search(
            r"@media \(max-width: 31\.25rem\) \{(.*?)\n\}", STYLE_SOURCE, re.DOTALL
        )
        assert block_match is not None, "expected a <500px sidebar breakpoint"
        block = block_match.group(1)
        self.assertIn('[data-testid="stSidebar"]', block)
        self.assertIn("width: 100vw", block)
        self.assertIn("background-color:", block)

    def test_desktop_sidebar_rule_is_not_forced_to_full_width(self):
        # The FIRST stSidebar rule in the file is the base (non-media) one -
        # it must remain untouched: only the border-right styling, no
        # width/background override that would also apply on desktop.
        base_match = re.search(r'\[data-testid="stSidebar"\] \{([^}]*)\}', STYLE_SOURCE)
        assert base_match is not None
        base_rule = base_match.group(1)
        self.assertNotIn("100vw", base_rule)
        self.assertIn("border-right", base_rule)

    def test_stable_testids_only_are_used_for_the_sidebar_override(self):
        # data-testid="stSidebar" is the same confirmed-present hook already
        # used elsewhere in this stylesheet (see the desktop border-right
        # rule above it) - no newly-invented selector.
        self.assertEqual(STYLE_SOURCE.count('[data-testid="stSidebar"]'), 2)


if __name__ == "__main__":
    unittest.main()
