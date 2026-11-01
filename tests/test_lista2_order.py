"""Orden de Lista 2 por nombre, resolución y bitrate (2026-10-31)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data/channel-editor-layout.json"


class Lista2OrderTest(unittest.TestCase):
    def test_lista2_is_sorted_by_name_and_quality(self):
        document = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(document["channels"], sorted(document["channels"], key=lambda row: row["order"]))
        # Los respaldos de otro canal no se ven en la app y van al final (normalizeLists).
        linked = {
            target
            for row in document["channels"]
            if row["state"] == "active"
            for target in list(row.get("backupm3u", [])) + ([row["preferredM3u"]] if row.get("preferredM3u") else [])
        }
        block = [
            row
            for row in document["channels"]
            if row["state"] == "active" and row.get("sourceList") == "2.m3u" and row.get("tvgId") not in linked
        ]
        # Pedido del usuario (2026-10-31: «Vuelve a reordenar la lista 2 con primero nombre, segundo
        # resolución, y tercero el bitrate… que el primer canal siempre sea el de mejor calidad»):
        # nombre A–Z y, dentro de cada nombre, resolución y bitrate medidos con la variante HLS mayor
        # (contracts/bitrate-lista2-20261031.json). Los sin medir van al final de su nombre.
        measured = {
            item["tvg_id"]: item
            for item in json.loads((ROOT / "contracts/bitrate-lista2-20261031.json").read_text(encoding="utf-8"))
            if item.get("ok") and item.get("height")
        }

        def name_of(row):
            return str(row.get("displayName") or row.get("name") or "").strip().lower()

        def rank(row):
            item = measured.get(row.get("tvgId"))
            if item is None:
                return (name_of(row), 1, 0, 0, 0)
            # Bitrate exacto (sin redondear): el primero de cada nombre es siempre el de más calidad medida.
            return (name_of(row), 0, -item["height"], -(item.get("width") or 0), -(item.get("kbps") or 0))

        ranks = [rank(row) for row in block]
        self.assertEqual(ranks, sorted(ranks))


if __name__ == "__main__":
    unittest.main()
