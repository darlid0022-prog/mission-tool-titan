import math
import unittest
from unittest.mock import patch

from mission.direct_trajectory_animation import (
    build_baseline_lambert_segment,
    build_direct_trajectory_timeline,
)
from mission.launch_search import evaluate_launch_scenario
from mission.launch_search_ephemeris import solve_earth_saturn_lambert
from mission.models import TrajectoryResult
from mission.trajectory_plot import (
    build_direct_animation_figure,
    scene_figure_to_standalone_html,
)
from mission.trajectory_scene import segments_from_launch_search


class TestDirectTrajectoryAnimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenario = evaluate_launch_scenario(10_408.0, 12_428.0, sample_count=16)
        cls.source = next(
            segment for segment in cls.scenario.segments if segment.frame == "heliocentric"
        )
        cls.timeline = build_direct_trajectory_timeline(
            cls.source, scenario_id=cls.scenario.scenario_id
        )
        cls.segments = segments_from_launch_search(
            (cls.source,), reference_frame="heliocentric", distance_unit="AU"
        )

    def test_first_and_last_frames_match_existing_segment_endpoints(self):
        first = self.timeline.frames[0]
        last = self.timeline.frames[-1]
        self.assertEqual(first.epoch_mjd2000, self.source.departure_mjd2000)
        self.assertEqual(last.epoch_mjd2000, self.source.arrival_mjd2000)
        self.assertEqual(
            first.spacecraft_position_au, (self.source.x[0], self.source.y[0], self.source.z[0])
        )
        self.assertEqual(
            last.spacecraft_position_au, (self.source.x[-1], self.source.y[-1], self.source.z[-1])
        )

    def test_dates_are_strictly_monotone_and_planet_states_are_finite(self):
        epochs = [frame.epoch_mjd2000 for frame in self.timeline.frames]
        self.assertTrue(all(left < right for left, right in zip(epochs, epochs[1:])))
        self.assertTrue(
            all(
                math.isfinite(value)
                for frame in self.timeline.frames
                for vector in (frame.earth_position_au, frame.saturn_position_au)
                for value in vector
            )
        )

    def test_timeline_rejects_mixed_reference_frame_or_unit(self):
        saturn_source = next(
            segment for segment in self.scenario.segments if segment.frame == "saturn_centred"
        )
        with self.assertRaisesRegex(ValueError, "heliocentric"):
            build_direct_trajectory_timeline(saturn_source, scenario_id="wrong-scene")

    def test_animation_does_not_change_delta_v(self):
        before = self.scenario.total_delta_v_m_s
        build_direct_trajectory_timeline(self.source, scenario_id=self.scenario.scenario_id)
        self.assertEqual(self.scenario.total_delta_v_m_s, before)
        self.assertEqual(before, sum(value for _, value in self.scenario.delta_v_by_manoeuvre_m_s))

    def test_plotly_frames_and_static_html_export_are_valid(self):
        figure = build_direct_animation_figure(self.segments, self.timeline)
        self.assertEqual(len(figure.frames), len(self.timeline.frames))
        self.assertEqual(figure.frames[0].name, "0")
        self.assertEqual(figure.frames[-1].name, str(len(self.timeline.frames) - 1))
        labels = [button.label for button in figure.layout.updatemenus[0].buttons]
        self.assertEqual(labels, ["Play", "Pause", "Reset"])
        html = scene_figure_to_standalone_html(figure)
        self.assertIn("Plotly.addFrames", html)
        self.assertIn("graphical interpolation", self.timeline.interpolation_notice)
        self.assertIn(
            "not an independent dynamical propagation", self.timeline.interpolation_notice
        )

    def test_baseline_arc_reuses_retained_lambert_state(self):
        solved = solve_earth_saturn_lambert(10_408.0, 12_428.0, 16)
        trajectory = TrajectoryResult(
            departure_mjd2000=solved.departure_mjd2000,
            arrival_mjd2000=solved.arrival_mjd2000,
            v_inf_depart=solved.earth_v_infinity_m_s,
            v_inf_arrival=solved.saturn_v_infinity_m_s,
            method="lambert",
            departure_position_m=solved.departure_position_m,
            arrival_position_m=solved.arrival_position_m,
            transfer_departure_velocity_m_s=solved.transfer_departure_velocity_m_s,
            central_mu_m3_s2=1.3271244004127942e20,
        )
        with patch(
            "mission.direct_trajectory_animation.pk.lambert_problem",
            side_effect=AssertionError("animation must not resolve Lambert"),
        ):
            segment = build_baseline_lambert_segment(trajectory, frame_count=32)
        self.assertEqual(segment.x[0], solved.sample_positions_au[0][0])
        self.assertEqual(segment.x[-1], solved.sample_positions_au[-1][0])
        self.assertEqual(len(segment.x), 32)


if __name__ == "__main__":
    unittest.main()
