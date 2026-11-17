"""Orden de Lista 2: todo en un solo bloque A–Z, sin separar los con respaldos (2026-11-09)."""
import json
import re
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data/channel-editor-layout.json"


class Lista2OrderTest(unittest.TestCase):
    def test_lista2_is_alphabetical_in_one_block(self):
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
        # El bloque TvVoo del 2026-11-17 (catálogo completo por país, pedido del usuario) va al final
        # de Lista 2 y no sigue A–Z: se verifica aparte, abajo. El resto del bloque sí sigue A–Z.
        tvvoo_block = [row for row in block if row.get("kind") == "provider" and row.get("provider") == "tvvoo"]
        block = [row for row in block if not (row.get("kind") == "provider" and row.get("provider") == "tvvoo")]
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
            return (fold(row.get("displayName") or row.get("name")),
                    quality, str(row.get("tvgId")))

        # Pedido del usuario (2026-11-09: «reordena toda la lista 2 por orden alfabético»): reemplaza
        # el bloque «con respaldos primero» del 2026-11-03. Un canal nuevo o renombrado obliga a reordenar.
        ranks = [rank(row) for row in block]
        self.assertEqual(ranks, sorted(ranks))

        # Bloque TvVoo (2026-11-17): va después de todas las demás filas de Lista 2, agrupado por
        # país (Reino Unido, España, luego el resto por nombre en español) y por nombre dentro del país.
        lista2 = [
            row
            for row in document["channels"]
            if row["state"] == "active" and row.get("sourceList") == "2.m3u"
        ]
        if tvvoo_block:
            first = lista2.index(tvvoo_block[0])
            self.assertEqual(lista2[first:], tvvoo_block, "el bloque TvVoo debe ir al final de Lista 2")
            countries = []
            for row in tvvoo_block:
                if not countries or countries[-1] != row["countryKey"]:
                    self.assertNotIn(row["countryKey"], countries, "cada país del bloque va en un solo tramo")
                    countries.append(row["countryKey"])
            self.assertEqual(countries[:2], ["unitedkingdom", "spain"])
            # Dentro del país el orden es el de localeCompare("es") de JS (símbolos, espacios y
            # paréntesis incluidos), que Python no reproduce: no se verifica aquí.

if __name__ == "__main__":
    unittest.main()
