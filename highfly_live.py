"""Enlaces directos de Highfly para que la app abra sus canales sin resolver.

En cada corrida confirma, para cada canal Highfly activo del layout, qué hoja
(slug) está entregando señal ahora y publica su enlace directo en
``data/highfly-live.json``. El enlace no lleva token ni datos de sesión: es
``https://papacito.cfd/m3u/<slug>/live.m3u8``. La app lo abre directo y, si
falla porque Highfly rotó la hoja entre corridas, usa su resolutor.

Uso: python highfly_live.py [--output data/highfly-live.json]
Sale con código 0 aunque un canal no tenga señal: ese canal simplemente no se
publica y la app lo resuelve como siempre.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import update_m3u
from tests.catalog_approval import approved_by_user, layout_approval_digest

ROOT = Path(__file__).resolve().parent
LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"
SELECTION_PATH = ROOT / "data" / "vibem3u-selection.json"
OUTPUT_PATH = ROOT / "data" / "highfly-live.json"
SCHEMA = 1


# ── Identificadores Highfly al día (2026-10-15) ──────────────────────────────────────────
# Highfly renombra sus hojas (now-34343434 → now-4344344). La app pide Premium con el
# resolverSlug del layout: con uno viejo no hay 4K y los UHD caen a la señal gratis. Cada
# corrida copia al layout (y a la selección) el id que el catálogo público de Highfly da hoy
# para cada catalogKey. Solo cambian resolverSlug/providerResourceId: ni números, ni estados,
# ni nombres; por eso un sello de aprobación válido se renueva con su mismo origen.

def _dump(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def sync_slugs(rows: list[dict], current: dict[str, str]) -> list[str]:
    """Pone en cada fila Highfly el id vigente; devuelve los cambios hechos."""
    changes = []
    for row in rows:
        if not isinstance(row, dict) or row.get("provider") != "highfly":
            continue
        slug = (current.get(row.get("catalogKey") or "") or "").strip()
        if not slug or not update_m3u.HIGHFLY_LEAF_ID_PATTERN.fullmatch(f"leaf:{slug}"):
            continue
        if row.get("resolverSlug") == slug and row.get("providerResourceId") == f"leaf:{slug}":
            continue
        changes.append(f"{row.get('catalogKey')}: {row.get('resolverSlug')} → {slug}")
        row["resolverSlug"] = slug
        row["providerResourceId"] = f"leaf:{slug}"
    return changes


def sync_layout_document(layout: dict, current: dict[str, str]) -> list[str]:
    was_approved = approved_by_user(layout)
    changes = sync_slugs(layout.get("channels", []), current)
    if changes and was_approved:
        layout["approval"] = {"source": layout["approval"]["source"],
                              "sha256": layout_approval_digest(layout)}
    return changes


def sync_selection_document(selection: dict, current: dict[str, str]) -> list[str]:
    changes = []
    for source in selection.get("sources", []):
        if isinstance(source, dict) and source.get("provider") == "highfly":
            changes += sync_slugs(source.get("channels", []), current)
    return changes


def sync_files(current: dict[str, str], layout_path: Path = LAYOUT_PATH,
               selection_path: Path = SELECTION_PATH) -> list[str]:
    """Escribe los ids vigentes. Si un archivo no tiene el formato exacto que se reescribe,
    no se toca (evita un diff enorme o un cambio de formato inesperado)."""
    if not current:
        return []
    applied = []
    for path, sync in ((layout_path, sync_layout_document), (selection_path, sync_selection_document)):
        try:
            text = path.read_text(encoding="utf-8")
            document = json.loads(text)
        except (OSError, ValueError):
            continue
        if _dump(document) != text.replace("\r\n", "\n"):
            print(f"  [--] {path.name}: formato distinto al esperado; ids Highfly sin sincronizar")
            continue
        changes = sync(document, current)
        if changes:
            path.write_text(_dump(document), encoding="utf-8", newline="\n")
            applied += [f"{path.name} · {change}" for change in changes]
    return applied


def active_highfly_rows(layout: dict) -> list[dict]:
    rows = []
    for row in layout.get("channels", []):
        if not isinstance(row, dict) or row.get("provider") != "highfly":
            continue
        if row.get("state", "active") != "active":
            continue
        if not row.get("catalogKey"):
            continue
        rows.append(row)
    return rows


def candidate_slugs(row: dict) -> list[str]:
    """Hoja elegida en el editor primero; luego las demás hojas del mismo canal."""
    candidates: list[str] = []

    def add(slug: str | None) -> None:
        slug = (slug or "").strip()
        if slug.startswith("leaf:"):
            slug = slug[len("leaf:"):]
        if slug and slug not in candidates and update_m3u.HIGHFLY_LEAF_ID_PATTERN.fullmatch(f"leaf:{slug}"):
            candidates.append(slug)

    add(row.get("resolverSlug") or row.get("providerResourceId"))
    add(update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS.get(row["catalogKey"]))
    key = update_m3u.highfly_catalog_name_key(row.get("name"))
    for slug in update_m3u.HIGHFLY_RUNTIME_VARIANTS.get(key, []) if key else []:
        add(slug)
    return candidates


def live_slug(row: dict, fetch=None, reasons: list[str] | None = None) -> str | None:
    """Primera hoja del canal que Highfly entrega con señal en este momento."""
    fetch = fetch or update_m3u.fetch_highfly_stream_urls_for_slug
    for slug in candidate_slugs(row):
        try:
            if fetch(slug):
                return slug
        except Exception as error:  # noqa: BLE001 - una hoja caída no detiene las demás
            if reasons is not None:
                reasons.append(f"{slug}: {error}")
            continue
    return None


def build_document(rows: list[dict], fetch=None, now: datetime | None = None) -> dict:
    channels = []
    for row in rows:
        reasons: list[str] = []
        slug = live_slug(row, fetch, reasons)
        if not slug:
            detail = f" ({'; '.join(reasons)})" if reasons else ""
            print(f"  [--] {row.get('name')}: Highfly sin señal ahora{detail}; la app usará su resolutor")
            continue
        url = update_m3u.highfly_fallback_url(slug)
        if not update_m3u.is_highfly_leaf_url(url):
            continue
        channels.append({"catalogKey": row["catalogKey"], "slug": slug, "url": url})
        print(f"  [OK] {row.get('name')}: {slug}")
    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    return {"schema": SCHEMA, "generatedAt": moment.isoformat().replace("+00:00", "Z"), "channels": channels}


# La app descarta el archivo si su generatedAt tiene más de 24 h. Aunque los enlaces
# no cambien, la fecha se renueva cada 3 h para que un enlace vigente siga usándose.
TIMESTAMP_REFRESH = timedelta(hours=3)


def _parse_timestamp(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def write_if_changed(document: dict, path: Path = OUTPUT_PATH) -> bool:
    """Reescribe si cambian los enlaces o si la fecha publicada ya tiene 3 h o más."""
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            previous_at = _parse_timestamp(previous.get("generatedAt"))
            current_at = _parse_timestamp(document.get("generatedAt"))
            fresh = (
                previous_at is not None
                and current_at is not None
                and current_at - previous_at < TIMESTAMP_REFRESH
            )
            if previous.get("channels") == document["channels"] and fresh:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    current: dict[str, str] = {}
    try:
        current = update_m3u.refresh_highfly_runtime_catalog() or {}
    except Exception as error:  # noqa: BLE001 - sin catálogo se prueban las hojas del layout
        print(f"  [--] catálogo Highfly no disponible: {error}")
    for change in sync_files(current):
        print(f"  [ID] {change}")
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    document = build_document(active_highfly_rows(layout))
    changed = write_if_changed(document, args.output)
    print(f"Enlaces Highfly: {len(document['channels'])} publicados · "
          f"{'actualizado' if changed else 'sin cambios'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
