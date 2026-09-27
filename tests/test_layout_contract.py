"""Contrato compartido de filas de proveedor (contracts/layout-provider-rows.json).

Los mismos casos los validan el editor (tests/layout-contract.test.mjs), la app y el
auxiliar local de VibeM3U. Para el runner una fila es válida si la acepta la validación
del layout y la de la selección que el editor publica junto a ella.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_site_data  # noqa: E402
import vibem3u_selection  # noqa: E402

CONTRACT_PATH = ROOT / "contracts" / "layout-provider-rows.json"
VIBEM3U_COPY = ROOT.parent / "VibeM3U" / "app" / "src" / "test" / "resources" / "contracts" / "layout-provider-rows.json"
SELECTION_FIELDS = (
    "provider", "catalogKey", "providerResourceId", "resolverSlug", "name", "group",
    "category", "identityState", "countryKey", "aliases",
)


def selection_channel(row: dict) -> dict:
    """Campos que buildSelectionDocument (editor-core) publica para la fila."""
    channel = {field: row[field] for field in SELECTION_FIELDS if row.get(field) not in (None, "")}
    channel["order"] = 1
    return channel


def runner_accepts(row: dict) -> tuple[bool, str]:
    layout = {"schemaVersion": 1, "excludedM3u": [], "channels": [row]}
    try:
        build_site_data.validate_layout(layout)
        vibem3u_selection._parse_row(selection_channel(row), row["provider"], "contrato")
    except ValueError as error:
        return False, str(error)
    return True, ""


class LayoutContractTest(unittest.TestCase):
    def test_runner_agrees_with_every_contract_case(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        for case in contract["cases"]:
            with self.subTest(case=case["id"]):
                accepted, reason = runner_accepts(case["row"])
                self.assertEqual(case["valid"], accepted, f"{case['why']} {reason}")

    @unittest.skipUnless(VIBEM3U_COPY.is_file(), "VibeM3U no está junto a Lista M3U")
    def test_vibem3u_copy_is_identical(self) -> None:
        self.assertEqual(
            CONTRACT_PATH.read_bytes().replace(b"\r\n", b"\n"),
            VIBEM3U_COPY.read_bytes().replace(b"\r\n", b"\n"),
            "Copia contracts/layout-provider-rows.json a VibeM3U/app/src/test/resources/contracts/",
        )


if __name__ == "__main__":
    unittest.main()
