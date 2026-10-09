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


class NautaChannelsRemainIndependentTest(unittest.TestCase):
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
        cls.nauta_rows = [
            row for row in cls.active_list1 if row.get("tvgId", "").startswith("Nauta.")
        ]
        cls.pairs = _adjacent_base_hd_pairs(cls.active_list1)

    def test_adjacent_base_and_hd_rows_stay_independent(self):
        self.assertEqual(55, len(self.pairs))
        presentation = self.presentation
        trial_ids = set(presentation["trial_m3u"])
        excluded_ids = set(self.layout["excludedM3u"]) | set(presentation["excluded_m3u"])
        for base, hd in self.pairs:
            with self.subTest(base=base["number"], primary=hd["number"], name=hd["name"]):
                self.assertTrue(base["tvgId"].startswith("Nauta."))
                self.assertTrue(hd["tvgId"].startswith("Nauta."))
                self.assertTrue(base.get("trial"))
                self.assertTrue(hd.get("trial"))
                self.assertNotIn("backupm3u", hd)
                self.assertIn(base["tvgId"], trial_ids)
                self.assertIn(hd["tvgId"], trial_ids)
                self.assertNotIn(base["tvgId"], excluded_ids)
                self.assertNotIn(hd["tvgId"], excluded_ids)
                for key in ("m3u.m3u", "1.m3u", "channel-catalog.m3u"):
                    self.assertIn(base["tvgId"], presentation["orders"][key])
                    self.assertIn(hd["tvgId"], presentation["orders"][key])

    def test_no_nauta_row_declares_an_m3u_backup(self):
        self.assertEqual(353, len(self.nauta_rows))
        self.assertTrue(all(not row.get("backupm3u") for row in self.nauta_rows))

    def test_existing_http_backups_are_preserved(self):
        rows = {
            row["tvgId"]: row for row in self.layout["channels"]
            if row.get("kind") == "m3u" and row.get("tvgId")
        }
        self.assertEqual(["TVN.cl@Direct38b", "TVN.cl@Direct45"], rows["0104"]["backupm3u"])
        self.assertEqual(["T13EnVivo.cl@DPS"], rows["0107"]["backupm3u"])


if __name__ == "__main__":
    unittest.main()
