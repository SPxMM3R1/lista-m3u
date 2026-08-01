#!/usr/bin/env python3
"""Refresh only the optional sports block without touching EPG or TVN."""

from __future__ import annotations

import json
import os
from pathlib import Path

from update_m3u import (
    DEFAULT_PLAYLIST,
    LEGACY_PLAYLIST,
    sports_feature_enabled,
    sync_legacy_playlist,
    update_sports_block,
)


SPORTS_REPORT_PATH = Path(__file__).with_name("sports-status.json")


def main() -> int:
    playlist = DEFAULT_PLAYLIST
    lines = playlist.read_text(encoding="utf-8-sig").splitlines()
    enabled = sports_feature_enabled() if "SPORTS_EVENTS_ENABLED" in os.environ else True
    updated_lines, status = update_sports_block(lines, enabled=enabled)

    if updated_lines != lines:
        playlist.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
        print(f"Lista deportiva actualizada: {status.get('channels', 0)} entradas")
    else:
        print(f"Lista deportiva sin cambios: {status.get('channels', 0)} entradas")

    if sync_legacy_playlist(playlist):
        print(f"Copia compatible sincronizada: {LEGACY_PLAYLIST.name}")

    SPORTS_REPORT_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    for error in status.get("errors", [])[:8]:
        print(f"[DEPORTE AVISO] {error}")

    if not status.get("ok", False) and not status.get("preserved", False):
        print("No se pudo generar un bloque deportivo valido.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        SPORTS_REPORT_PATH.write_text(
            json.dumps({"ok": False, "fatal_error": str(error)}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"ERROR: {error}")
        raise SystemExit(1)
