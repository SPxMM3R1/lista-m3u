"""Base aprobada del catálogo y bajas posteriores del usuario (app o editor).

Las pruebas del catálogo comparaban hashes fijos; cada envío a la papelera los rompía
(setRowState también reordena `order`). Ahora se compara contra la base aprobada
descontando solo las filas que el usuario pasó a «deleted» después de ella.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "contracts/editorial-baseline-20261012.json").read_text(encoding="utf-8"))


def row_key(row):
    if row.get("kind") == "provider":
        return f'provider:{row["provider"]}:{row["catalogKey"]}'
    return f'm3u:{row["tvgId"]}'


def user_trashed_rows(layout):
    """Filas activas u ocultas en la base que hoy están en la papelera."""
    before = {row_key(row): row["state"] for row in BASELINE["layout"]["channels"]}
    return {row_key(row) for row in layout["channels"]
            if row["state"] == "deleted" and before.get(row_key(row), "deleted") != "deleted"}


def user_trashed_ids(layout):
    return {key.removeprefix("m3u:") for key in user_trashed_rows(layout) if key.startswith("m3u:")}


def _without_rows(rows, trashed, key=row_key):
    kept = [dict(row) for row in rows if key(row) not in trashed]
    kept.sort(key=lambda row: row.get("order", 0))
    for rank, row in enumerate(kept, 1):
        row["order"] = rank  # Solo importa el orden relativo; la papelera lo recalcula.
    return kept


def layout_without_trash(layout, trashed):
    current = dict(layout)
    current["channels"] = _without_rows(layout["channels"], trashed)
    ids = {key.removeprefix("m3u:") for key in trashed}
    current["excludedM3u"] = sorted(set(layout.get("excludedM3u", [])) - ids)
    return current


def selection_without_trash(selection, trashed):
    current = {k: v for k, v in selection.items() if k not in {"selectionSignature", "publishedAt"}}
    current["sources"] = [
        {**source, "channels": _without_rows(
            source.get("channels", []), trashed,
            key=lambda row: f'provider:{row["provider"]}:{row["catalogKey"]}')}
        for source in selection.get("sources", [])
    ]
    return current


def presentation_without_trash(presentation, trashed_ids):
    def strip(value):
        if isinstance(value, list):
            return [strip(v) for v in value if not (isinstance(v, str) and v in trashed_ids)]
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in trashed_ids}
        return value
    return strip(presentation)
