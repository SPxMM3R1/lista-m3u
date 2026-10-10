import json
import unittest
from pathlib import Path

import update_m3u as runner


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_ESPN7 = "Nauta.52bb87a2e2911ed34f7ae3bc@Nauta"


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

    def test_unselected_nauta_remains_opt_in_and_only_espn7_is_official(self):
        self.assertEqual(353, len(self.nauta_ids))
        unselected = self.nauta_ids - self.selected_nauta.keys()
        self.assertTrue(unselected.isdisjoint(row.get("tvgId") for row in self.layout["channels"]))
        self.assertTrue(unselected.issubset(self.presentation["excluded_m3u"]))
        # These are publication exclusions, not trash/tombstones: the live Nauta tab
        # checks layout.excludedM3u, so previously active unselected rows remain selectable.
        self.assertTrue(unselected.isdisjoint(self.layout["excludedM3u"]))
        self.assertTrue(unselected.isdisjoint(self.presentation["trial_m3u"]))
        self.assertTrue(all(row["state"] == "active" and row["sourceList"] == "1.m3u"
                            for row in self.selected_nauta.values()))
        self.assertEqual({OFFICIAL_ESPN7}, {key for key, row in self.selected_nauta.items() if "trial" not in row})
        self.assertEqual(self.selected_nauta.keys() - {OFFICIAL_ESPN7},
                         set(self.presentation["trial_m3u"]) & self.selected_nauta.keys())
        self.assertEqual("ESPN 7", self.selected_nauta[OFFICIAL_ESPN7]["displayName"])
        self.assertEqual(37, self.selected_nauta[OFFICIAL_ESPN7]["number"])
        self.assertEqual("logos/espn-7.png", self.selected_nauta[OFFICIAL_ESPN7]["logoOverride"])
        self.assertEqual("ESPN 7", self.presentation["names"][OFFICIAL_ESPN7])
        self.assertEqual("logos/espn-7.png", self.presentation["logos"][OFFICIAL_ESPN7])
        self.assertIn(OFFICIAL_ESPN7, {c.tvg_id for c in runner.main_playlist_channels()})
        self.assertIn(("co1", "ESPN.7.HD.co"), runner.epg_source_chain(OFFICIAL_ESPN7))
        self.assertTrue(self.selected_nauta.keys().isdisjoint(self.presentation["excluded_m3u"]))
        for order in self.presentation["orders"].values():
            self.assertTrue(unselected.isdisjoint(order))
        for filename in ["channel-catalog.m3u", "m3u.m3u", "1.m3u", "m3u-externa.m3u", "2.m3u"]:
            channels = runner.parse_channels((ROOT / filename).read_text(encoding="utf-8").splitlines())
            self.assertTrue(unselected.isdisjoint(channel.tvg_id for channel in channels), filename)
        self.assertEqual((ROOT / "m3u.m3u").read_bytes(), (ROOT / "1.m3u").read_bytes())

    def test_nauta_rows_are_explicit_and_not_backup_links(self):
        nauta_rows = [row for row in self.layout["channels"] if str(row.get("tvgId", "")).startswith("Nauta.")]
        self.assertEqual(set(self.selected_nauta), {row["tvgId"] for row in nauta_rows})
        self.assertTrue(all(
            not str(backup).startswith("Nauta.")
            for row in self.layout["channels"]
            for backup in row.get("backupm3u", [])
        ))

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
        self.assertEqual(["T13EnVivo.cl@DPS"], rows["0107"]["backupm3u"])


if __name__ == "__main__":
    unittest.main()
