"""adultos.json cubre todos los canales del grupo «Adultos» (2026-10-24).

La app VibeM3U oculta los canales de adultos hasta que el usuario los desbloquea con su
clave en Opciones › Canales. La lista pública de `tvg-id` es la única fuente de esa
decisión: si una fila del grupo «Adultos» no está aquí, se vería sin clave.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"
ADULTOS_PATH = ROOT / "adultos.json"


def load():
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    adultos = json.loads(ADULTOS_PATH.read_text(encoding="utf-8"))
    return layout, adultos


class AdultosJsonTest(unittest.TestCase):
    def test_schema_and_description(self):
        _, document = load()
        self.assertEqual(1, document["schema"])
        self.assertTrue(document["description"].strip())
        self.assertIsInstance(document["channels"], list)

    def test_every_adult_row_is_covered(self):
        layout, document = load()
        listed = set(document["channels"])
        rows = [
            row
            for row in layout["channels"]
            if row.get("state") == "active" and row.get("group") == "Adultos"
        ]
        self.assertTrue(rows, "debe haber canales activos del grupo Adultos")
        missing = [row.get("tvgId") for row in rows if row.get("tvgId") not in listed]
        self.assertEqual([], missing, "canales de adultos sin entrada en adultos.json")

    def test_entries_exist_in_the_layout(self):
        layout, document = load()
        known = {row.get("tvgId") for row in layout["channels"]}
        unknown = [channel_id for channel_id in document["channels"] if channel_id not in known]
        self.assertEqual([], unknown, "adultos.json no debe inventar identidades")

    def test_list_is_unique_and_sorted(self):
        _, document = load()
        channels = document["channels"]
        self.assertEqual(len(channels), len(set(channels)))
        self.assertEqual(sorted(channels), channels)

    def test_adult_swim_is_not_hidden(self):
        _, document = load()
        self.assertFalse([item for item in document["channels"] if "adultswim" in item.lower().replace(".", "")])

    def test_the_reinstated_quality_rows_are_listed(self):
        # 2026-10-25: Brazzers TV, Venus Tv, VENUS RADIO TV y ADULTOS 1–10 al final de Lista 2.
        layout, document = load()
        listed = set(document["channels"])
        expected = {
            "PublicDirect.611041b791c77e57b0831623",
            "PublicDirect.1abf4474e1f3f29b70d71a03",
            "PublicDirect.0fdcde11e1250f52aa149c8f",
            "PublicDirect.24a6ad8c7c081886d48dab4b",
            "PublicDirect.fb685864e25513e9957f3212",
            "PublicDirect.265aa780cd512ed0698e4465",
            "PublicDirect.a0d01f76df0915446fff9f2d",
            "PublicDirect.82c1cfe1958fde3d4a7349d4",
            "PublicDirect.7403b602e798262aa32fdc10",
            "PublicDirect.c68d9bdb5131e451b513f365",
            "PublicDirect.1eeaefba050d362a9c44f878",
            "PublicDirect.08a604268e68ce7fee42eab9",
            "PublicDirect.6ab9b36bf0cf09082ad54017",
        }
        self.assertEqual(set(), expected - listed)
        by_id = {row.get("tvgId"): row for row in layout["channels"]}
        for channel_id in sorted(expected):
            row = by_id[channel_id]
            self.assertEqual("active", row["state"])
            self.assertEqual("2.m3u", row["sourceList"])
            self.assertEqual("Adultos", row["group"])


if __name__ == "__main__":
    unittest.main()
