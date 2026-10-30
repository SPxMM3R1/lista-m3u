"""Referencias tokenless M6Foot y las 19 filas editoriales de Lista 2 (2026-10-18)."""
from fractions import Fraction
import json
import re
import unittest
import unicodedata
from pathlib import Path

import catalog_approval
import m6foot_reference
import update_m3u

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data/channel-editor-layout.json"
CATALOG_PATH = ROOT / "channel-catalog.m3u"
EXTERNAL_PATH = ROOT / "m3u-externa.m3u"

EXPECTED = {
    "49": "Movistar LaLiga ES",
    "71": "ESPN Deportes",
    "75": "TNT Sports Premium",
    "76": "ESPN Premium",
    "77": "TyC Sports",
    "78": "Fox Sports ARG",
    "79": "Fox Sport 2 ARG",
    "80": "Fox Sports 3 ARG",
    "87": "ESPN ARG",
    "88": "ESPN 2 ARG",
    "89": "ESPN 3",
    "90": "ESPN 4",
    "91": "ESPN 5",
    "92": "ESPN 6",
    "93": "ESPN 7",
    "94": "DirecTV Sports",
    "95": "DirecTV Sports 2",
    "96": "DirecTV Sports Plus",
    "106": "TUDN",
}

# La papelera desde la app retira filas M6Foot con el tiempo (ESPN Deportes, ESPN ARG, ESPN 7, TUDN…):
# una fila `deleted` es una baja editorial válida; las activas deben cumplir el contrato completo.


def layout():
    return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))


def sort_key(row):
    name = str(row.get("displayName") or row.get("name") or "")
    folded = unicodedata.normalize("NFD", name)
    folded = "".join(character for character in folded if not unicodedata.combining(character)).casefold()
    return (re.sub(r"^[^a-z0-9]+", "", folded), str(row.get("tvgId") or row.get("catalogKey") or ""))


class M6FootReferenceTest(unittest.TestCase):
    def test_reference_roundtrip_is_tokenless(self):
        for player_id in EXPECTED:
            url = m6foot_reference.reference(player_id)
            self.assertEqual("vibem3u://resolver/m6foot/" + player_id, url)
            self.assertEqual(player_id, m6foot_reference.parse_reference(url))
            self.assertEqual("M6Foot." + player_id + "@M6Foot", m6foot_reference.channel_id(player_id))
            for secret in (".m3u8", "http://", "https://", "token=", "?s="):
                self.assertNotIn(secret, url)

    def test_reference_rejects_non_player_ids(self):
        for bad in (
            "vibem3u://resolver/m6foot/abc",
            "vibem3u://resolver/m6foot/",
            "vibem3u://resolver/m6foot/12?token=x",
            "vibem3u://resolver/nauta/12",
            "vibem3u://user@resolver/m6foot/12",
            "https://m6foot.click/player/3/90",
        ):
            self.assertIsNone(m6foot_reference.parse_reference(bad))

    def test_catalog_has_the_m6foot_provider(self):
        catalog = update_m3u.validate_resolver_catalog()
        provider = next((item for item in catalog["providers"] if item["id"] == "m6foot"), None)
        self.assertIsNotNone(provider)
        self.assertEqual("m6foot", provider["engine"])
        self.assertEqual(["@M6Foot"], provider["match"]["tvgIdSuffixes"])
        self.assertEqual(
            {
                "pageBase": "https://m6foot.click/player/3/",
                "embedBase": "https://navytitle.net/embed/",
                "embedReferer": "https://navytitle.net/",
            },
            provider["config"],
        )

    def test_playlist_contract_accepts_the_tokenless_rows(self):
        lines = CATALOG_PATH.read_text(encoding="utf-8-sig").splitlines()
        counts = update_m3u.validate_playlist_resolvers(lines)
        self.assertEqual(len(EXPECTED), counts["m6foot"])
        tampered = list(lines)
        for index, line in enumerate(tampered):
            if 'tvg-id="M6Foot.90@M6Foot"' in line:
                tampered[index] = line.replace("M6Foot.90@M6Foot", "M6Foot.91@M6Foot")
                break
        with self.assertRaises(ValueError):
            update_m3u.validate_playlist_resolvers(tampered)

    def test_layout_rows_are_trial_list2_and_sorted(self):
        document = layout()
        rows = [row for row in document["channels"] if str(row.get("tvgId", "")).startswith("M6Foot.")]
        self.assertEqual(len(EXPECTED), len(rows))
        ids = set()
        numbers = set()
        for row in rows:
            player_id = row["tvgId"].removeprefix("M6Foot.").removesuffix("@M6Foot")
            self.assertIn(player_id, EXPECTED)
            self.assertEqual(EXPECTED[player_id], row["name"])
            self.assertEqual("2.m3u", row["sourceList"])
            self.assertEqual("Deportes", row["group"])
            self.assertIn(row["state"], ("active", "deleted"))
            if row["state"] == "active":
                self.assertIs(True, row["trial"])
                numbers.add(row["number"])
            ids.add(row["tvgId"])
        self.assertEqual(len(EXPECTED), len(ids))
        self.assertEqual(sum(1 for row in rows if row["state"] == "active"), len(numbers))
        self.assertEqual(document["channels"], sorted(document["channels"], key=lambda row: row["order"]))
        # Los respaldos de otro canal no se ven en la app y van al final (normalizeLists,
        # 2026-10-19): el orden alfabético es el de los canales visibles.
        linked = {
            target
            for row in document["channels"]
            if row["state"] == "active"
            for target in list(row.get("backupm3u", [])) + ([row["preferredM3u"]] if row.get("preferredM3u") else [])
        }
        # 2026-10-25: los canales de adultos van al final de Lista 2 por pedido explícito del
        # usuario («agregar al final de Lista 2 los canales de adultos»), fuera del orden por
        # bitrate. Se validan aparte, más abajo.
        # 2026-10-28, pedido del usuario: lo que volvió de la papelera y abría va en un bloque
        # propio al final de Lista 2 (después de Nauta y M6Foot), con la misma regla de orden y
        # sus medidas en contracts/papelera-recuperados-20261028.json. Los adultos recuperados
        # van dentro de ese bloque (desde 2026-10-26 Lista 2 ya no cierra con adultos).
        recovered_measures = {
            item["tvg_id"]: item
            for item in json.loads((ROOT / "contracts/papelera-recuperados-20261028.json").read_text(encoding="utf-8"))
        }
        adults = [
            row
            for row in document["channels"]
            if row["state"] == "active" and row.get("sourceList") == "2.m3u"
            and row.get("tvgId") not in linked and row.get("group") == "Adultos"
            and row.get("tvgId") not in recovered_measures
        ]
        block = [
            row
            for row in document["channels"]
            if row["state"] == "active" and row.get("sourceList") == "2.m3u"
            and row.get("tvgId") not in linked and row not in adults
        ]
        # 2026-10-25, pedido del usuario: primero se agrupan por nombre (A–Z); dentro de cada nombre,
        # resolución, luego fps, luego bitrate medido y luego el nombre. Los sin medir van al final
        # de su nombre. Nauta y M6Foot van después.
        # 2026-10-29, pedido del usuario («Vuelve a reordenar la lista 2 completa. Por nombre y
        # calidad»): medición nueva de todo Lista 2 (contracts/bitrate-lista2-20261029.json) y un
        # solo orden; el bloque de recuperados de la papelera se mezcla con el principal.
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
            fps_text = str(item.get("fps") or "0")
            fps = 0.0 if fps_text.endswith("/0") else float(Fraction(fps_text))
            # El bitrate se redondea a múltiplos de 500 kbps: pequeñas variaciones de medición no mueven el orden.
            return (name_of(row), 0, -item["height"], -(item.get("width") or 0), -fps, -round((item.get("kbps") or 0) / 500))

        main_block = [
            row for row in block
            if not str(row.get("tvgId", "")).startswith(("Nauta.", "M6Foot."))
        ]
        ranks = [rank(row) for row in main_block]
        self.assertEqual(ranks, sorted(ranks))
        last_main = max(row["order"] for row in main_block)
        last_special = last_main
        for row in block:
            if str(row.get("tvgId", "")).startswith(("Nauta.", "M6Foot.")):
                self.assertGreater(row["order"], last_main)
                last_special = max(last_special, row["order"])
        # Los adultos cierran Lista 2: ninguna fila no-adulto puede quedar después de ellos.
        if adults:
            last_adult = max(row["order"] for row in adults)
            self.assertTrue(
                all(row["order"] < last_adult for row in block),
                "los canales de adultos deben ir al final de Lista 2",
            )
            self.assertEqual(adults, sorted(adults, key=lambda row: row["order"]))

    def test_layout_is_sealed_and_rows_reach_lista_2(self):
        document = layout()
        self.assertTrue(catalog_approval.approved_by_user(document))
        catalog_ids = set(re.findall(r'tvg-id="([^"]+)"', CATALOG_PATH.read_text(encoding="utf-8-sig")))
        external_ids = set(re.findall(r'tvg-id="([^"]+)"', EXTERNAL_PATH.read_text(encoding="utf-8-sig")))
        states = {row.get("tvgId"): row.get("state") for row in document["channels"]}
        for player_id in EXPECTED:
            channel_id = m6foot_reference.channel_id(player_id)
            self.assertIn(channel_id, catalog_ids)
            if states.get(channel_id) == "active":
                self.assertIn(channel_id, external_ids)
            else:
                self.assertNotIn(channel_id, external_ids)

    def test_no_signed_url_or_provider_host_reaches_the_repository(self):
        for path in (CATALOG_PATH, EXTERNAL_PATH, ROOT / "m3u.m3u", LAYOUT_PATH, ROOT / "presentation-overrides.json"):
            text = path.read_text(encoding="utf-8-sig")
            for forbidden in ("m6foot.click", "navytitle", "?s=", "&s=", "?t=", "&t="):
                self.assertNotIn(forbidden, text, path.name)


if __name__ == "__main__":
    unittest.main()
