#!/usr/bin/env python3
"""Coordina una ejecucion completa de Lista M3U cada 48 horas.

El mismo coordinador se usa desde Windows y desde GitHub Actions. No publica
por si mismo: prepara la salida y el estado para que cada ejecutor pueda usar
su mecanismo de commit y verificacion habitual.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PROJECT_ROOT = Path(__file__).resolve().parent
UPDATE_SCRIPT = PROJECT_ROOT / "update_m3u.py"
STATE_PATH = PROJECT_ROOT / "run-state.json"
OUTPUT_PATHS = (PROJECT_ROOT / "m3u.m3u", PROJECT_ROOT / "epg.xml")
INTERVAL = timedelta(hours=48)
LOCAL_LAST_DAY = date(2026, 9, 1)
GITHUB_FIRST_DAY = date(2026, 9, 2)
try:
    CHILE_TIMEZONE = ZoneInfo("America/Santiago")
except ZoneInfoNotFoundError:
    CHILE_TIMEZONE = timezone(timedelta(hours=-4))


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
            "interval_hours": 48,
            "last_published_at": None,
            "last_executor": None,
        }
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"run-state.json no se puede leer: {error}") from error
    if not isinstance(state, dict):
        raise RuntimeError("run-state.json no contiene un objeto JSON")
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


def is_due(state: dict, current: datetime, force: bool) -> bool:
    if force:
        return True
    previous = last_published_at(state)
    if previous is None:
        return True
    elapsed = current - previous
    if elapsed.total_seconds() < 0:
        print(
            "La ultima publicacion esta en el futuro; se omite la ejecucion "
            "para evitar una frecuencia accidental.",
            file=sys.stderr,
        )
        return False
    return elapsed >= INTERVAL


def write_state(current: datetime, executor: str) -> None:
    state = {
        "schema": 1,
        "interval_hours": 48,
        "last_published_at": timestamp(current),
        "last_executor": executor,
    }
    temporary = STATE_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    temporary.replace(STATE_PATH)


def restore_outputs(snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        try:
            if path.read_bytes() != content:
                path.write_bytes(content)
        except FileNotFoundError:
            path.write_bytes(content)


def run_updater(force_epg: bool) -> int:
    environment = os.environ.copy()
    # TVN y Meganoticias conservan sus masters para que la aplicacion resuelva
    # la autenticacion. El ejecutor local debe clasificar sus 401/403 igual que
    # Actions, sin sustituir la URL ni escribir tokens.
    environment["M3U_ALLOW_GEO_RESTRICTED"] = "true"
    if force_epg:
        environment["EPG_FORCE_REFRESH"] = "true"
    completed = subprocess.run(
        [sys.executable, str(UPDATE_SCRIPT)],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta la validacion M3U/EPG cuando vencen 48 horas."
    )
    parser.add_argument("--executor", choices=("local", "github"), required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="ignora el intervalo de 48 horas, sin saltar la ventana local/GitHub",
    )
    parser.add_argument("--force-epg", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    current = now_utc()
    chile_day = current.astimezone(CHILE_TIMEZONE).date()

    write_github_output("ran", "false")
    write_github_output("due", "false")

    if args.executor == "local" and chile_day >= GITHUB_FIRST_DAY:
        print(
            f"Ventana local finalizada el {LOCAL_LAST_DAY.isoformat()}; "
            "GitHub queda como ejecutor desde el 2026-09-02."
        )
        return 0
    if args.executor == "github" and chile_day < GITHUB_FIRST_DAY:
        print(
            "Ventana GitHub en espera hasta el 2026-09-02; no se consume "
            "la ejecucion de actualizacion."
        )
        return 0

    state = load_state()
    previous = last_published_at(state)
    if previous:
        print(f"Ultima publicacion efectiva: {timestamp(previous)}")
    due = is_due(state, current, args.force or args.force_epg)
    write_github_output("due", "true" if due else "false")
    if not due:
        next_at = previous + INTERVAL if previous else current
        print(f"Actualizacion no necesaria; proxima ventana: {timestamp(next_at)}")
        return 0
    if args.dry_run:
        print("La actualizacion esta vencida; dry-run no ejecuta el actualizador.")
        return 0

    snapshots = {
        path: path.read_bytes() if path.exists() else None for path in OUTPUT_PATHS
    }
    print(f"Ejecutando validacion completa con {args.executor} a las {timestamp(current)}")
    return_code = run_updater(args.force_epg)
    if return_code != 0:
        restore_outputs(snapshots)
        print(
            "El actualizador fallo; se conservaron m3u.m3u y epg.xml anteriores.",
            file=sys.stderr,
        )
        return return_code

    write_state(current, args.executor)
    write_github_output("ran", "true")
    print("Actualizacion completa preparada para publicar.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
