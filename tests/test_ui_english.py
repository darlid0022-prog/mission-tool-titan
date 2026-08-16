import ast
import unittest
from pathlib import Path

from mission.ui_text import UI_TEXT

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
        copy = "\n".join(UI_TEXT.values())
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


if __name__ == "__main__":
    unittest.main()
