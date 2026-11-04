"""Orden de Lista 2: primero los canales con respaldos y después el resto, cada bloque A–Z (2026-11-03)."""
import json
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data/channel-editor-layout.json"


class Lista2OrderTest(unittest.TestCase):
    def test_lista2_has_backed_up_channels_first_then_the_rest_alphabetically(self):
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
        with_backups = set(json.loads((ROOT / "backups.json").read_bytes().decode("utf-8"))["channels"])
        # Dentro de un mismo nombre, la de más calidad medida primero (2026-10-31); sin medir al final.
        measured = {
            item["tvg_id"]: item
            for item in json.loads((ROOT / "contracts/bitrate-lista2-20261031.json").read_text(encoding="utf-8"))
            if item.get("ok") and item.get("height")
        }

        def fold(text):
            text = unicodedata.normalize("NFD", str(text or ""))
            return "".join(char for char in text if not unicodedata.combining(char)).casefold().lstrip("@#*-_. ")

        def rank(row):
            item = measured.get(row.get("tvgId"))
            quality = (1, 0, 0, 0) if item is None else (
                0, -item["height"], -(item.get("width") or 0), -(item.get("kbps") or 0))
            return (0 if row.get("tvgId") in with_backups else 1, fold(row.get("displayName") or row.get("name")),
                    quality, str(row.get("tvgId")))

        # Pedido del usuario (2026-11-03: «Pon primero los con backup, despues lo otro. Todo en orden
        # alfabetico»): reemplaza el orden por categoría del 2026-11-01. Un canal que gana o pierde
        # respaldos cambia de bloque: hay que reordenar (outputs/lista2-orden-respaldos-20261103/order.py).
        ranks = [rank(row) for row in block]
        self.assertEqual(ranks, sorted(ranks))


if __name__ == "__main__":
    unittest.main()
