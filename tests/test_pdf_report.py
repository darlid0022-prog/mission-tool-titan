import unittest
from datetime import date

from mission.pdf_report import MissionPdfReport, generate_mission_summary_pdf


class TestMissionPdfReport(unittest.TestCase):
    def test_known_titan_case_generates_pdf_with_expected_values(self) -> None:
        report = MissionPdfReport(
            destination="Saturn",
            selected_moon="Titan",
            launch_window_start=date(2026, 6, 1),
            launch_window_end=date(2027, 6, 1),
            departure_mjd2000=9_681.181818,
            arrival_mjd2000=12_537.181818,
            mission_duration_days=2_862.258,
            method="lambert",
            v_inf_depart_m_s=10_432.306468,
            v_inf_arrival_m_s=6_490.744714,
            delta_v_rows=(
                ("Earth departure injection", 7_381.480000),
                ("DSM / fly-by corrections", 0.0),
                ("Saturn capture to transfer ellipse", 2_280.8),
                ("Saturn staging circularization", 4_501.6),
                ("Saturn staging to Titan transfer", 1_257.575),
                ("Titan circular capture", 862.725),
            ),
            delta_v_total_m_s=16_284.134471,
        )

        pdf_bytes = generate_mission_summary_pdf(report)
        pdf_text = pdf_bytes.decode("latin-1")

        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 2_000)
        self.assertIn("Earth -> Saturn -> Titan", pdf_text)
        self.assertIn("Earth departure injection", pdf_text)
        self.assertIn("16,284.134", pdf_text)
        self.assertIn("2,862.258 days", pdf_text)
        self.assertIn("10,432.306 m/s", pdf_text)


if __name__ == "__main__":
    unittest.main()
