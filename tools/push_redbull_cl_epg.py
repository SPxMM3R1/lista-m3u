"""Sube la parrilla de Red Bull Chile desde una conexión chilena.

Red Bull entrega https://www.redbull.tv/es_CL/epg según el país de la IP; desde
GitHub (EE. UU.) trae otra región. Este script corre en un PC en Chile, guarda
solo títulos y horarios en data/redbull-cl-epg.json y lo publica con
``[skip ci]``: la siguiente corrida de EPG lo usa. No guarda tokens ni URL.

Uso: python tools/push_redbull_cl_epg.py [--no-push]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import update_m3u  # noqa: E402
from epg_sources import red_bull  # noqa: E402

FIELDS = ("start_time", "end_time", "title", "subheading", "short_description", "long_description")


def build_snapshot(now: datetime) -> dict:
    country = red_bull.red_bull_request_country()
    if country != "cl":
        raise SystemExit(f"Red Bull ve esta conexion como '{country}', no como Chile: no se sube nada")
    schedule = red_bull.red_bull_page_schedule(now)
    return {
        "schema": 1,
        "country": "cl",
        "source": update_m3u.RED_BULL_SPANISH_EPG_PAGE,
        "fetchedAt": now.replace(microsecond=0).isoformat(),
        "programmes": [{key: item.get(key) for key in FIELDS if item.get(key)} for item in schedule],
    }


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-push", action="store_true", help="solo escribe el archivo")
    args = parser.parse_args()

    path = update_m3u.RED_BULL_CHILE_EPG_SNAPSHOT_PATH
    relative = path.relative_to(ROOT).as_posix()
    if not args.no_push:
        git("pull", "--rebase", "--quiet")
    snapshot = build_snapshot(datetime.now(timezone.utc))
    previous = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if previous.get("programmes") == snapshot["programmes"]:
        print("Parrilla Red Bull Chile sin cambios")
        return 0
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Parrilla Red Bull Chile: {len(snapshot['programmes'])} programas hasta "
          f"{snapshot['programmes'][-1]['end_time']}")
    if args.no_push:
        return 0
    git("add", relative)
    git("commit", "--quiet", "-m", "Actualiza parrilla Red Bull Chile [skip ci]")
    for attempt in range(3):
        try:
            git("push", "--quiet")
            return 0
        except subprocess.CalledProcessError:
            git("pull", "--rebase", "--quiet")
    raise SystemExit("no se pudo publicar la parrilla Red Bull Chile")


if __name__ == "__main__":
    raise SystemExit(main())
