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
from datetime import datetime, timezone
from pathlib import Path

import update_m3u

ROOT = Path(__file__).resolve().parent
LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"
OUTPUT_PATH = ROOT / "data" / "highfly-live.json"
SCHEMA = 1


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


def live_slug(row: dict, fetch=None) -> str | None:
    """Primera hoja del canal que Highfly entrega con señal en este momento."""
    fetch = fetch or update_m3u.fetch_highfly_stream_urls_for_slug
    for slug in candidate_slugs(row):
        try:
            if fetch(slug):
                return slug
        except Exception:  # noqa: BLE001 - una hoja caída no detiene las demás
            continue
    return None


def build_document(rows: list[dict], fetch=None, now: datetime | None = None) -> dict:
    channels = []
    for row in rows:
        slug = live_slug(row, fetch)
        if not slug:
            print(f"  [--] {row.get('name')}: Highfly sin señal ahora; la app usará su resolutor")
            continue
        url = update_m3u.highfly_fallback_url(slug)
        if not update_m3u.is_highfly_leaf_url(url):
            continue
        channels.append({"catalogKey": row["catalogKey"], "slug": slug, "url": url})
        print(f"  [OK] {row.get('name')}: {slug}")
    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    return {"schema": SCHEMA, "generatedAt": moment.isoformat().replace("+00:00", "Z"), "channels": channels}


def write_if_changed(document: dict, path: Path = OUTPUT_PATH) -> bool:
    """Solo reescribe si cambian los enlaces; la hora sola no genera commits."""
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous.get("channels") == document["channels"]:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    try:
        update_m3u.refresh_highfly_runtime_catalog()
    except Exception as error:  # noqa: BLE001 - sin catálogo se prueban las hojas del layout
        print(f"  [--] catálogo Highfly no disponible: {error}")
    document = build_document(active_highfly_rows(layout))
    changed = write_if_changed(document, args.output)
    print(f"Enlaces Highfly: {len(document['channels'])} publicados · "
          f"{'actualizado' if changed else 'sin cambios'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
