import unittest

from mission.colors import (
    DARK_SURFACE,
    LIGHT_SURFACE,
    PHASE_ORDER,
    wcag_contrast_ratio,
)

# WCAG AA non-text/large-text threshold: phase colors are used as graphical
# marks (curve lines, markers, badges) in this app, never as small body
# text, so 3:1 - not the 4.5:1 normal-text threshold - is the applicable bar.
MINIMUM_GRAPHICAL_CONTRAST = 3.0


class TestPhaseColorContrast(unittest.TestCase):
    def test_contrast_ratio_matches_known_reference_values(self):
        # Black vs white is the canonical 21:1 WCAG reference pair.
        self.assertAlmostEqual(wcag_contrast_ratio("#000000", "#ffffff"), 21.0, places=2)
        self.assertEqual(wcag_contrast_ratio("#2a78d6", "#2a78d6"), 1.0)
        # Symmetric regardless of argument order.
        self.assertAlmostEqual(
            wcag_contrast_ratio("#2a78d6", LIGHT_SURFACE),
            wcag_contrast_ratio(LIGHT_SURFACE, "#2a78d6"),
        )

    def test_every_phase_color_clears_aa_graphical_contrast_on_light_surface(self):
        for phase in PHASE_ORDER:
            with self.subTest(phase=phase.label, step="light"):
                ratio = wcag_contrast_ratio(phase.light, LIGHT_SURFACE)
                self.assertGreaterEqual(
                    ratio,
                    MINIMUM_GRAPHICAL_CONTRAST,
                    msg=f"{phase.label} light step {phase.light} is only {ratio:.2f}:1 "
                    f"against the light surface {LIGHT_SURFACE}.",
                )

    def test_every_phase_color_clears_aa_graphical_contrast_on_dark_surface(self):
        for phase in PHASE_ORDER:
            with self.subTest(phase=phase.label, step="dark"):
                ratio = wcag_contrast_ratio(phase.dark, DARK_SURFACE)
                self.assertGreaterEqual(
                    ratio,
                    MINIMUM_GRAPHICAL_CONTRAST,
                    msg=f"{phase.label} dark step {phase.dark} is only {ratio:.2f}:1 "
                    f"against the dark surface {DARK_SURFACE}.",
                )

    def test_phase_labels_and_hex_values_are_unique(self):
        labels = [phase.label for phase in PHASE_ORDER]
        light_hexes = [phase.light.lower() for phase in PHASE_ORDER]
        dark_hexes = [phase.dark.lower() for phase in PHASE_ORDER]
        self.assertEqual(len(labels), len(set(labels)), "Phase labels must be unique.")
        self.assertEqual(
            len(light_hexes), len(set(light_hexes)), "Light-step hexes must be unique."
        )
        self.assertEqual(len(dark_hexes), len(set(dark_hexes)), "Dark-step hexes must be unique.")


if __name__ == "__main__":
    unittest.main()
