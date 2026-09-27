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

    def test_layout_provider_rows_match_selection(self) -> None:
        layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

        self.assertEqual(active_layout_providers(layout), selected_providers(selection))

    def test_selection_source_enabled_only_with_channels(self) -> None:
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

        for source in selection.get("sources", []):
            with self.subTest(provider=source.get("provider")):
                self.assertEqual(bool(source.get("enabled")), bool(source.get("channels")))


if __name__ == "__main__":
    unittest.main()
