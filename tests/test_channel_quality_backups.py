import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _editorial_name(value):
    return re.sub(r"\s*\[Nauta\]\s*$", "", str(value or ""), flags=re.IGNORECASE).strip()


def _adjacent_base_hd_pairs(rows):
    by_number = {row["number"]: row for row in rows}
    pairs = []
    for base in rows:
        hd = by_number.get(base["number"] + 1)
        if hd is None:
            continue
        base_name = _editorial_name(base["name"])
        hd_name = _editorial_name(hd["name"])
        if not re.search(r"\s+HD$", hd_name, flags=re.IGNORECASE):
            continue
        name_without_hd = re.sub(r"\s+HD$", "", hd_name, flags=re.IGNORECASE).strip()
        if base_name.casefold() == name_without_hd.casefold():
            pairs.append((base, hd))
    return pairs


class ChannelQualityBackupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        cls.presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        cls.active_list1 = [
            row for row in cls.layout["channels"]
            if row.get("kind") == "m3u"
            and row.get("sourceList") == "1.m3u"
            and row.get("state") == "active"
        ]
        cls.pairs = _adjacent_base_hd_pairs(cls.active_list1)

    def test_every_adjacent_base_hd_pair_is_a_hd_backup(self):
        self.assertEqual(55, len(self.pairs))
        for base, hd in self.pairs:
            with self.subTest(base=base["number"], primary=hd["number"], name=hd["name"]):
                self.assertTrue(base["tvgId"].startswith("Nauta."))
                self.assertTrue(hd["tvgId"].startswith("Nauta."))
                self.assertTrue(base.get("trial"))
                self.assertTrue(hd.get("trial"))
                self.assertEqual([base["tvgId"]], hd.get("backupm3u"))

    def test_base_rows_are_owned_once_and_stay_published_for_resolution(self):
        owners = {}
        for row in self.active_list1:
            for backup_id in row.get("backupm3u", []):
                owners.setdefault(backup_id, []).append(row["tvgId"])

        orders = self.presentation["orders"]
        catalog_order = orders["channel-catalog.m3u"]
        trial_ids = set(self.presentation["trial_m3u"])
        excluded_ids = set(self.layout["excludedM3u"]) | set(self.presentation["excluded_m3u"])
        for base, hd in self.pairs:
            with self.subTest(base=base["number"], primary=hd["number"]):
                self.assertEqual([hd["tvgId"]], owners.get(base["tvgId"]))
                self.assertIn(base["tvgId"], trial_ids)
                self.assertIn(hd["tvgId"], trial_ids)
                self.assertNotIn(base["tvgId"], excluded_ids)
                self.assertNotIn(hd["tvgId"], excluded_ids)
                self.assertIn(base["tvgId"], orders["m3u.m3u"])
                self.assertIn(hd["tvgId"], orders["m3u.m3u"])
                self.assertIn(base["tvgId"], orders["1.m3u"])
                self.assertIn(hd["tvgId"], orders["1.m3u"])
                self.assertIn(base["tvgId"], catalog_order)
                self.assertIn(hd["tvgId"], catalog_order)

if __name__ == "__main__":
    unittest.main()
