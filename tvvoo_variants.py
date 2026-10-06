"""Versiones hermanas de cada canal TvVoo elegido (respaldo real para VibeM3U).

TvVoo lista varias entradas del mismo canal en un país: «SKY SPORTS MIX», «SKY SPORTS MIX
HD», «SKY SPORTS MIX FHD», «SKY SPORTS MIX (BACKUP)». Cada una es una fuente de origen
distinta en Vavoo, así que si una se cae otra puede seguir al aire. Este script publica,
por cada canal TvVoo activo del catálogo editorial, los alias de sus hermanas en
``data/tvvoo-variantes.json``. La app prueba primero la versión elegida y después estas.

Reglas (decididas con el usuario, 2026-10-01):

- Solo dentro del mismo país (grupo TvVoo). No se cruzan países por parecido de nombre.
- Excepción editorial (2026-10-06): una fila TvVoo con ``backupCountries`` (lista de
  countryKey en orden, pedida por el usuario para Eurosport 1 y 2) suma, después de sus
  hermanas, el mismo canal de cada uno de esos países: una entrada por país, con el mismo
  nombre base, la de mejor calidad y nunca un (BACKUP). Es otro idioma de la misma señal.
- El nombre base debe coincidir exacto. Solo se quitan marcas de calidad o respaldo
  (HD, FHD, UHD, 4K, SD, HD+, HEVC, H265, (BACKUP), (BACKUP 2)...).
- «SPORT» y «SPORTS» NO se igualan: en Alemania «SKY SPORT F1» es la señal alemana y
  «SKY SPORTS F1» la inglesa; mezclarlas cambiaría el idioma.
- Entradas dudosas no son hermanas: «(MATCH TIME)», «[LIVE DURING EVENTS ONLY]»,
  «(LOCAL)» y «RAW» pueden tener otro contenido o estar apagadas.
- Excepción UK: BT/TNT se unen solo mediante nombres exactos verificados con
  fotogramas (2026-10-02, TVVOO_UK_EQUIVALENCIAS.md), no por parecido de nombre.

El archivo solo lleva alias del catálogo público de TvVoo: ni URL de reproducción ni tokens.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent
LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"
OUTPUT_PATH = ROOT / "data" / "tvvoo-variantes.json"
CATALOG_URL = "https://tvvoo.hayd.uk/catalog/tv/vavoo_tv_{code}.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024
MAX_SIBLINGS = 7
# El catálogo de TvVoo omite entradas de una consulta a otra (2026-10-01: «SKY SPORTS MIX
# HD» faltó en una consulta y volvió en la siguiente). Una hermana publicada se conserva
# hasta que falte en esta cantidad de corridas seguidas.
MISSING_RUNS_BEFORE_DROP = 3
# La app descarta variantes con más de 7 días. Una comprobación correcta renueva
# su fecha al menos cada 24 h, aunque los alias no cambien, sin un commit por cron.
TIMESTAMP_REFRESH = timedelta(hours=24)
# Igual que COUNTRY_KEYS de site/provider-catalog.mjs.
COUNTRY_CODES = {
    "albania": "al", "arabia": "ar", "bulgaria": "bg", "balkans": "bk", "germany": "de",
    "spain": "es", "france": "fr", "italy": "it", "netherlands": "nl", "poland": "pl",
    "portugal": "pt", "romania": "ro", "russia": "ru", "turkey": "tr", "unitedkingdom": "uk",
}

_VARIANT_SUFFIX = re.compile(
    r"(?:\s*\((?:BACKUP(?:\s*\d+)?|H\.?265)\)|\s+(?:FHD|UHD|4K|HD\+|HD|SD|HEVC|H\.?265))$"
)
_NOT_A_SIBLING = re.compile(r"\(MATCH TIME\)|\[LIVE DURING EVENTS ONLY\]|\(LOCAL\)|\bRAW\b")

# Lista cerrada: no extender a HD/BACKUP sin comprobar su señal y programación.
# TNT SPORT 1 es la identidad elegida; hoy entrega una placa de error, no video real.
UK_VERIFIED_SIGNALS = {
    "TNT SPORT 1": 1, "BT SPORT 1": 1, "BT SPORT 1 (BACKUP)": 1,
    "TNT SPORT 2": 2, "BT SPORT 2": 2, "BT SPORT 2 HD": 2,
    "TNT SPORTS 3": 3, "TNT SPORTS 3 HD": 3, "BT SPORT 3": 3,
    "TNT SPORT 4": 4, "TNT SPORTS 4 HD": 4,
    "BT SPORT ESPN": 4, "BT SPORT ESPN HD": 4,
}
UK_VERIFIED_FAMILIES = {"BT SPORT 1", "BT SPORT 2", "BT SPORT 3", "BT SPORT ESPN",
                        "TNT SPORT 1", "TNT SPORT 2", "TNT SPORTS 3", "TNT SPORT 4",
                        "TNT SPORTS 4"}


def alias_name(alias: str) -> str:
    decoded = unquote(alias[len("vavoo_"):]) if alias.startswith("vavoo_") else ""
    return decoded.split("|", 1)[0]


def verified_uk_signal(alias: str, name: str, code: str | None) -> int | None:
    if code != "uk" or not alias.startswith("vavoo_"):
        return None
    decoded = unquote(alias[len("vavoo_"):])
    if not decoded.lower().endswith("|group:uk"):
        return None
    normalized = re.sub(r"\s+", " ", name.strip().upper())
    # El nombre visible y el alias deben representar la misma entrada verificada.
    if normalized != re.sub(r"\s+", " ", alias_name(alias).strip().upper()):
        return None
    return UK_VERIFIED_SIGNALS.get(normalized)


def base_name(name: str) -> str | None:
    """Nombre sin marcas de calidad/respaldo; None si la entrada no puede ser hermana."""
    value = re.sub(r"\s+", " ", (name or "").strip().upper())
    if not value or _NOT_A_SIBLING.search(value):
        return None
    previous = None
    while previous != value:
        previous = value
        value = _VARIANT_SUFFIX.sub("", value).strip()
    return value or None


def variant_rank(name: str) -> int:
    """Orden de las hermanas: primero las de mejor calidad, los respaldos al final."""
    upper = (name or "").upper()
    if "BACKUP" in upper:
        return 3
    if re.search(r"\b(?:FHD|UHD|4K)\b", upper):
        return 0
    if re.search(r"\bHD\+?(?:\s|$)", upper):
        return 1
    return 2


def _encode_alias_part(value: str) -> str:
    # encodeURIComponent + !'()~ escapados y hex en mayúsculas, como el editor
    # (canonicalTvVooAlias) y TvVooSourceHistory.canonicalAlias en la app.
    return quote(value, safe="-_.*").replace("~", "%7E")


def canonical_alias(raw_id: str, code: str) -> str | None:
    raw = (raw_id or "").strip()
    if not raw.startswith("vavoo_"):
        return None
    decoded = unquote(raw[len("vavoo_"):].replace("+", "%2B"))
    if "|group:" not in decoded.lower():
        decoded += f"|group:{code}"
    return "vavoo_" + _encode_alias_part(decoded)


def catalog_entries(document: dict, code: str) -> list[tuple[str, str]]:
    """(alias canónico, nombre) de cada canal del catálogo del país."""
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for meta in document.get("metas") or []:
        if not isinstance(meta, dict):
            continue
        name = str(meta.get("name") or "").strip()
        alias = canonical_alias(str(meta.get("id") or ""), code)
        if name and alias and alias not in seen:
            seen.add(alias)
            entries.append((alias, name))
    return entries


def siblings_for(selected_alias: str, entries: list[tuple[str, str]], code: str | None = None) -> list[str]:
    names = {alias: name for alias, name in entries}
    selected_name = names.get(selected_alias)
    if selected_name is None:
        # La versión elegida ya no figura en el catálogo: su nombre sale del alias.
        selected_name = alias_name(selected_alias)
    base = base_name(selected_name)
    if not base:
        return []
    protected_uk = code == "uk" and base in UK_VERIFIED_FAMILIES
    signal = verified_uk_signal(selected_alias, selected_name, code)
    if protected_uk and signal is None:
        return []
    candidates = [
        (variant_rank(name), index, alias)
        for index, (alias, name) in enumerate(entries)
        if alias != selected_alias and (
            verified_uk_signal(alias, name, code) == signal if protected_uk
            else base_name(name) == base
        )
    ]
    return [alias for _, _, alias in sorted(candidates)[:MAX_SIBLINGS]]


def active_tvvoo_rows(layout: dict) -> list[dict]:
    return [
        row for row in layout.get("channels") or []
        if isinstance(row, dict)
        and row.get("kind") == "provider"
        and row.get("provider") == "tvvoo"
        and row.get("state") == "active"
        and "|" in str(row.get("catalogKey") or "")
    ]


def fetch_catalog(code: str) -> dict:
    request = urllib.request.Request(
        CATALOG_URL.format(code=code),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError(f"catálogo TvVoo {code} excede {MAX_BYTES} bytes")
    return json.loads(body.decode("utf-8"))


def backup_countries(row: dict) -> list[str]:
    """countryKey de ``backupCountries`` válidos, sin repetir ni incluir el propio país."""
    own = str(row.get("countryKey") or "")
    result: list[str] = []
    for value in row.get("backupCountries") or []:
        country = str(value or "")
        if country in COUNTRY_CODES and country != own and country not in result:
            result.append(country)
    return result


def cross_country_aliases(selected_alias: str, selected_name: str | None,
                          entries_by_code: dict[str, list[tuple[str, str]]],
                          countries: list[str]) -> list[str]:
    """El mismo canal en otros países (uno por país), en el orden pedido."""
    base = base_name(selected_name or alias_name(selected_alias))
    if not base:
        return []
    result: list[str] = []
    for country in countries:
        entries = entries_by_code.get(COUNTRY_CODES[country])
        if not entries:
            continue
        candidates = [
            (variant_rank(name), index, alias)
            for index, (alias, name) in enumerate(entries)
            if base_name(name) == base and "BACKUP" not in name.upper()
        ]
        if candidates:
            result.append(min(candidates)[2])
    return result


def build_variants(layout: dict, fetch=fetch_catalog) -> tuple[dict[str, list[str]], dict[str, str]]:
    rows = active_tvvoo_rows(layout)
    countries = {str(row.get("countryKey") or "") for row in rows}
    for row in rows:
        countries.update(backup_countries(row))
    codes = sorted({COUNTRY_CODES.get(country, "") for country in countries} - {""})
    entries_by_code: dict[str, list[tuple[str, str]]] = {}
    errors: dict[str, str] = {}
    for code in codes:
        try:
            entries_by_code[code] = catalog_entries(fetch(code), code)
        except Exception as error:  # un país caído no borra los demás
            errors[code] = f"{type(error).__name__}: {error}"
    channels: dict[str, list[str]] = {}
    for row in rows:
        code = COUNTRY_CODES.get(str(row.get("countryKey") or ""))
        if code not in entries_by_code:
            continue
        selected = str(row["catalogKey"]).split("|", 1)[1]
        siblings = siblings_for(selected, entries_by_code[code], code)
        extra = backup_countries(row)
        if extra:
            # Las hermanas del país primero, pero dejando lugar a un idioma por país.
            names = dict(entries_by_code[code])
            cross = cross_country_aliases(selected, names.get(selected), entries_by_code, extra)
            siblings = siblings[:max(1, MAX_SIBLINGS - len(cross))] + cross
        if siblings:
            channels[str(row["catalogKey"])] = siblings[:MAX_SIBLINGS]
    return channels, errors


def merge_with_previous(
    channels: dict[str, list[str]],
    previous: dict,
    active_keys: set[str],
    failed_countries: set[str],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Suma hermanas publicadas antes que hoy faltaron, hasta MISSING_RUNS_BEFORE_DROP corridas."""
    merged = {key: list(aliases) for key, aliases in channels.items()}
    previous_channels = previous.get("channels") or {}
    previous_missing = previous.get("missing") or {}
    missing: dict[str, int] = {}
    for key, aliases in previous_channels.items():
        if key not in active_keys:
            continue  # el canal ya no está elegido en el editor
        country = key.split("|", 1)[0]
        current = merged.setdefault(key, [])
        for alias in aliases:
            if alias in current:
                continue
            # Una entrada rechazada por evidencia no se conserva tres corridas ni
            # se recupera si el catálogo falla. No altera la retención del resto.
            selected = key.split("|", 1)[1]
            if country == "unitedkingdom" and base_name(alias_name(selected)) in UK_VERIFIED_FAMILIES:
                signal = verified_uk_signal(selected, alias_name(selected), "uk")
                if signal is None or verified_uk_signal(alias, alias_name(alias), "uk") != signal:
                    continue
            marker = f"{key} {alias}"
            # Un respaldo de otro país depende del catálogo de ese país, no del propio.
            group = re.search(r"%7Cgroup%3A([a-z]{2})$", alias, re.IGNORECASE)
            alias_country = next((name for name, code in COUNTRY_CODES.items()
                                  if group and code == group.group(1).lower()), country)
            runs = 0 if alias_country in failed_countries else previous_missing.get(marker, 0) + 1
            if runs < MISSING_RUNS_BEFORE_DROP:
                current.append(alias)
                if runs:
                    missing[marker] = runs
        if not current:
            del merged[key]
    return {key: aliases[:MAX_SIBLINGS] for key, aliases in merged.items()}, missing


def timestamp_refresh_due(previous: dict, now: datetime) -> bool:
    """Fecha ausente/inválida o con 24 h: hay que renovar tras consultar con éxito."""
    try:
        generated_at = datetime.fromisoformat(str(previous.get("generatedAt", "")).replace("Z", "+00:00"))
        if generated_at.tzinfo is None:
            return True
        age = now - generated_at
        return age < timedelta(0) or age >= TIMESTAMP_REFRESH
    except (ValueError, TypeError):
        return True


def main() -> int:
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    channels, errors = build_variants(layout)
    for code, error in sorted(errors.items()):
        print(f"AVISO catálogo TvVoo {code}: {error}", file=sys.stderr)
    previous: dict = {}
    if OUTPUT_PATH.is_file():
        try:
            previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
    active_keys = {str(row["catalogKey"]) for row in active_tvvoo_rows(layout)}
    failed_countries = {country for country, code in COUNTRY_CODES.items() if code in errors}
    channels, missing = merge_with_previous(channels, previous, active_keys, failed_countries)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    # No rejuvenecer un respaldo conservado solo porque el proveedor está caído.
    refresh_timestamp = bool(channels) and not errors and timestamp_refresh_due(previous, now)
    if (previous.get("channels") == channels
            and (previous.get("missing") or {}) == missing
            and not refresh_timestamp):
        print("Variantes TvVoo sin cambios")
        return 0
    document = {
        "schema": 1,
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "channels": dict(sorted(channels.items())),
        # Corridas seguidas en que cada hermana conservada faltó en el catálogo.
        "missing": dict(sorted(missing.items())),
    }
    OUTPUT_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Variantes TvVoo: {len(channels)} canales con hermanas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
