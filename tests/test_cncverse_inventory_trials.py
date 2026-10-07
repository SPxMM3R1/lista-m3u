import hashlib
import json
import unittest
from pathlib import Path

import update_m3u as runner

ROOT = Path(__file__).resolve().parents[1]


class CncVerseInventoryTrialsTest(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((ROOT / "contracts/cncverse-inventory-trials-20261007.json").read_text(encoding="utf-8"))
        self.layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        self.presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))

    def test_existing_editorial_rows_are_byte_equivalent_including_numbers_and_backups(self):
        by_key = {(("provider:" + row["provider"] + ":" + row["catalogKey"])
                   if row["kind"] == "provider" else "m3u:" + row["tvgId"]): row
                  for row in self.layout["channels"]}
        for before in self.request["baselineRows"]:
            row = by_key[before["key"]]
            payload = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.assertEqual(before["sha256"], hashlib.sha256(payload).hexdigest(), before["key"])

    def test_new_trials_are_an_exact_unique_tail_with_consecutive_new_numbers(self):
        added = self.request["addedChannels"]
        self.assertGreater(len(added), 0)
        self.assertEqual(self.request["addedCount"], len(added))
        self.assertEqual(len(added), len({spec["tvgId"] for spec in added}))
        self.assertEqual(list(range(219, 219 + len(added))), [spec["number"] for spec in added])
        active = sorted((row for row in self.layout["channels"] if row["state"] == "active"), key=lambda row: row["order"])
        self.assertEqual([spec["tvgId"] for spec in added], [row["tvgId"] for row in active[-len(added):]])
        for row in active[-len(added):]:
            self.assertEqual(("m3u", "1.m3u", True), (row["kind"], row["sourceList"], row["trial"]))
        self.assertEqual((ROOT / "1.m3u").read_bytes(), (ROOT / "m3u.m3u").read_bytes())

    def test_all_known_chile_entries_are_unique_exact_locators_not_new_provider_ids(self):
        specs = [spec for spec in self.request["activeChannels"] if spec["catalog"] == "chiletv"]
        self.assertEqual(236, self.request["knownChileEntries"])
        self.assertEqual(236, len(specs))
        self.assertEqual(236, len({spec["group"] for spec in specs}))
        self.assertTrue(all(spec["label"] == "auto" for spec in specs))

    def test_new_trials_have_no_epg_even_if_an_old_guide_or_name_could_match(self):
        ids = {spec["tvgId"] for spec in self.request["activeChannels"]}
        self.assertTrue(ids <= runner.trial_m3u_ids())
        official = {channel.tvg_id for channel in runner.main_playlist_channels()}
        extras = {channel.tvg_id for channel in runner.epg_scope_extra_channels(official)}
        self.assertFalse(ids & (official | extras))
        self.assertFalse(ids & set(runner.EPG_PROGRAMME_SOURCES))

    def test_restoration_is_explicit_and_unrelated_exclusions_remain(self):
        restored = set(self.request["reintroducedIds"])
        added = {spec["tvgId"] for spec in self.request["addedChannels"]}
        self.assertTrue(restored <= added)
        self.assertTrue(all(channel_id.endswith("@CNCVerse") for channel_id in restored))
        self.assertFalse(restored & set(self.layout["excludedM3u"]))
        self.assertFalse(restored & set(self.presentation["excluded_m3u"]))
        self.assertIn("DSports.us@Direct38", self.layout["excludedM3u"])

    def test_no_donation_ambiguous_group_or_session_material_was_adopted(self):
        specs = self.request["activeChannels"]
        self.assertTrue(all(spec["group"] != "Sky Sports" for spec in specs))
        text = json.dumps(specs).lower()
        for forbidden in ["click to donate", "token=", "https://", "clearkey", "/proxy/"]:
            self.assertNotIn(forbidden, text)
        for spec in specs:
            locator = f'{spec["catalog"]}|{spec["group"]}|{spec["label"]}'
            from urllib.parse import quote
            self.assertEqual(locator, runner.cncverse_reference_id("vibem3u://resolver/cncverse/" + quote(locator, safe="")))


if __name__ == "__main__":
    unittest.main()
