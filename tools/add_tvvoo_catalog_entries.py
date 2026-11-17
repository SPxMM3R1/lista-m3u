"""Fichas canónicas en channel-catalog.m3u para las filas TvVoo activas de Lista 2 sin ficha.

2026-11-17: el bloque «catálogo completo de Vavoo» (8.382 filas) no tenía fichas, así que la
conciliación las dejaba pendientes (catalog_not_found) y no llegaban a 2.m3u. Cada ficha usa el
contrato tvvoo:// (tvg-id = catalogKey + "@TvVoo", como exige M3uParser de VibeM3U). Idempotente.
"""
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "channel-catalog.m3u"
LAYOUT = ROOT / "data" / "channel-editor-layout.json"
RAW = "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/"


def attr(value: str) -> str:
    return str(value or "").replace('"', "'").replace("\n", " ").strip()


def main() -> int:
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    text = CATALOG.read_text(encoding="utf-8")
    lines = text.splitlines()
    existing = set(re.findall(r'tvg-id="([^"]+)"', text))
    resolver_aliases = {
        unquote(alias)
        for value in re.findall(r'\bx-(?:resolver-ids|tvvoo-aliases)="([^"]*)"', text)
        for alias in value.split(";") if alias
    }
    added = []
    names = set(re.findall(r'tvg-name="([^"]+)"', text))
    for row in layout.get("channels") or []:
        if row.get("state") != "active" or row.get("provider") != "tvvoo" or row.get("sourceList") != "2.m3u":
            continue
        key = str(row.get("catalogKey") or "")
        if "|" not in key:
            continue
        country, alias = key.split("|", 1)
        tvg_id = key + "@TvVoo"
        if tvg_id in existing or key in existing:
            continue  # ya tiene su ficha exacta
        # Aunque una ficha antigua comparta el alias, la fila lleva su propia ficha exacta: la
        # conciliación prefiere la identidad exacta y no intenta migrar la antigua.
        logo = row.get("logoPath") or ""
        logo_url = logo if logo.startswith("http") else (RAW + logo if logo else "")
        name = attr(row.get("displayName") or row.get("name"))
        # tvg-name único por ficha (load_checked_in_tvvoo_aliases lo exige): el mismo nombre
        # existe en varios países. Mismo formato que las fichas TvVoo antiguas.
        code = unquote(alias).rsplit("|group:", 1)[-1]
        catalog_name = f"{name} [TvVoo {code}]"
        if catalog_name in names:
            # Una ficha TvVoo antigua ya usa ese nombre con otro alias: se distingue con el alias.
            catalog_name = f"{name} [TvVoo {code} · {unquote(alias)[6:].rsplit('|group:', 1)[0]}]"
            if catalog_name in names:
                continue
        names.add(catalog_name)
        added.append(
            f'#EXTINF:-1 tvg-id="{attr(tvg_id)}" tvg-name="{catalog_name}" tvg-logo="{attr(logo_url)}" '
            f'group-title="{attr(row.get("group"))}" x-vibem3u-selection="managed" x-resolver="tvvoo" '
            f'x-resolver-endpoint="https://tvvoo.hayd.uk/stream/tv" x-resolver-ids="{attr(alias)}" '
            f'x-resolver-refresh="on_play" x-resolver-recipe="bounded-payload-v1" '
            f'x-resolver-country="{attr(country)}" x-resolver-stable-id="{attr(key)}",{name}'
        )
        added.append("tvvoo://channel/" + quote(key, safe=""))
        existing.add(tvg_id)
    if added:
        CATALOG.write_text("\n".join(lines + added) + "\n", encoding="utf-8", newline="\n")
    print(f"Fichas TvVoo agregadas: {len(added) // 2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
