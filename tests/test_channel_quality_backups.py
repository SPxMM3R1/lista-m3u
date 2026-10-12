import json
import unittest
from pathlib import Path

import update_m3u as runner
import os

from catalog_approval import live_catalog  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_ESPN7 = "Nauta.52bb87a2e2911ed34f7ae3bc@Nauta"
OFFICIAL_ESPN1_AR = "Nauta.4dec2794ee77cb450b79aa5b@Nauta"
OFFICIAL_ESPN1_MX = "Nauta.267720adcfe18e0c87fca46c@Nauta"
OFFICIAL_MTV_LIVE = "Nauta.d6c4cf31e1a88709b605ac8f@Nauta"
ESPN1_BACKUPS = [
    "Nauta.dac26a78f5bdf111bc9b9ffc@Nauta",  # ESPN 1 | Sur
    "Nauta.81dc69c20557da0672921475@Nauta",  # ESPN 1 | Chile
]
# Primeras bajas desde la app (2026-10-11). Las siguientes, hechas desde la app o el editor,
# se leen del layout: cualquier fila «deleted» es una decisión del usuario y no rompe pruebas.
FIRST_APP_TRASHED_NAUTA = {
    "Nauta.6186c37c4a108ec7eb171697@Nauta",  # ESPN 2 | Sur
    "Nauta.d3d2698fec772d9095f5ed4d@Nauta",  # ESPN 1 | Colombia
    "Nauta.4ad5525f8e38f0915deaa561@Nauta",  # ESPN Deportes
    "Nauta.8297a7fa0389cc7cf1d200dd@Nauta",  # ESPN 3 | Mexico
}


def current_nauta_ids():
    snapshot = json.loads((ROOT / "contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
    restorations = json.loads((ROOT / "contracts/nauta-restoration-20261008-sports.json").read_text(encoding="utf-8"))
    followup = json.loads((ROOT / "contracts/nauta-247-cleanup-20261008.json").read_text(encoding="utf-8"))
    snapshot_ids = {row["tvgId"] for row in snapshot["channels"]}
    removed = {row["tvgId"] for row in audit["channels"] if row["decision"] == "remove"}
    removed -= {row["tvgId"] for row in restorations["channels"]}
    removed |= {row["tvgId"] for row in followup["channels"]}
    return snapshot_ids - removed


@live_catalog
class NautaChannelsAreOptInTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        cls.presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        cls.nauta_ids = current_nauta_ids()
        cls.selected_nauta = {
            row["tvgId"]: row for row in cls.layout["channels"]
            if str(row.get("tvgId", "")).startswith("Nauta.")
        }

    def test_unselected_nauta_remains_opt_in_and_only_approved_rows_are_official(self):
        self.assertEqual(353, len(self.nauta_ids))
        unselected = self.nauta_ids - self.selected_nauta.keys()
        self.assertTrue(unselected.isdisjoint(row.get("tvgId") for row in self.layout["channels"]))
        self.assertTrue(unselected.issubset(self.presentation["excluded_m3u"]))
        # These are publication exclusions, not trash/tombstones: the live Nauta tab
        # checks layout.excludedM3u, so previously active unselected rows remain selectable.
        self.assertTrue(unselected.isdisjoint(self.layout["excludedM3u"]))
        self.assertTrue(unselected.isdisjoint(self.presentation["trial_m3u"]))
        APP_TRASHED_NAUTA = {key for key, row in self.selected_nauta.items() if row["state"] == "deleted"}
        self.assertTrue(FIRST_APP_TRASHED_NAUTA <= APP_TRASHED_NAUTA)
        self.assertTrue(all(row["state"] == "active" and row["sourceList"] == "1.m3u"
                            for key, row in self.selected_nauta.items()
                            if key not in APP_TRASHED_NAUTA))
        self.assertTrue(all(self.selected_nauta[key]["sourceList"] == "1.m3u"
                            for key in APP_TRASHED_NAUTA))
        official = {OFFICIAL_ESPN7, OFFICIAL_ESPN1_AR, OFFICIAL_ESPN1_MX, OFFICIAL_MTV_LIVE}
        self.assertEqual(official, {key for key, row in self.selected_nauta.items() if "trial" not in row})
        self.assertEqual(self.selected_nauta.keys() - official - APP_TRASHED_NAUTA,
                         set(self.presentation["trial_m3u"]) & self.selected_nauta.keys())
        self.assertEqual("ESPN 7", self.selected_nauta[OFFICIAL_ESPN7]["displayName"])
        self.assertEqual(37, self.selected_nauta[OFFICIAL_ESPN7]["number"])
        self.assertEqual("logos/espn-7.png", self.selected_nauta[OFFICIAL_ESPN7]["logoOverride"])
        self.assertEqual("ESPN 7", self.presentation["names"][OFFICIAL_ESPN7])
        self.assertEqual("logos/espn-7.png", self.presentation["logos"][OFFICIAL_ESPN7])
        self.assertIn(OFFICIAL_ESPN7, {c.tvg_id for c in runner.main_playlist_channels()})
        self.assertIn(("co1", "ESPN.7.HD.co"), runner.epg_source_chain(OFFICIAL_ESPN7))
        rows = self.selected_nauta
        self.assertEqual("ESPN 1 Argentina", rows[OFFICIAL_ESPN1_AR]["displayName"])
        self.assertEqual("logos/espn.svg", rows[OFFICIAL_ESPN1_AR]["logoOverride"])
        self.assertEqual(33, rows[OFFICIAL_ESPN1_AR]["number"])
        self.assertEqual("ESPN 1 MX", rows[OFFICIAL_ESPN1_MX]["displayName"])
        self.assertEqual("logos/espn.svg", rows[OFFICIAL_ESPN1_MX]["logoOverride"])
        self.assertEqual(34, rows[OFFICIAL_ESPN1_MX]["number"])
        self.assertEqual("MTV Live", rows[OFFICIAL_MTV_LIVE]["displayName"])
        self.assertEqual("logos/tvvoo/mtv-live-hd-nl.png", rows[OFFICIAL_MTV_LIVE]["logoOverride"])
        self.assertEqual(52, rows[OFFICIAL_MTV_LIVE]["number"])
        self.assertEqual(("ar1", "Canal.ESPN.(Argentina).ar"),
                         runner.EPG_PROGRAMME_SOURCES[OFFICIAL_ESPN1_AR])
        self.assertEqual(("mx1", "ESPN.MX.mx"), runner.EPG_PROGRAMME_SOURCES[OFFICIAL_ESPN1_MX])
        self.assertEqual(("us2", "MTVLIVE.us2"), runner.EPG_PROGRAMME_SOURCES[OFFICIAL_MTV_LIVE])
        self.assertIn(("ar1", "Canal.ESPN.(Argentina).ar"), runner.epg_source_chain(OFFICIAL_ESPN1_AR))
        self.assertIn(("mx1", "ESPN.MX.mx"), runner.epg_source_chain(OFFICIAL_ESPN1_MX))
        self.assertIn(("us2", "MTVLIVE.us2"), runner.epg_source_chain(OFFICIAL_MTV_LIVE))
        self.assertEqual("ESPN 1 Argentina", self.presentation["names"][OFFICIAL_ESPN1_AR])
        self.assertEqual("ESPN 1 MX", self.presentation["names"][OFFICIAL_ESPN1_MX])
        self.assertEqual("MTV Live", self.presentation["names"][OFFICIAL_MTV_LIVE])
        self.assertEqual("logos/espn.svg", self.presentation["logos"][OFFICIAL_ESPN1_AR])
        self.assertEqual("logos/espn.svg", self.presentation["logos"][OFFICIAL_ESPN1_MX])
        self.assertEqual("logos/tvvoo/mtv-live-hd-nl.png", self.presentation["logos"][OFFICIAL_MTV_LIVE])
        self.assertEqual(
            APP_TRASHED_NAUTA,
            self.selected_nauta.keys() & set(self.presentation["excluded_m3u"]),
        )
        for order in self.presentation["orders"].values():
            self.assertTrue(unselected.isdisjoint(order))
        for filename in ["channel-catalog.m3u", "m3u.m3u", "1.m3u", "m3u-externa.m3u", "2.m3u"]:
            channels = runner.parse_channels((ROOT / filename).read_text(encoding="utf-8").splitlines())
            self.assertTrue(unselected.isdisjoint(channel.tvg_id for channel in channels), filename)
        self.assertEqual((ROOT / "m3u.m3u").read_bytes(), (ROOT / "1.m3u").read_bytes())

    def test_nauta_rows_are_explicit_and_only_user_linked_rows_are_backups(self):
        nauta_rows = [row for row in self.layout["channels"] if str(row.get("tvgId", "")).startswith("Nauta.")]
        self.assertEqual(set(self.selected_nauta), {row["tvgId"] for row in nauta_rows})
        rows = {row["tvgId"]: row for row in nauta_rows}
        parent = rows[OFFICIAL_ESPN1_AR]
        self.assertEqual(ESPN1_BACKUPS, parent["backupm3u"])
        self.assertTrue(all(rows[key].get("trial") is True for key in ESPN1_BACKUPS))
        self.assertFalse(any(key in runner.EPG_PROGRAMME_SOURCES for key in ESPN1_BACKUPS))
        self.assertEqual({OFFICIAL_ESPN1_AR}, {
            row["tvgId"] for row in self.layout["channels"]
            if any(str(backup).startswith("Nauta.") for backup in row.get("backupm3u", []))
        })

    def test_runner_materializes_only_explicit_editor_rows(self):
        lines = (ROOT / "channel-catalog.m3u").read_text(encoding="utf-8").splitlines()
        before = {channel.tvg_id for channel in runner.parse_channels(lines)}
        changed = runner.apply_editor_nauta_channels(lines)
        after = {channel.tvg_id for channel in runner.parse_channels(lines)}
        self.assertEqual(bool(self.selected_nauta.keys() - before), changed)
        self.assertEqual(self.selected_nauta.keys() - before, after - before)
        self.assertTrue((self.nauta_ids - self.selected_nauta.keys()).isdisjoint(after))

    def test_existing_http_backups_are_preserved(self):
        rows = {
            row["tvgId"]: row for row in self.layout["channels"]
            if row.get("kind") == "m3u" and row.get("tvgId")
        }
        self.assertEqual(["TVN.cl@Direct38b", "TVN.cl@Direct45"], rows["0104"]["backupm3u"])

    def test_canal13_uses_official_signal_first_then_ordered_backups(self):
        rows = {
            row["tvgId"]: row for row in self.layout["channels"]
            if row.get("kind") == "m3u" and row.get("tvgId")
        }
        canal13 = rows["0107"]
        self.assertEqual("Canal 13", canal13["name"])
        self.assertEqual("active", canal13["state"])
        self.assertEqual("1.m3u", canal13["sourceList"])
        self.assertNotIn("preferredM3u", canal13)
        self.assertEqual(["Canal13.cl@Direct187", "T13EnVivo.cl@DPS"], canal13["backupm3u"])


if __name__ == "__main__":
    unittest.main()
