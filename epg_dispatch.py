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
INDEX_PATH = ROOT / "epg" / "indice.json"
# Aviso y renovación anticipada por canal (2026-10-13): con menos de AVISO_HORIZON de guía
# queda un aviso; con RENEW_LEAD o menos, sus fuentes se adelantan antes de quedar sin guía.
AVISO_HORIZON = timedelta(hours=6)
RENEW_LEAD = timedelta(hours=2)


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
    interval = interval_for(part)
    if failures <= 0:
        return interval

    # No calcular FIRST_RETRY * 2 ** failures antes de limitarlo: una fuente
    # que falla muchas veces acaba desbordando timedelta antes de llegar a min().
    # La espera se satura al ritmo normal en unas pocas iteraciones, incluso si
    # el contador lleva años acumulándose.
    delay = FIRST_RETRY
    remaining_doublings = failures - 1
    while remaining_doublings > 0 and delay < interval:
        delay = min(interval, delay * 2)
        remaining_doublings -= 1
    return min(interval, delay)


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


def channel_horizons(index: dict, now: datetime, skip: set[str] = frozenset()) -> dict[str, dict]:
    """Horas de guía que le quedan a cada canal del índice (None: sin guía)."""
    horizons = {}
    for entry in index.get("channels", []):
        channel_id = entry.get("id")
        if not channel_id or channel_id in skip:
            continue
        stop = parse(entry.get("lastStop"))
        hours = None if stop is None else max(0.0, (stop - now).total_seconds() / 3600)
        horizons[channel_id] = {"name": entry.get("name") or channel_id,
                                "lastStop": entry.get("lastStop"), "hours": hours}
    return horizons


def build_notices(horizons: dict[str, dict]) -> dict[str, dict]:
    """Avisos: canales con poca guía por delante, y si se renuevan ya."""
    notices = {}
    for channel_id, info in horizons.items():
        hours = info["hours"]
        if hours is not None and hours >= AVISO_HORIZON.total_seconds() / 3600:
            continue
        urgent = hours is None or hours <= RENEW_LEAD.total_seconds() / 3600
        notices[channel_id] = {
            "name": info["name"],
            "hours": None if hours is None else round(hours, 1),
            "lastStop": info["lastStop"],
            "action": "renovar ya" if urgent else "vigilar",
        }
    return notices


def urgent_channels(notices: dict[str, dict]) -> set[str]:
    return {channel_id for channel_id, notice in notices.items() if notice["action"] == "renovar ya"}


def print_notices(notices: dict[str, dict]) -> None:
    for channel_id, notice in sorted(notices.items(), key=lambda item: (item[1]["hours"] is not None, item[1]["hours"] or 0)):
        left = "sin guía" if notice["hours"] is None else f"{notice['hours']} h de guía"
        print(f"  [EPG-AVISO] {notice['name']} ({channel_id}): {left} · {notice['action']}")


def load_index(path: Path = INDEX_PATH) -> dict:
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
        return index if isinstance(index, dict) else {}
    except (OSError, ValueError):
        return {}


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


ALERT_MIN_FAILURES = 8


def failing_sources(state: dict, min_failures: int = ALERT_MIN_FAILURES) -> list[dict]:
    """Fuentes con ``min_failures`` o más fallos seguidos, la peor primero."""
    rows = []
    for part, entry in (state.get("parts") or {}).items():
        failures = int(entry.get("failures", 0))
        if failures >= min_failures:
            rows.append({"part": part, "failures": failures,
                         "lastSuccess": entry.get("lastSuccess"), "lastAttempt": entry.get("lastAttempt")})
    return sorted(rows, key=lambda row: (-row["failures"], row["part"]))


def alert_body(rows: list[dict], min_failures: int = ALERT_MIN_FAILURES) -> str:
    lines = [f"Fuentes EPG con {min_failures} o más fallos seguidos (según `epg/estado.json`).",
             "Cada canal conserva su última guía buena; esto avisa que la fuente no se renueva.", "",
             "| Fuente | Fallos seguidos | Último éxito |", "|---|---|---|"]
    for row in rows:
        lines.append(f"| `{row['part']}` | {row['failures']} | {row['lastSuccess'] or 'nunca registrado'} |")
    return "\n".join(lines) + "\n"


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def unused_official_parts(update_m3u, scope_ids: list[str]) -> set[str]:
    """Fuentes oficiales sin ningún canal en el alcance de la EPG (2026-10-31).

    Ej.: 13C quedó borrado y su guía oficial se seguía pidiendo: sin canal al que
    asignarla, cada corrida contaba como fallo.
    """
    used: set[str] = set()
    for channel_id in scope_ids:
        used |= update_m3u.epg_channel_parts(channel_id)
    return {source.name for source in update_m3u.OFFICIAL_EPG_SOURCES} - used


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
    unused: set[str] = set()
    try:
        scope_ids, _ = update_m3u.epg_scope_order()
        unused = unused_official_parts(update_m3u, scope_ids)
        existing = set(update_m3u.epg_fragments.read_dir(update_m3u.EPG_FRAGMENTS_DIR))
        for channel_id in scope_ids:
            if channel_id not in existing:
                needed |= update_m3u.epg_channel_parts(channel_id)
        # Renovación anticipada: canales a punto de quedarse sin guía adelantan sus fuentes.
        skip = set(update_m3u.EPG_ALLOWED_EMPTY_IDS) | {update_m3u.EPG_MAIN_LIVE_CHANNEL_ID}
        notices = build_notices(channel_horizons(load_index(), now_utc(), skip))
        print_notices(notices)
        for channel_id in urgent_channels(notices) & set(scope_ids):
            needed |= update_m3u.epg_channel_parts(channel_id)
    except Exception as error:  # noqa: BLE001 (sin alcance, se planifica por ritmo)
        print(f"AVISO: no se pudo revisar canales sin fragmento: {error}", file=sys.stderr)
    if unused:
        print("Fuentes oficiales sin canales (no se piden): " + ", ".join(sorted(unused)))
    candidates = [part for part in all_parts if part not in unused or part in forced]
    parts = due_parts(load_state(), candidates, now_utc(), needed=needed, forced=forced)
    print("Partes a renovar: " + (", ".join(parts) if parts else "ninguna"))
    write_output("parts", json.dumps(parts))
    write_output("any", "true" if parts else "false")
    return 0


def command_record(args: argparse.Namespace) -> int:
    import update_m3u  # noqa: PLC0415

    raw = (args.planned or "").strip()
    planned = json.loads(raw) if raw.startswith("[") else [p.strip() for p in raw.split(",") if p.strip()]
    results = {}
    for part in planned:
        loaded = update_m3u.read_epg_part(args.parts_dir, part) if args.parts_dir else None
        results[part] = bool(loaded and (loaded.documents or loaded.red_bull_schedules))
    now = now_utc()
    state = record(load_state(), planned, results, now)
    # Avisos sobre la guía recién unida: quedan en el estado y en el log de la corrida.
    skip = set(update_m3u.EPG_ALLOWED_EMPTY_IDS) | {update_m3u.EPG_MAIN_LIVE_CHANNEL_ID}
    notices = build_notices(channel_horizons(load_index(), now, skip))
    state["avisos"] = {"updatedAt": stamp(now), "channels": notices}
    try:
        scope_ids, _ = update_m3u.epg_scope_order()
        for part in unused_official_parts(update_m3u, scope_ids):
            state["parts"].pop(part, None)
    except Exception as error:  # noqa: BLE001 (sin alcance, el estado queda como estaba)
        print(f"AVISO: no se pudieron quitar fuentes sin canales: {error}", file=sys.stderr)
    print_notices(notices)
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


def command_alerts(args: argparse.Namespace) -> int:
    rows = failing_sources(load_state(), args.min_failures)
    body = alert_body(rows, args.min_failures)
    if args.body:
        Path(args.body).write_text(body, encoding="utf-8")
    print(body if rows else "Sin fuentes EPG con fallos seguidos.")
    write_output("count", str(len(rows)))
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
    alerts = sub.add_parser("alerts")
    alerts.add_argument("--min-failures", type=int, default=ALERT_MIN_FAILURES)
    alerts.add_argument("--body", help="archivo donde escribir el cuerpo de la alerta")
    args = parser.parse_args()
    return {"plan": command_plan, "record": command_record, "alerts": command_alerts}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
