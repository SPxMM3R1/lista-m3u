"""Genera data/lista2-tvvoo-bloque.m3u: el catálogo completo de Vavoo al final de Lista 2.

2026-11-17. El bloque no va en data/channel-editor-layout.json: con 8.000 filas ahí la memoria
de VibeM3U crecía sin parar y la TV quedaba en negro. Va como líneas M3U que el runner pega al
final de m3u-externa.m3u/2.m3u (update_m3u.with_tvvoo_catalog_block); la app las muestra al
final, en este orden, como canales sin fila en el editor.

Fuente: la captura del catálogo vivo data/tvvoo-catalogo-vivo-20261117.json (un canal por
nombre y país). Fuera: los nombres con exclusión permanente del runner, los canales que ya
están en una lista (fila TvVoo activa o respaldo TvVoo) y los que Lista 1 ya publica.
Logos: el del inventario (contracts/tvvoo-logos-lista2-20261117.json) o el genérico del país.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import update_m3u  # noqa: E402

SNAPSHOT = ROOT / "data" / "tvvoo-catalogo-vivo-20261117.json"
LOGOS = ROOT / "contracts" / "tvvoo-logos-lista2-20261117.json"
LAYOUT = ROOT / "data" / "channel-editor-layout.json"
OUTPUT = ROOT / "data" / "lista2-tvvoo-bloque.m3u"
RAW = "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/"
BLOCK_ATTRIBUTE = update_m3u.TVVOO_CATALOG_BLOCK_ATTRIBUTE

COUNTRIES = {
    # inglés del catálogo: (countryKey, código, etiqueta)
    "United Kingdom": ("unitedkingdom", "uk", "Reino Unido"),
    "Spain": ("spain", "es", "España"),
    "Albania": ("albania", "al", "Albania"),
    "Germany": ("germany", "de", "Alemania"),
    "Arabia": ("arabia", "ar", "Arabia"),
    "Balkans": ("balkans", "bk", "Balcanes"),
    "Bulgaria": ("bulgaria", "bg", "Bulgaria"),
    "France": ("france", "fr", "Francia"),
    "Italy": ("italy", "it", "Italia"),
    "Netherlands": ("netherlands", "nl", "Países Bajos"),
    "Poland": ("poland", "pl", "Polonia"),
    "Portugal": ("portugal", "pt", "Portugal"),
    "Romania": ("romania", "ro", "Rumania"),
    "Russia": ("russia", "ru", "Rusia"),
    "Turkey": ("turkey", "tr", "Turquía"),
}
FIRST = ("unitedkingdom", "spain")


def encode_alias_part(value: str) -> str:
    # Igual que tvvoo_variants._encode_alias_part y canonicalTvVooAlias del editor.
    return quote(value, safe="-_.*").replace("~", "%7E")


def attr(value: str) -> str:
    return re.sub(r"[\r\n\"]", " ", str(value or "")).strip()


def used_keys(layout: dict) -> set[str]:
    keys: set[str] = set()
    for row in layout.get("channels") or []:
        if row.get("state") != "active":
            continue
        for field in ("catalogKey", "backupTvVoo"):
            value = str(row.get(field) or "")
            if "|" in value:
                keys.add(value)
    return keys


def used_aliases(layout: dict) -> set[str]:
    """Alias TvVoo (sin codificar) de filas activas: también sus aliases y resolverAliases."""
    aliases: set[str] = set()
    for row in layout.get("channels") or []:
        if row.get("state") != "active":
            continue
        values = list(row.get("aliases") or []) + list(row.get("resolverAliases") or [])
        for field in ("catalogKey", "backupTvVoo"):
            value = str(row.get(field) or "")
            if "|" in value:
                values.append(value.split("|", 1)[1])
        aliases.update(unquote(value) for value in values if value)
    return aliases


def main() -> int:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["channels"]
    logos = json.loads(LOGOS.read_text(encoding="utf-8"))["rows"]
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    taken_keys = used_keys(layout)
    taken_aliases = used_aliases(layout)
    # Alias que Lista 1 ya resuelve en el catálogo (x-resolver-ids / x-tvvoo-aliases).
    catalog_text = (ROOT / "channel-catalog.m3u").read_text(encoding="utf-8")
    main_ids = {
        line.split('tvg-id="', 1)[1].split('"', 1)[0]
        for line in (ROOT / "m3u.m3u").read_text(encoding="utf-8").splitlines()
        if line.startswith("#EXTINF") and 'tvg-id="' in line
    }
    for line in catalog_text.splitlines():
        match = re.search(r'tvg-id="([^"]+)"', line)
        if not line.startswith("#EXTINF") or not match or match.group(1) not in main_ids:
            continue
        for value in re.findall(r'\bx-(?:resolver-ids|tvvoo-aliases)="([^"]*)"', line):
            taken_aliases.update(unquote(alias) for alias in value.split(";") if alias)

    rows = []
    skipped = {"excluido": 0, "en lista": 0}
    for item in snapshot:
        country = COUNTRIES.get(item.get("country"))
        name = str(item.get("name") or "").strip()
        if not country or not name:
            continue
        country_key, code, label = country
        if any(pattern.search(name) for pattern in update_m3u.PERMANENTLY_REMOVED_CHANNEL_NAME_PATTERNS):
            skipped["excluido"] += 1
            continue
        alias = "vavoo_" + encode_alias_part(f"{name}|group:{code}")
        key = f"{country_key}|{alias}"
        if key in taken_keys or unquote(alias) in taken_aliases:
            skipped["en lista"] += 1
            continue
        logo = (logos.get(f"{country_key}|{name.lower()}") or {}).get("logoPath") or f"logos/tvvoo-paises/{code}.svg"
        rows.append((country_key, label, name, key, logo))

    order = {key: index for index, key in enumerate(FIRST)}
    labels = {country_key: label for country_key, _, label in COUNTRIES.values()}
    rows.sort(key=lambda row: (order.get(row[0], len(FIRST)), labels[row[0]], row[2].casefold()))
    lines = ["#EXTM3U"]
    for country_key, label, name, key, logo in rows:
        lines.append(
            f'#EXTINF:-1 tvg-id="{attr(key)}@TvVoo" tvg-name="{attr(name)}" '
            f'tvg-logo="{attr(RAW + logo)}" group-title="{attr(label)}" '
            f'{BLOCK_ATTRIBUTE}="tvvoo-catalogo",{attr(name)}'
        )
        lines.append("tvvoo://channel/" + quote(key, safe=""))
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    per_country: dict[str, int] = {}
    for row in rows:
        per_country[row[1]] = per_country.get(row[1], 0) + 1
    print(f"Bloque TvVoo de Lista 2: {len(rows)} canales; omitidos {skipped}")
    print(json.dumps(per_country, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
