"""Títulos de Red Bull sin la marca «EN VIVO» (pedido del usuario, 2026-10-24)."""
import unittest

from epg_sources.red_bull import clean_red_bull_title, normalize_red_bull_schedule


class RedBullLiveMarkTest(unittest.TestCase):
    def test_removes_live_prefix_with_and_without_colon(self):
        self.assertEqual(
            "Red Bull Dance Your Style World Final 2026",
            clean_red_bull_title("EN VIVO: EN VIVO Red Bull Dance Your Style World Final 2026"),
        )
        self.assertEqual(
            "Red Bull Rampage 2026: Competencia Femenina",
            clean_red_bull_title("EN VIVO Red Bull Rampage 2026: Competencia Femenina"),
        )

    def test_removes_live_marker_anywhere_and_any_case(self):
        self.assertEqual("Final Round 2", clean_red_bull_title("Final - en vivo: Round 2"))
        self.assertEqual("Final", clean_red_bull_title("Final En Vivo"))

    def test_keeps_titles_without_the_marker(self):
        self.assertEqual(
            "Red Bull Soapbox Race: coches sin motor en Texas",
            clean_red_bull_title("Red Bull Soapbox Race: coches sin motor en Texas"),
        )
        self.assertEqual("Vivo en Nueva York", clean_red_bull_title("Vivo en Nueva York"))
        self.assertEqual("Red Bull Live Sessions", clean_red_bull_title("Red Bull Live Sessions"))

    def test_keeps_original_when_nothing_would_remain(self):
        self.assertEqual("EN VIVO", clean_red_bull_title("EN VIVO"))

    def test_normalize_cleans_titles_without_mutating_the_source(self):
        source = [{
            "start_time": "2026-10-24T18:00:00Z",
            "end_time": "2026-10-24T19:00:00Z",
            "title": "EN VIVO: EN VIVO Red Bull Dance Your Style World Final 2026",
        }]
        result = normalize_red_bull_schedule(source)
        self.assertEqual("Red Bull Dance Your Style World Final 2026", result[0]["title"])
        self.assertIn("EN VIVO", source[0]["title"])


if __name__ == "__main__":
    unittest.main()
