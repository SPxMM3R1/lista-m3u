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
        # 2026-10-26: Brazzers TV pasó a Lista 1 y, por pedido del usuario, todo lo que quedaba
        # de «Adultos» después de él en Lista 2 pasó a la papelera. Ninguna fila de Lista 2 con
        # grupo «Adultos» debe seguir activa. Excepción (2026-10-28, pedido del usuario): los que
        # volvieron de la papelera porque abrían («los canales que borré a propósito, también
        # devuélvelos»), registrados en contracts/papelera-recuperados-20261028.json.
        layout, _ = load()
        recovered = {
            item["tvg_id"]
            for item in json.loads((ROOT / "contracts/papelera-recuperados-20261028.json").read_text(encoding="utf-8"))
        }
        leftovers = [
            row["tvgId"] for row in layout["channels"]
            if row.get("state") == "active" and row.get("sourceList") == "2.m3u" and row.get("group") == "Adultos"
            and row["tvgId"] not in recovered
        ]
        self.assertEqual([], leftovers)
        brazzers = next(row for row in layout["channels"] if row.get("tvgId") == "PublicDirect.611041b791c77e57b0831623")
        self.assertEqual(("active", "1.m3u", "Adultos"), (brazzers["state"], brazzers["sourceList"], brazzers["group"]))

if __name__ == "__main__":
    unittest.main()
