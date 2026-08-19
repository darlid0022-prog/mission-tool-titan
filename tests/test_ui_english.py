import ast
import unittest
from pathlib import Path

from mission.ui_text import UI_SYMBOLS, UI_TEXT, UI_UNITS, UI_V030_TEXT, UI_V030_TOOLTIPS

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_VISIBLE_FRAGMENTS = (
    "Saturne",
    "Terre",
    "Calculer",
    "Masse sèche",
    "Masse d'ergols",
    "Fenêtre de lancement",
    "Hypothèses",
    "modèle préliminaire",
    "n'est pas",
    "Sélectionnez",
)


class TestEnglishUiCopy(unittest.TestCase):
    def test_central_ui_copy_contains_no_known_french_fragments(self):
        copy = "\n".join(
            (
                *UI_TEXT.values(),
                *UI_V030_TEXT.values(),
                *UI_V030_TOOLTIPS.values(),
            )
        )
        for fragment in FORBIDDEN_VISIBLE_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, copy)

    def test_app_string_literals_contain_no_known_french_fragments(self):
        tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
        literals = "\n".join(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )
        for fragment in FORBIDDEN_VISIBLE_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, literals)

    def test_v030_catalog_contains_required_locked_copy(self):
        self.assertEqual(UI_V030_TEXT["mission_title"], "Mission")
        self.assertEqual(UI_V030_TEXT["trajectory_title"], "Trajectory")
        self.assertEqual(UI_V030_TEXT["budget_title"], "Budget")
        self.assertEqual(UI_V030_TEXT["verdict_title"], "Verdict")
        self.assertEqual(
            UI_V030_TEXT["budget_saturn_subtotal"],
            "Subtotal of modeled Saturn maneuvers",
        )
        self.assertEqual(UI_V030_TEXT["budget_total_heading"], "Connected total")
        self.assertEqual(
            UI_V030_TEXT["badge_isolated"],
            "Not connected to the active mission",
        )

    def test_scientific_symbols_and_units_are_centralized(self):
        self.assertEqual(UI_SYMBOLS["c3"], "C3")
        self.assertEqual(UI_SYMBOLS["v_infinity"], "v∞")
        self.assertEqual(UI_SYMBOLS["delta_v"], "Δv")
        self.assertEqual(UI_SYMBOLS["utc"], "UTC")
        self.assertEqual(UI_SYMBOLS["mjd2000"], "MJD2000")
        self.assertEqual(UI_UNITS["metres_per_second"], "m/s")
        self.assertEqual(UI_UNITS["square_kilometres_per_square_second"], "km²/s²")


if __name__ == "__main__":
    unittest.main()
