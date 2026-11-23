#!/usr/bin/env python3
"""Catálogo liviano para VibeM3U: data/app-layout.json (2026-11-23).

El layout del editor (data/channel-editor-layout.json) guarda también las ~16 mil filas
borradas para que el editor recuerde la papelera. La app solo necesita las filas activas y
ocultas: leer las 16 mil le costaba varios segundos en cada arranque (más en la TV), y
mientras tanto la guía y la numeración quedaban viejas. Este archivo tiene el mismo esquema,
sin las filas borradas; una fila borrada solo se conserva si su canal sigue apareciendo en
una lista publicada (así la app lo sigue escondiendo).

Uso: python scripts/build_app_layout.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "data" / "channel-editor-layout.json"
OUTPUT = ROOT / "data" / "app-layout.json"
PLAYLISTS = (ROOT / "m3u.m3u", ROOT / "m3u-externa.m3u")
IDENTITY = re.compile(r'(?:tvg-id|x-resolver-stable-id)="([^"]*)"')


def playlist_identities(paths=PLAYLISTS) -> set[str]:
    found: set[str] = set()
    for path in paths:
        if path.exists():
            found.update(value.strip() for value in IDENTITY.findall(path.read_text(encoding="utf-8")))
    found.discard("")
    return found


def row_identity(row: dict) -> str:
    return str(row.get("tvgId") if row.get("kind") == "m3u" else row.get("catalogKey") or "").strip()


def build(layout: dict, identities: set[str]) -> dict:
    channels = [
        row for row in layout.get("channels", [])
        if row.get("state") != "deleted" or row_identity(row) in identities
    ]
    return {
        "schemaVersion": layout.get("schemaVersion", 1),
        "generatedFrom": "data/channel-editor-layout.json",
        "excludedM3u": list(layout.get("excludedM3u", [])),
        "channels": channels,
    }


def render(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="falla si el archivo no está al día")
    args = parser.parse_args()
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    text = render(build(layout, playlist_identities()))
    current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if args.check:
        if current != text:
            print("data/app-layout.json no está al día", file=sys.stderr)
            return 1
        return 0
    if current != text:
        OUTPUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"app-layout.json: {len(json.loads(text)['channels'])} filas")
    else:
        print("app-layout.json sin cambios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
