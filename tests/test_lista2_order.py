"""Orden de Lista 2 por nombre y calidad (2026-10-29)."""
from fractions import Fraction
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
        # Pedido del usuario (2026-10-25, repetido el 2026-10-29: «Vuelve a reordenar la lista 2
        # completa. Por nombre y calidad»): nombre A–Z y, dentro de cada nombre, resolución, fps y
        # bitrate medido (contracts/bitrate-lista2-20261029.json). Los sin medir van al final de su nombre.
        measured = {
            item["tvg_id"]: item
            for item in json.loads((ROOT / "contracts/bitrate-lista2-20261029.json").read_text(encoding="utf-8"))
            if item.get("ok") and item.get("height")
        }

        def name_of(row):
            return str(row.get("displayName") or row.get("name") or "").strip().lower()

        def rank(row):
            item = measured.get(row.get("tvgId"))
            if item is None:
                return (name_of(row), 1, 0, 0, 0, 0)
            # Algunas señales informan «0/0» fps: cuentan como 0.
            fps_text = str(item.get("fps") or "0")
            fps = 0.0 if fps_text.endswith("/0") else float(Fraction(fps_text))
            # El bitrate se redondea a múltiplos de 500 kbps: pequeñas variaciones de medición no mueven el orden.
            return (name_of(row), 0, -item["height"], -(item.get("width") or 0), -fps, -round((item.get("kbps") or 0) / 500))

        ranks = [rank(row) for row in block]
        self.assertEqual(ranks, sorted(ranks))


if __name__ == "__main__":
    unittest.main()
