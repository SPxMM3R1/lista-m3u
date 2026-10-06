import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"
SELECTION_PATH = ROOT / "data" / "vibem3u-selection.json"


def active_layout_providers(layout: dict) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"highfly": [], "tvvoo": []}
    rows = [
        row for row in layout.get("channels", [])
        if row.get("kind") == "provider" and row.get("state") == "active"
    ]
    for row in sorted(rows, key=lambda row: row.get("order", 0)):
        result.setdefault(row.get("provider"), []).append(row.get("catalogKey"))
    return result


def selected_providers(selection: dict) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"highfly": [], "tvvoo": []}
    for source in selection.get("sources", []):
        channels = sorted(source.get("channels", []), key=lambda channel: channel.get("order", 0))
        result.setdefault(source.get("provider"), []).extend(
            channel.get("catalogKey") for channel in channels
        )
    return result


class PublishedEditorialConsistencyTest(unittest.TestCase):
    """La app lee el layout y el runner lee la selección: deben declarar lo mismo.

    Un commit que edita solo uno de los dos documentos (por ejemplo, baf985e
    cambió Sky F1 a TvVoo en la selección y dejó la fila Highfly en el layout)
    deja a la app y al runner con canales de proveedor distintos.
    """

    def test_requested_118_is_permanently_removed_without_renumbering(self) -> None:
        import update_m3u as runner

        removed_id = "DSports.us@Direct38"
        layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertFalse(any(row.get("tvgId") == removed_id for row in layout["channels"]))
        # La baja conserva su identidad; la inserción posterior de France 24
        # inglés (19) desplazó el hueco del antiguo 118 al 119.
        shift = json.loads((ROOT / "contracts/channel-position-change-20261006-france24.json").read_text(encoding="utf-8"))["numberShift"]["delta"]
        self.assertFalse(any(row["state"] == "active" and row["number"] == 118 + shift
                             for row in layout["channels"]))
        self.assertIn(removed_id, layout["excludedM3u"])
        self.assertIn(removed_id, presentation["excluded_m3u"])
        following = next(row for row in layout["channels"]
                         if row.get("tvgId") == "DSports2.us@Direct187")
        # 2026-10-06: DSports 2 pasó al 38, antes de los XITE, por pedido del usuario.
        self.assertEqual((38, "active"), (following["number"], following["state"]))
        for filename in ["channel-catalog.m3u", "m3u.m3u", "1.m3u"]:
            with self.subTest(filename=filename):
                ids = {channel.tvg_id for channel in runner.parse_channels(
                    (ROOT / filename).read_text(encoding="utf-8").splitlines())}
                self.assertNotIn(removed_id, ids)
        for order in presentation["orders"].values():
            self.assertNotIn(removed_id, order)

    def test_layout_provider_rows_match_selection(self) -> None:
        layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

        self.assertEqual(active_layout_providers(layout), selected_providers(selection))

    def test_tvvoo_layout_rows_carry_country_key_of_their_identity(self) -> None:
        """La app lee el layout directo; VibeM3U <= 0.5.29 caia al arrancar
        cuando una fila TvVoo no traia countryKey y usaba `country` (texto
        visible, p. ej. "Reino Unido") como clave (incidente 98ee25a)."""
        layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))

        for row in layout.get("channels", []):
            if row.get("kind") != "provider" or row.get("provider") != "tvvoo":
                continue
            key = str(row.get("catalogKey", ""))
            with self.subTest(catalogKey=key):
                country_key, separator, alias = key.partition("|")
                self.assertTrue(separator and country_key and alias.startswith("vavoo_"))
                self.assertEqual(country_key, row.get("countryKey"))
                self.assertEqual(key, row.get("providerResourceId"))

    def test_selection_source_enabled_only_with_channels(self) -> None:
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

        for source in selection.get("sources", []):
            with self.subTest(provider=source.get("provider")):
                self.assertEqual(bool(source.get("enabled")), bool(source.get("channels")))


if __name__ == "__main__":
    unittest.main()
