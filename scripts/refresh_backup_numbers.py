"""Actualiza los números de los canales principales en backups.json (2026-10-24).

El emparejamiento de respaldos es por tvg-id (la clave de cada canal); el campo ``number`` es solo
de referencia para quien lee el archivo. Cuando Lista 1 se renumera, este script lo pone al día
con el número actual del catálogo y reordena por número. No toca nada más.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUPS_PATH = ROOT / "backups.json"
LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"


def refresh(backups: dict, layout: dict) -> list[str]:
    """Pone al día ``number`` de cada principal; devuelve los cambios hechos (vacío si no hubo)."""
    rows = {row.get("tvgId"): row for row in layout.get("channels", []) if row.get("tvgId")}
    changes: list[str] = []
    for key, entry in backups.get("channels", {}).items():
        row = rows.get(key)
        if row is None or not isinstance(row.get("number"), int):
            continue  # sin fila: lo informa la prueba de backups.json, no se inventa un número
        if entry.get("number") != row["number"]:
            changes.append(f"{entry.get('display_name', key)}: {entry.get('number')} → {row['number']}")
            entry["number"] = row["number"]
    if changes:
        backups["channels"] = dict(
            sorted(backups["channels"].items(), key=lambda item: item[1].get("number") or 0)
        )
        backups["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return changes


def main() -> int:
    backups = json.loads(BACKUPS_PATH.read_text(encoding="utf-8"))
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    changes = refresh(backups, layout)
    if not changes:
        print("backups.json: números al día.")
        return 0
    text = json.dumps(backups, ensure_ascii=False, indent=2) + "\n"
    BACKUPS_PATH.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    print("backups.json: números actualizados:")
    for change in changes:
        print(f"  {change}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
