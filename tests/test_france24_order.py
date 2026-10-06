"""Cambio editorial: France 24 inglés existente va después del español."""
import json
from pathlib import Path
import unittest

import update_m3u as runner

ROOT = Path(__file__).resolve().parents[1]
ES, EN = "France24.fr", "France24.fr@English"


class France24OrderTests(unittest.TestCase):
    def test_existing_english_row_is_adjacent_without_duplicate_or_officialization(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = sorted((r for r in layout["channels"] if r["state"] == "active"), key=lambda r: r["order"])
        spanish = next(r for r in rows if r.get("tvgId") == ES)
        english = next(r for r in rows if r.get("tvgId") == EN)
        self.assertEqual(1, sum(r.get("tvgId") == EN for r in layout["channels"]))
        self.assertEqual((18, 19), (spanish["number"], english["number"]))
        self.assertEqual(english, rows[rows.index(spanish) + 1])
        self.assertEqual("1.m3u", english["sourceList"])
        self.assertIs(True, english["trial"])
        self.assertEqual("logos/france24.svg", english["logoPath"])
        self.assertNotIn(EN, layout["excludedM3u"])

    def test_order_is_durable_in_inventory_and_both_list1_aliases(self):
        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        for name in ("channel-catalog.m3u", "m3u.m3u", "1.m3u"):
            with self.subTest(name=name):
                channels = runner.parse_channels((ROOT / name).read_text(encoding="utf-8").splitlines())
                ids = [c.tvg_id for c in channels]
                self.assertEqual(EN, ids[ids.index(ES) + 1])
                desired = presentation["orders"][name]
                self.assertEqual(EN, desired[desired.index(ES) + 1])
                self.assertEqual(1, ids.count(EN))
                self.assertEqual("https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_5000.m3u8",
                                 next(c.url for c in channels if c.tvg_id == EN))
        self.assertEqual((ROOT / "m3u.m3u").read_bytes(), (ROOT / "1.m3u").read_bytes())
        self.assertIn(EN, presentation["trial_m3u"])
        self.assertNotIn(EN, {c.tvg_id for c in runner.main_playlist_channels()})

    def test_recorded_number_changes_match_without_rewriting_historical_removals(self):
        manifest = json.loads((ROOT / "contracts/channel-position-change-20261006-france24.json").read_text(encoding="utf-8"))
        self.assertEqual((EN, ES, 62, 19),
                         (manifest["movedId"], manifest["afterId"], manifest["fromNumber"], manifest["toNumber"]))
        self.assertEqual({"fromInclusive": 19, "delta": 1}, manifest["numberShift"])
        self.assertTrue(manifest["preserveTrial"])
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        by_key = {f'provider:{r["provider"]}:{r["catalogKey"]}' if r["kind"] == "provider"
                  else f'm3u:{r["tvgId"]}': r for r in layout["channels"]}
        for change in manifest["changes"]:
            row = by_key[change["key"]]
            self.assertEqual(change["to"], row["number"])
            self.assertEqual("active", row["state"])
            self.assertEqual(19 if change["key"] == f"m3u:{EN}" else change["from"] + 1, change["to"])
        removed = json.loads((ROOT / "contracts/channel-number-exclusions-20261006-t13.json").read_text(encoding="utf-8"))
        self.assertEqual(217, removed["backup"]["backupNumber"])


if __name__ == "__main__":
    unittest.main()
