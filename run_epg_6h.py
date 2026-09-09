#!/usr/bin/env python3
"""Coordina la publicacion independiente de la EPG cada seis horas."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
UPDATE_SCRIPT = PROJECT_ROOT / "update_m3u.py"
STATE_PATH = PROJECT_ROOT / "epg-run-state.json"
EPG_PATH = PROJECT_ROOT / "epg.xml"
PREMIUM_STABLE_PLAYLIST_PATH = PROJECT_ROOT / "3.m3u"
INTERVAL = timedelta(hours=6)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def write_github_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    with Path(output_file).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            "schema": 1,
            "interval_hours": 6,
            "last_published_at": None,
            "last_executor": None,
        }
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"epg-run-state.json no se puede leer: {error}") from error
    if not isinstance(state, dict):
        raise RuntimeError("epg-run-state.json no contiene un objeto JSON")
    return state


def last_published_at(state: dict) -> datetime | None:
    value = state.get("last_published_at")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError(f"last_published_at invalido: {value}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def next_scheduled_at(state: dict, current: datetime) -> datetime:
    previous = last_published_at(state)
    return current if previous is None else previous + INTERVAL


def is_due(state: dict, current: datetime, force: bool) -> bool:
    if force:
        return True
    previous = last_published_at(state)
    if previous is None:
        return True
    if current < previous:
        print(
            "La ultima EPG publicada esta en el futuro; se omite la ejecucion.",
            file=sys.stderr,
        )
        return False
    return current >= next_scheduled_at(state, current)


def write_state(current: datetime, executor: str, next_run: datetime) -> None:
    state = {
        "schema": 2,
        "interval_hours": 6,
        "minimum_interval_hours": 6,
        "last_published_at": timestamp(current),
        "last_executor": executor,
        "next_scheduled_at": timestamp(next_run),
        "schedule_basis": "EPG independiente cada 6 horas sobre catalogo completo",
    }
    temporary = STATE_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    temporary.replace(STATE_PATH)


def run_updater() -> int:
    environment = os.environ.copy()
    environment["EPG_FORCE_REFRESH"] = "true"
    completed = subprocess.run(
        [sys.executable, str(UPDATE_SCRIPT), "--refresh-epg-only"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Actualiza la EPG del catalogo completo cada seis horas."
    )
    parser.add_argument("--executor", choices=("local", "github"), required=True)
    parser.add_argument("--force", action="store_true", help="ignora el intervalo")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    current = now_utc()
    write_github_output("ran", "false")
    write_github_output("due", "false")

    state = load_state()
    previous = last_published_at(state)
    if previous:
        print(f"Ultima EPG publicada: {timestamp(previous)}")
    next_at = next_scheduled_at(state, current)
    due = is_due(state, current, args.force)
    write_github_output("due", "true" if due else "false")
    write_github_output("next_scheduled_at", timestamp(next_at))
    if not due:
        print(f"EPG no necesita actualizacion; proxima ventana: {timestamp(next_at)}")
        return 0
    if args.dry_run:
        print("La EPG esta vencida; dry-run no ejecuta el actualizador.")
        return 0

    snapshot_epg = EPG_PATH.read_bytes() if EPG_PATH.exists() else None
    snapshot_premium_stable = (
        PREMIUM_STABLE_PLAYLIST_PATH.read_bytes()
        if PREMIUM_STABLE_PLAYLIST_PATH.exists()
        else None
    )
    snapshot_state = STATE_PATH.read_bytes() if STATE_PATH.exists() else None
    print(f"Ejecutando EPG independiente con {args.executor} a las {timestamp(current)}")
    return_code = run_updater()
    if return_code != 0:
        if snapshot_epg is None:
            EPG_PATH.unlink(missing_ok=True)
        else:
            EPG_PATH.write_bytes(snapshot_epg)
        if snapshot_premium_stable is None:
            PREMIUM_STABLE_PLAYLIST_PATH.unlink(missing_ok=True)
        else:
            PREMIUM_STABLE_PLAYLIST_PATH.write_bytes(snapshot_premium_stable)
        if snapshot_state is None:
            STATE_PATH.unlink(missing_ok=True)
        else:
            STATE_PATH.write_bytes(snapshot_state)
        print("La EPG fallo; se conservaron la guia y su estado anteriores.", file=sys.stderr)
        return return_code

    published_at = now_utc()
    next_after_publish = next_scheduled_at(
        {"last_published_at": timestamp(published_at)}, published_at
    )
    write_state(published_at, args.executor, next_after_publish)
    write_github_output("ran", "true")
    write_github_output("next_scheduled_at", timestamp(next_after_publish))
    print(f"EPG preparada para publicar. Proxima ventana: {timestamp(next_after_publish)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
