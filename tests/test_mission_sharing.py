import unittest
from datetime import date

import pandas as pd
from pandas.testing import assert_frame_equal

from app_services import (
    MissionSetupInputs,
    build_mission_share_url,
    decode_mission_setup_query,
    encode_mission_setup_query,
)


class TestMissionSharing(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = MissionSetupInputs(
            destination="Saturn",
            selected_moon="Titan",
            departure_type="LEO",
            leo_altitude_km=250.0,
            saturn_periapsis_radius_km=62_330.0,
            saturn_staging_radius_km=600_000.0,
            titan_capture_altitude_km=1_500.0,
            launch_window_start=date(2026, 6, 1),
            launch_window_end=date(2027, 6, 1),
            isp_s=320.0,
            instruments_df=pd.DataFrame(
                [
                    {
                        "Instrument": "Science payload (aggregate)",
                        "Cible": "Orbiter",
                        "Masse (kg)": 143.5,
                        "Puissance (W)": 323.0,
                        "Débit (bps)": 0.0,
                    },
                    {
                        "Instrument": "Test camera",
                        "Cible": "Lander",
                        "Masse (kg)": 12.25,
                        "Puissance (W)": 42.5,
                        "Débit (bps)": 8_192.0,
                    },
                ]
            ),
        )

    def test_inputs_round_trip_through_query_params(self) -> None:
        query_params = encode_mission_setup_query(self.inputs)
        restored = decode_mission_setup_query(query_params)

        self.assertEqual(restored.destination, self.inputs.destination)
        self.assertEqual(restored.selected_moon, self.inputs.selected_moon)
        self.assertEqual(restored.departure_type, self.inputs.departure_type)
        self.assertEqual(restored.leo_altitude_km, self.inputs.leo_altitude_km)
        self.assertEqual(
            restored.saturn_periapsis_radius_km,
            self.inputs.saturn_periapsis_radius_km,
        )
        self.assertEqual(restored.saturn_staging_radius_km, self.inputs.saturn_staging_radius_km)
        self.assertEqual(
            restored.titan_capture_altitude_km,
            self.inputs.titan_capture_altitude_km,
        )
        self.assertEqual(restored.launch_window_start, self.inputs.launch_window_start)
        self.assertEqual(restored.launch_window_end, self.inputs.launch_window_end)
        self.assertEqual(restored.isp_s, self.inputs.isp_s)
        assert_frame_equal(restored.instruments_df, self.inputs.instruments_df)

    def test_share_url_preserves_the_encoded_query(self) -> None:
        query_params = encode_mission_setup_query(self.inputs)
        share_url = build_mission_share_url(
            "https://mission.example/setup?obsolete=true",
            query_params,
        )

        self.assertEqual(
            share_url,
            f"https://mission.example/setup?mission={query_params['mission']}",
        )

    def test_rejects_malformed_or_incompatible_shared_state(self) -> None:
        for query_params in ({}, {"mission": "not-valid-base64"}):
            with self.subTest(query_params=query_params):
                with self.assertRaises(ValueError):
                    decode_mission_setup_query(query_params)


if __name__ == "__main__":
    unittest.main()
