#!/usr/bin/env python3
"""Despachador de la guía por canal (2026-10-12).

Corre cada 30 minutos y decide qué fuentes (partes) descargar: solo las vencidas, cada una
con su propio ritmo, más las que necesita un canal que todavía no tiene fragmento. Si una
fuente falla se reintenta con espera creciente, sin arrastrar a las demás.

    python epg_dispatch.py plan [--force a,b] [--all]   -> imprime y publica ``parts``
    python epg_dispatch.py record --planned a,b --parts-dir epg-parts

Estado en ``epg/estado.json``; también mantiene ``epg-run-state.json`` (última publicación).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "epg" / "estado.json"
RUN_STATE_PATH = ROOT / "epg-run-state.json"
DEFAULT_INTERVAL = timedelta(hours=6)
# Ritmo propio por fuente: Red Bull publica tarjetas cortas y cambia seguido.
PART_INTERVALS = {
    "red-bull": timedelta(hours=2),
}
FIRST_RETRY = timedelta(minutes=30)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def interval_for(part: str) -> timedelta:
    return PART_INTERVALS.get(part, DEFAULT_INTERVAL)


def retry_after(part: str, failures: int) -> timedelta:
    """30 min, 1 h, 2 h… sin pasar del ritmo normal de la fuente."""
    if failures <= 0:
        return interval_for(part)
    return min(interval_for(part), FIRST_RETRY * (2 ** (failures - 1)))


def load_state(path: Path = STATE_PATH) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(state, dict) and isinstance(state.get("parts"), dict):
            return state
    except (OSError, ValueError):
        pass
    return {"schema": 1, "parts": {}}


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def due_parts(
    state: dict,
    all_parts: list[str],
    now: datetime,
    *,
    needed: set[str] = frozenset(),
    forced: set[str] = frozenset(),
) -> list[str]:
    """Partes vencidas, pedidas a mano o que necesita un canal sin fragmento."""
    due = []
    for part in all_parts:
        entry = state["parts"].get(part, {})
        next_due = parse(entry.get("nextDue"))
        last_attempt = parse(entry.get("lastAttempt"))
        if part in forced or next_due is None or next_due <= now:
            due.append(part)
        elif part in needed and (last_attempt is None or now - last_attempt >= FIRST_RETRY):
            due.append(part)
    return due


def record(state: dict, planned: list[str], results: dict[str, bool], now: datetime) -> dict:
    for part in planned:
        entry = dict(state["parts"].get(part, {}))
        entry["lastAttempt"] = stamp(now)
        if results.get(part):
            entry["lastSuccess"] = stamp(now)
            entry["failures"] = 0
        else:
            entry["failures"] = int(entry.get("failures", 0)) + 1
        entry["nextDue"] = stamp(now + retry_after(part, entry["failures"]))
        state["parts"][part] = entry
    return state


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def command_plan(args: argparse.Namespace) -> int:
    import update_m3u  # noqa: PLC0415 (carga pesada: solo al planificar)

    all_parts = update_m3u.epg_part_names()
    forced = {p.strip() for p in (args.force or "").split(",") if p.strip()}
    unknown = sorted(forced - set(all_parts))
    if unknown:
        print("Partes desconocidas: " + ", ".join(unknown) + ". Válidas: " + ", ".join(all_parts),
              file=sys.stderr)
        return 2
    if args.all:
        forced = set(all_parts)
    needed: set[str] = set()
    try:
        scope_ids, _ = update_m3u.epg_scope_order()
        existing = set(update_m3u.epg_fragments.read_dir(update_m3u.EPG_FRAGMENTS_DIR))
        for channel_id in scope_ids:
            if channel_id not in existing:
                needed |= update_m3u.epg_channel_parts(channel_id)
    except Exception as error:  # noqa: BLE001 (sin alcance, se planifica por ritmo)
        print(f"AVISO: no se pudo revisar canales sin fragmento: {error}", file=sys.stderr)
    parts = due_parts(load_state(), all_parts, now_utc(), needed=needed, forced=forced)
    print("Partes a renovar: " + (", ".join(parts) if parts else "ninguna"))
    write_output("parts", json.dumps(parts))
    write_output("any", "true" if parts else "false")
    return 0


def command_record(args: argparse.Namespace) -> int:
    import update_m3u  # noqa: PLC0415

    planned = [p for p in json.loads(args.planned or "[]")] if args.planned.startswith("[") else [
        p.strip() for p in args.planned.split(",") if p.strip()]
    results = {}
    for part in planned:
        loaded = update_m3u.read_epg_part(args.parts_dir, part) if args.parts_dir else None
        results[part] = bool(loaded and (loaded.documents or loaded.red_bull_schedules))
    now = now_utc()
    state = record(load_state(), planned, results, now)
    save_state(state)
    failed = sorted(part for part in planned if not results[part])
    if failed:
        print("Fuentes sin datos (se reintentan con espera): " + ", ".join(failed), file=sys.stderr)
    RUN_STATE_PATH.write_text(json.dumps({
        "schema": 3,
        "last_published_at": stamp(now),
        "last_executor": "github",
        "schedule_basis": "Guía por canal: despachador cada 30 min, cada fuente con su ritmo",
    }, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--force", default="", help="partes separadas por coma")
    plan.add_argument("--all", action="store_true")
    rec = sub.add_parser("record")
    rec.add_argument("--planned", default="")
    rec.add_argument("--parts-dir", type=Path)
    args = parser.parse_args()
    return command_plan(args) if args.command == "plan" else command_record(args)


if __name__ == "__main__":
    raise SystemExit(main())
