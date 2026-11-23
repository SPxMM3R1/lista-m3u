"""Cobertura EPG del 2026-11-23: Red Bull World, NTV y Stingray iConcerts.

Pedido del usuario: «Revisa la programación de ambas listas, 1 por 1. No puede
quedar ningún canal sin programación, eso es imperativo». Las tres entradas
quedan declaradas en ``epg-overrides.json`` con una fuente real y un respaldo
verificado; no se inventa programación.
"""
import json
from pathlib import Path
import unittest

import update_m3u


class EpgOverrides20261123Test(unittest.TestCase):
    def setUp(self):
        self.channels = json.loads(
            Path(update_m3u.EPG_OVERRIDES_PATH).read_text(encoding="utf-8")
        )["channels"]

    def test_red_bull_world_falls_back_to_cz1(self):
        entry = self.channels["RedBullWorldEnglish.int"]
        self.assertEqual(("cz1", "Red.Bull.TV.cz"),
                         (entry["source"], entry["source_id"]))

    def test_ntv_claro_guide_is_primary_and_covers_the_gap(self):
        entry = self.channels["45"]
        self.assertEqual(("claro-guia", "claro:chile:908362", True),
                         (entry["source"], entry["source_id"], entry.get("primary")))

    def test_stingray_iconcerts_uses_pt1_with_measured_shift(self):
        entry = self.channels["PublicDirect.650a768cd537cb17d491e369"]
        self.assertEqual(("pt1", "Stingray.iConcerts.HD.pt", 60),
                         (entry["source"], entry["source_id"], entry["shift_minutes"]))

    def test_espn_premium_chile_uses_gatotv_chile(self):
        entry = self.channels["PublicDirect.9cd6da14085f95bfe651ca1e"]
        self.assertEqual(("gatotv", "gatotv:espn_premium_chile"),
                         (entry["source"], entry["source_id"]))

    def test_espn_premium_argentina_uses_claro_argentina(self):
        entry = self.channels["IPTVOrg.ESPNPremium.ar-HD"]
        self.assertEqual(("claro-guia", "claro:argentina:888160"),
                         (entry["source"], entry["source_id"]))

    def test_trial_channels_with_country_guide_enter_epg_scope(self):
        scope = {channel.tvg_id for channel in update_m3u.main_playlist_channels()}
        self.assertIn("PublicDirect.9cd6da14085f95bfe651ca1e", scope)
        self.assertIn("IPTVOrg.ESPNPremium.ar-HD", scope)
        self.assertEqual(105, len(scope))


if __name__ == "__main__":
    unittest.main()
