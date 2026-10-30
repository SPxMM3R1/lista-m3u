"""backups.json (2026-10-24): respaldos de canales de Lista 1, legibles y coherentes con el catálogo."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BackupsJsonTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT / "backups.json").read_text(encoding="utf-8"))
        layout = json.loads((ROOT / "data" / "channel-editor-layout.json").read_text(encoding="utf-8"))
        self.rows = {row.get("tvgId"): row for row in layout["channels"] if row.get("tvgId")}

    def test_every_principal_is_an_active_list_one_channel(self):
        for key, entry in self.doc["channels"].items():
            with self.subTest(channel=entry["display_name"]):
                row = self.rows.get(key)
                self.assertIsNotNone(row, "el canal principal no está en el catálogo")
                self.assertEqual("1.m3u", row.get("sourceList"))
                # Un principal mandado a la papelera desde la app (FX, 2026-10-30) conserva su
                # registro de respaldos por si se recupera.
                self.assertIn(row.get("state"), {"active", "hidden", "deleted"})

    def test_every_copy_is_out_of_the_lists_and_fully_described(self):
        app_fields = {"tvg_id", "display_name", "url", "group"}
        seen = set()
        for entry in self.doc["channels"].values():
            for copy in entry["backups"]:
                with self.subTest(copy=copy.get("tvg_id")):
                    self.assertTrue(app_fields <= copy.keys(), "faltan campos que lee la app")
                    self.assertTrue({"source_name", "from_list", "from_number"} <= copy.keys())
                    self.assertTrue(copy["url"].startswith(("http://", "https://")))
                    self.assertNotIn(copy["tvg_id"], seen, "copia repetida")
                    seen.add(copy["tvg_id"])
                    self.assertEqual("deleted", self.rows[copy["tvg_id"]].get("state"),
                                     "una copia de respaldo sigue publicada en la lista")


if __name__ == "__main__":
    unittest.main()
