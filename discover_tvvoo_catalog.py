#!/usr/bin/env python3
"""Discover bounded, stable TvVoo catalogue entries for the external list.

This job is deliberately separate from stream maintenance and EPG generation.
It reads only the public TvVoo catalogues, keeps stable aliases in a small
sidecar, and lets the six-hour channel job resolve and validate the actual HLS
source afterwards. No response URL, token, session key or executable payload is
written to the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import update_m3u as updater


PROJECT_ROOT = Path(__file__).resolve().parent
CATALOG_PATH = PROJECT_ROOT / "channel-catalog.m3u"
DISCOVERY_MAP_PATH = PROJECT_ROOT / "tvvoo-discovered.json"
TVVOO_HOST = "tvvoo.hayd.uk"
TVVOO_CATALOG_URL = (
    "https://tvvoo.hayd.uk/catalog/tv/vavoo_tv_{region}.json"
)
DISCOVERY_REGIONS = (
    "uk",
    "it",
    "fr",
    "de",
    "pt",
    "es",
    "nl",
    "pl",
    "bg",
    "ar",
    "ro",
    "ru",
)
REGION_LABELS = {
    "uk": "Reino Unido",
    "it": "Italia",
    "fr": "Francia",
    "de": "Alemania",
    "pt": "Portugal",
    "es": "España",
    "nl": "Países Bajos",
    "pl": "Polonia",
    "bg": "Bulgaria",
    "ar": "Argentina",
    "ro": "Rumanía",
    "ru": "Rusia",
}
REGION_COUNTRIES = {
    "uk": "GB",
    "it": "IT",
    "fr": "FR",
    "de": "DE",
    "pt": "PT",
    "es": "ES",
    "nl": "NL",
    "pl": "PL",
    "bg": "BG",
    "ar": "AR",
    "ro": "RO",
    "ru": "RU",
}
CATALOG_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_NEW = 24
MAX_NEW_PER_RUN = 48
MAX_TOTAL_DISCOVERED = updater.TVVOO_DISCOVERY_MAX_CHANNELS
SAFE_LOGO_HOSTS = frozenset(
    {
        "antifriz.tv",
        "epg.pw",
        "i.imgur.com",
        "raw.githubusercontent.com",
        "static.wikia.nocookie.net",
        "tvlogo.org",
    }
)
QUALITY_TOKENS = frozenset(
    {"4K", "8K", "FHD", "HD", "SD", "UHD", "H265", "HEVC", "BACKUP"}
)
EXCLUDED_NAME_PATTERN = re.compile(
    r"\b(?:PPV|PAY\s+PER\s+VIEW|VOD|TEST|DEMO|EVENT|MATCH\s+CENTER|"
    r"TURKEY|TÜRKIYE|TURQU[IÍ]A|"
    r"BALKAN|BALCAN)\b",
    re.IGNORECASE,
)
ADULT_PATTERN = re.compile(
    r"\b(?:ADULT|EROTIC(?:A|S)?|PORN(?:O)?|XXX|PLAYBOY|PRIVATE|"
    r"BRAZZERS|HUSTLER|PENTHOUSE|REDLIGHT|DORCEL|VIVID|EROTIK|"
    r"BEATE|18\s*\+)",
    re.IGNORECASE,
)
SPORTS_PATTERN = re.compile(
    r"\b(?:SPORT|SPORTS|ESPN|DAZN|EUROSPORT|TNT\s+SPORT|BEIN|ZIGGO|"
    r"PREMIER\s+SPORT|RACING|RALLY|FOOTBALL|SOCCER|FUTBOL|FÚTBOL|"
    r"TENNIS|GOLF|CRICKET|NFL|F1|FORMULA\s*1|MOTOGP|MOTO|MOTORSPORT|"
    r"NBA|NHL|MLB|W-SPORT|ELEVEN|RUGBY|BOXING|UFC|FIGHT|WWE|"
    r"WRESTLING|CYCLING|ATHLETICS|HORSE|EQUESTRIAN|VOLLEY(?:BALL)?|"
    r"BASKET(?:BALL)?|BASEBALL|HOCKEY|SKI|SURF|EXTREME|OLYMPIC|"
    r"DARTS|HANDBALL|BADMINTON|SWIMMING|SWIM|WATER\s+SPORT)\b",
    re.IGNORECASE,
)
NEWS_PATTERN = re.compile(
    r"\b(?:NEWS|CNN|BBC\s+(?:WORLD|NEWS)|AL\s+JAZEERA|EURONEWS|DW|"
    r"FRANCE\s*24|SKY\s+NEWS|CNA|NHK)\b",
    re.IGNORECASE,
)
MUSIC_PATTERN = re.compile(
    r"\b(?:MUSIC|MUSIK|MUSIQUE|MUSICA|MTV|XITE|STINGRAY|TRACE|VH1|"
    r"BOX\s+HITS|HITS|CONCERTS?|ICONCERTS?|QELLO|LIVE\s+MUSIC|"
    r"JAZZ|CLASSICAL|CLASSIQUE|OPERA|DJAZZ|ROCK|POP|COUNTRY|KARAOKE)\b",
    re.IGNORECASE,
)
MOVIE_PATTERN = re.compile(
    r"\b(?:MOVIE|MOVIES|FILM|FILMS|CINEMA|CINE|CINÉ|SKY\s+CINEMA|"
    r"TCM|AMC|HOLLYWOOD|STAR\s+MOVIES|CINEMAX|PARAMOUNT|FILM4|"
    r"CANAL\s*\+|CINESTAR|KINO)\b",
    re.IGNORECASE,
)
SUBTITLE_HINT_PATTERN = re.compile(
    r"\b(?:SUBTITLE(?:S)?|SUBTIT(?:LE|LES|ULOS?|ULADA|ULADO)|SUBBED|"
    r"SUBTITLED|VOST(?:FR|ES)?|VOSE|VOST|WITH\s+SUBTITLES)\b",
    re.IGNORECASE,
)
CATEGORY_ORDER = (
    "Deportes",
    "Música",
    "Películas",
    "Adultos",
    "Noticias internacionales",
    "Misceláneos",
)


@dataclass(frozen=True)
class CandidateGroup:
    region: str
    source_name: str
    aliases: tuple[str, ...]
    logo: str
    category: str
    base_key: str
    subtitle_hint: bool = False


def normalize_spaces(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("\r", " ").replace("\n", " ")


def ascii_text(value: object) -> str:
    return (
        unicodedata.normalize("NFKD", normalize_spaces(value))
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def identity_key(value: object) -> str:
    """Collapse only quality/transport suffixes for duplicate detection."""
    tokens = re.findall(r"[A-Z0-9]+", ascii_text(value).upper())
    normalized = [
        "SPORT" if token == "SPORTS" else token
        for token in tokens
        if token not in QUALITY_TOKENS
    ]
    return " ".join(normalized)


def decode_vavoo_id(raw_id: object) -> tuple[str, str] | None:
    decoded = unquote(normalize_spaces(raw_id))
    match = re.fullmatch(
        r"vavoo_(?P<name>.+)\|group:(?P<region>[a-z]{2})", decoded,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    source_name = normalize_spaces(match.group("name"))
    region = match.group("region").lower()
    if (
        not source_name
        or region not in DISCOVERY_REGIONS
        or any(ord(char) < 32 for char in source_name)
        or "/" in source_name
        or "\\" in source_name
    ):
        return None
    return source_name, region


def normalize_vavoo_id(raw_id: object) -> str | None:
    decoded = decode_vavoo_id(raw_id)
    if decoded is None:
        return None
    source_name, region = decoded
    encoded_name = quote(source_name, safe="-._~")
    return f"vavoo_{encoded_name}%7Cgroup%3A{region}"


def alias_preference(alias: str) -> tuple[int, int, str]:
    decoded = decode_vavoo_id(alias)
    if decoded is None:
        return (99, len(alias), alias)
    source_name, _ = decoded
    tokens = set(re.findall(r"[A-Z0-9]+", ascii_text(source_name).upper()))
    if not tokens.intersection(QUALITY_TOKENS):
        quality_rank = 0
    elif "FHD" in tokens or "UHD" in tokens:
        quality_rank = 1
    elif "HD" in tokens:
        quality_rank = 2
    elif "SD" in tokens:
        quality_rank = 3
    else:
        quality_rank = 4
    return quality_rank, len(source_name), alias


def safe_logo(value: object) -> str:
    if not isinstance(value, str):
        return ""
    logo = value.strip()
    parsed = urlparse(logo)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in SAFE_LOGO_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(logo) > 512
    ):
        return ""
    return logo


def metadata_search_text(
    source_name: str, genres: object, metadata: dict[str, object] | None = None
) -> str:
    values = [source_name]
    if isinstance(genres, list):
        values.extend(item for item in genres if isinstance(item, str))
    elif isinstance(genres, str):
        values.append(genres)
    # TvVoo currently exposes mostly name/genres/logo fields. These optional
    # fields make the classifier forward-compatible if a catalogue starts
    # publishing language, subtitle or description hints later, without
    # persisting arbitrary provider metadata in the sidecar.
    if isinstance(metadata, dict):
        for key in (
            "description",
            "category",
            "language",
            "languages",
            "country",
            "audio",
            "subtitle",
            "subtitles",
            "tags",
        ):
            value = metadata.get(key)
            if isinstance(value, list):
                values.extend(item for item in value if isinstance(item, str))
            elif isinstance(value, str):
                values.append(value)
    return " ".join(normalize_spaces(value) for value in values if value)


def has_subtitle_hint(
    source_name: str, genres: object, metadata: dict[str, object] | None = None
) -> bool:
    combined = metadata_search_text(source_name, genres, metadata)
    return bool(
        MOVIE_PATTERN.search(combined)
        and SUBTITLE_HINT_PATTERN.search(combined)
    )


def category_for(
    source_name: str,
    genres: object,
    metadata: dict[str, object] | None = None,
) -> str:
    combined = metadata_search_text(source_name, genres, metadata)
    # Adult content is intentionally classified, never excluded. It comes
    # first so a movie/music-branded adult signal cannot be misfiled.
    if ADULT_PATTERN.search(combined):
        return "Adultos"
    if SPORTS_PATTERN.search(combined):
        return "Deportes"
    if NEWS_PATTERN.search(combined):
        return "Noticias internacionales"
    if MOVIE_PATTERN.search(combined):
        return "Películas"
    if MUSIC_PATTERN.search(combined):
        return "Música"
    return "Misceláneos"


def excluded_source_name(source_name: str) -> bool:
    return bool(
        EXCLUDED_NAME_PATTERN.search(source_name)
        or updater.is_permanently_removed_channel_name(source_name)
    )


def pretty_name(source_name: str, region: str) -> str:
    value = re.sub(
        r"(?:\s*\(?(?:4K|8K|FHD|HD|SD|UHD|H265|HEVC|BACKUP)\)?)+\s*$",
        "",
        normalize_spaces(source_name),
        flags=re.IGNORECASE,
    )
    if value.upper() == value:
        value = value.title()
    replacements = {
        r"\bTv\b": "TV",
        r"\bBt\b": "BT",
        r"\bDazn\b": "DAZN",
        r"\bEspn\b": "ESPN",
        r"\bBbc\b": "BBC",
        r"\bCnn\b": "CNN",
        r"\bNba\b": "NBA",
        r"\bNhl\b": "NHL",
        r"\bMtv\b": "MTV",
        r"\bXite\b": "XITE",
        r"\bFhd\b": "FHD",
        r"\bHd\b": "HD",
        r"\bF1\b": "F1",
    }
    for pattern, replacement in replacements.items():
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    value = re.sub(r"[\",\r\n]", " ", value)
    value = normalize_spaces(value)
    region_label = REGION_LABELS[region]
    if ascii_text(region_label).casefold() not in ascii_text(value).casefold():
        value = f"{value} {region_label}"
    return value


def fetch_region_catalog(region: str, *, timeout: int = 20) -> list[dict[str, object]]:
    if region not in DISCOVERY_REGIONS:
        raise ValueError(f"region no permitida: {region}")
    url = TVVOO_CATALOG_URL.format(region=region)
    if urlparse(url).hostname != TVVOO_HOST:
        raise ValueError("host de catalogo TvVoo no permitido")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "lista-m3u-tvvoo-discovery/1.0",
        },
    )
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                final_host = (urlparse(response.geturl()).hostname or "").lower()
                if final_host != TVVOO_HOST:
                    raise ValueError("el catalogo redirigio a un host no permitido")
                body = response.read(CATALOG_MAX_BYTES + 1)
                if len(body) > CATALOG_MAX_BYTES:
                    raise ValueError("catalogo TvVoo demasiado grande")
            payload = json.loads(body.decode("utf-8-sig"))
            metas = payload.get("metas") if isinstance(payload, dict) else None
            if not isinstance(metas, list):
                raise ValueError("TvVoo no devolvio metas")
            return [meta for meta in metas if isinstance(meta, dict)]
        except (OSError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == 0:
                continue
    raise RuntimeError(f"{region}: no se pudo leer el catalogo TvVoo: {last_error}")


def candidate_groups(metas: list[dict[str, object]], region: str) -> list[CandidateGroup]:
    variants: dict[str, list[dict[str, object]]] = defaultdict(list)
    for meta in metas:
        if str(meta.get("type", "")).lower() != "tv":
            continue
        alias = normalize_vavoo_id(meta.get("id", ""))
        decoded = decode_vavoo_id(meta.get("id", ""))
        raw_source_name = meta.get("name", "")
        source_name = (
            normalize_spaces(raw_source_name)
            if isinstance(raw_source_name, str)
            else ""
        )
        if alias is None or decoded is None or decoded[1] != region:
            continue
        if not source_name or len(source_name) > 100 or excluded_source_name(source_name):
            continue
        base_key = identity_key(source_name)
        if len(base_key) < 2:
            continue
        logo = safe_logo(meta.get("logo"))
        variants[base_key].append(
            {
                "alias": alias,
                "source_name": source_name,
                "logo": logo,
                "category": category_for(
                    source_name, meta.get("genres", []), meta
                ),
                "subtitle_hint": has_subtitle_hint(
                    source_name, meta.get("genres", []), meta
                ),
            }
        )

    groups: list[CandidateGroup] = []
    for base_key, group_variants in variants.items():
        aliases = tuple(
            sorted(
                {str(item["alias"]) for item in group_variants},
                key=alias_preference,
            )[:8]
        )
        if not aliases:
            continue
        ranked = sorted(
            group_variants,
            key=lambda item: (
                0 if item["logo"] else 1,
                alias_preference(str(item["alias"])),
            ),
        )
        primary = ranked[0]
        logo = str(primary["logo"])
        if not logo:
            # A candidate without a trustworthy logo is left for a later run;
            # this keeps the automatic list visually usable and prevents a
            # placeholder/remote tracking image from entering the catalogue.
            continue
        categories = [str(item["category"]) for item in group_variants]
        category = min(
            categories,
            key=lambda value: CATEGORY_ORDER.index(value),
        )
        subtitle_hint = any(
            bool(item.get("subtitle_hint"))
            for item in group_variants
        )
        groups.append(
            CandidateGroup(
                region=region,
                source_name=str(primary["source_name"]),
                aliases=aliases,
                logo=logo,
                category=category,
                base_key=base_key,
                subtitle_hint=subtitle_hint,
            )
        )
    return groups


def m3u_attribute(line: str, name: str) -> str:
    match = re.search(rf'\b{re.escape(name)}="([^"]*)"', line)
    return match.group(1) if match else ""


def existing_inventory(
    lines: list[str], sidecar: dict[str, dict[str, object]]
) -> tuple[set[str], set[str], set[str], set[str]]:
    ids: set[str] = set()
    aliases: set[str] = set()
    identity_names: set[str] = set()
    for line in lines:
        if not line.startswith("#EXTINF:"):
            continue
        tvg_id = m3u_attribute(line, "tvg-id")
        display_name = line.rsplit(",", 1)[-1].strip()
        if tvg_id:
            ids.add(tvg_id)
        if display_name:
            identity_names.add(identity_key(display_name))
        for raw_alias in m3u_attribute(line, "x-resolver-ids").split(";"):
            normalized = normalize_vavoo_id(raw_alias)
            if normalized:
                aliases.add(normalized)

    # The executable map also represents channels already curated in the
    # catalogue, even when a future manual edit has temporarily removed one.
    for resolver_aliases in updater.TVVOO_STREAM_RESOLVER_IDS.values():
        for alias in resolver_aliases:
            normalized = normalize_vavoo_id(alias)
            if normalized:
                aliases.add(normalized)

    for tvg_id, entry in sidecar.items():
        ids.add(tvg_id)
        source_name = str(entry.get("sourceName") or entry.get("name") or "")
        if source_name:
            identity_names.add(identity_key(source_name))
        for alias in entry.get("aliases", []):
            normalized = normalize_vavoo_id(alias)
            if normalized:
                aliases.add(normalized)
    return ids, aliases, identity_names, set(sidecar)


def stable_channel_id(group: CandidateGroup, used_ids: set[str]) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "", ascii_text(group.base_key).upper())
    slug = slug[:54] or "CHANNEL"
    candidate = f"Vavoo.{group.region}.{slug}@TvVoo"
    if candidate in used_ids:
        digest = hashlib.sha256(";".join(group.aliases).encode("utf-8")).hexdigest()[:8].upper()
        candidate = f"Vavoo.{group.region}.{slug[:45]}-{digest}@TvVoo"
    return candidate


def select_candidates(
    groups: list[CandidateGroup],
    *,
    existing_ids: set[str],
    existing_aliases: set[str],
    existing_names: set[str],
    existing_sidecar_count: int,
    max_new: int,
) -> tuple[list[tuple[str, CandidateGroup]], dict[str, int]]:
    stats = {
        "duplicate_alias": 0,
        "duplicate_name": 0,
        "no_logo": 0,
        "selected": 0,
        "capacity": 0,
    }
    available = max(0, MAX_TOTAL_DISCOVERED - existing_sidecar_count)
    limit = min(max_new, available)
    if limit == 0:
        stats["capacity"] = len(groups)
        return [], stats

    buckets: dict[tuple[str, str], list[CandidateGroup]] = defaultdict(list)
    for group in groups:
        if any(alias in existing_aliases for alias in group.aliases):
            stats["duplicate_alias"] += 1
            continue
        if group.base_key in existing_names:
            stats["duplicate_name"] += 1
            continue
        buckets[(group.region, group.category)].append(group)
    for bucket in buckets.values():
        bucket.sort(
            key=lambda group: (
                0 if group.category == "Películas" and group.subtitle_hint else 1,
                group.base_key,
                group.aliases,
            )
        )

    selected: list[tuple[str, CandidateGroup]] = []
    used_ids = set(existing_ids)
    while len(selected) < limit and any(buckets.values()):
        progress = False
        # Visit countries first and categories second. This keeps one noisy
        # region from consuming the whole daily budget while giving sports,
        # concerts/music, films and adult signals priority within every country.
        for region in DISCOVERY_REGIONS:
            for category in CATEGORY_ORDER:
                bucket = buckets.get((region, category), [])
                if not bucket or len(selected) >= limit:
                    continue
                group = bucket.pop(0)
                channel_id = stable_channel_id(group, used_ids)
                used_ids.add(channel_id)
                selected.append((channel_id, group))
                progress = True
        if not progress:
            break
    stats["selected"] = len(selected)
    stats["capacity"] = max(0, sum(len(bucket) for bucket in buckets.values()))
    return selected, stats


def sidecar_document(
    entries: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "channels": {
            tvg_id: entries[tvg_id]
            for tvg_id in sorted(entries)
        },
    }


def group_from_discovery_entry(
    channel_id: str, entry: dict[str, object]
) -> CandidateGroup:
    """Rebuild a candidate from the validated sidecar without network access."""
    id_match = updater.TVVOO_DISCOVERY_ID_PATTERN.fullmatch(channel_id)
    if id_match is None:
        raise ValueError(f"ID de descubrimiento invalido: {channel_id}")
    source_name = str(entry["sourceName"])
    return CandidateGroup(
        region=str(entry["region"]),
        source_name=source_name,
        aliases=tuple(str(alias) for alias in entry["aliases"]),
        logo=str(entry["logo"]),
        category=str(entry["category"]),
        base_key=identity_key(source_name),
    )


def missing_sidecar_records(
    catalog_lines: list[str], sidecar: dict[str, dict[str, object]]
) -> list[tuple[str, CandidateGroup]]:
    """Return sidecar identities absent from the materialized catalogue."""
    catalog_ids = {
        m3u_attribute(line, "tvg-id")
        for line in catalog_lines
        if line.startswith("#EXTINF:") and m3u_attribute(line, "tvg-id")
    }
    return [
        (channel_id, group_from_discovery_entry(channel_id, entry))
        for channel_id, entry in sorted(sidecar.items())
        if channel_id not in catalog_ids
    ]


def m3u_record(
    channel_id: str, group: CandidateGroup, *, fallback_url: str | None = None
) -> tuple[str, str]:
    display_name = pretty_name(group.source_name, group.region)
    attributes = [
        f'tvg-id="{channel_id}"',
        f'tvg-name="{display_name}"',
        f'tvg-country="{REGION_COUNTRIES[group.region]}"',
        f'tvg-logo="{group.logo}"',
        f'group-title="PRUEBA - {group.category}"',
        'x-resolver="tvvoo"',
        f'x-resolver-endpoint="{updater.TVVOO_STREAM_BASE_URL}"',
        f'x-resolver-ids="{";".join(group.aliases)}"',
        'x-resolver-refresh="on_play"',
        f'x-resolver-recipe="{updater.TVVOO_RECIPE_ID}"',
    ]
    fallback = fallback_url or f"{updater.TVVOO_STREAM_BASE_URL}/{group.aliases[0]}.json"
    return f"#EXTINF:-1 {' '.join(attributes)},{display_name}", fallback


def write_text_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return True


def restore_snapshots(snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.write_bytes(content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Busca candidatos TvVoo nuevos y los agrega al catalogo externo."
    )
    parser.add_argument(
        "--executor",
        choices=("local", "github"),
        default="local",
        help="ejecutor que quedara registrado en el resumen de Actions",
    )
    parser.add_argument(
        "--max-new",
        type=int,
        default=DEFAULT_MAX_NEW,
        help=f"maximo de canales nuevos por ejecucion (1-{MAX_NEW_PER_RUN})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="consulta y muestra candidatos sin escribir archivos",
    )
    parser.add_argument(
        "--reconcile-only",
        action="store_true",
        help="materializa el sidecar ya validado sin consultar catalogos nuevos",
    )
    return parser.parse_args()


def main() -> int:
    global updater
    args = parse_args()
    if args.max_new < 1 or args.max_new > MAX_NEW_PER_RUN:
        raise ValueError(f"--max-new debe estar entre 1 y {MAX_NEW_PER_RUN}")
    if not CATALOG_PATH.is_file():
        raise RuntimeError(f"falta {CATALOG_PATH.name}")

    catalog_lines = CATALOG_PATH.read_text(encoding="utf-8-sig").splitlines()
    sidecar = dict(updater.TVVOO_DISCOVERY_ENTRIES)
    missing_sidecar = missing_sidecar_records(catalog_lines, sidecar)
    existing_ids, existing_aliases, existing_names, _ = existing_inventory(
        catalog_lines, sidecar
    )
    all_groups: list[CandidateGroup] = []
    fetched_regions: list[str] = []
    failures: list[str] = []
    total_metas = 0
    if not args.reconcile_only:
        for region in DISCOVERY_REGIONS:
            try:
                metas = fetch_region_catalog(region)
                fetched_regions.append(region)
                total_metas += len(metas)
                all_groups.extend(candidate_groups(metas, region))
            except Exception as error:
                failures.append(f"{region}: {type(error).__name__}: {error}")

    # A transient outage must not erase or invalidate the existing catalogue.
    if not fetched_regions and not args.reconcile_only and not missing_sidecar:
        print(
            "Descubrimiento TvVoo sin cambios: todos los catálogos fallaron; "
            "se conserva la lista 2 anterior.",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  [AVISO] {failure}", file=sys.stderr)
        return 0

    if args.reconcile_only:
        selected: list[tuple[str, CandidateGroup]] = []
        stats = {"capacity": 0}
    else:
        selected, stats = select_candidates(
            all_groups,
            existing_ids=existing_ids,
            existing_aliases=existing_aliases,
            existing_names=existing_names,
            existing_sidecar_count=len(sidecar),
            max_new=args.max_new,
        )
    print(
        "Descubrimiento TvVoo: "
        f"regiones={len(fetched_regions)}/{len(DISCOVERY_REGIONS)}, "
        f"metas={total_metas}, grupos={len(all_groups)}, "
        f"pendientes_sidecar={len(missing_sidecar)}, "
        f"seleccionados={len(selected)}, "
        f"capacidad_restante={stats['capacity']}"
    )
    for failure in failures:
        print(f"  [AVISO] {failure}", file=sys.stderr)
    if args.dry_run:
        for channel_id, group in missing_sidecar:
            print(
                f"  [RECONCILIAR] {channel_id}: {pretty_name(group.source_name, group.region)}"
            )
        for channel_id, group in selected:
            print(
                f"  [DRY-RUN] {channel_id}: {pretty_name(group.source_name, group.region)} "
                f"[{group.category}] aliases={len(group.aliases)}"
            )
        return 0
    if not selected and not missing_sidecar:
        print("No se detectaron candidatos nuevos ni identidades pendientes.")
        return 0

    affected_paths = (
        DISCOVERY_MAP_PATH,
        CATALOG_PATH,
        updater.EXTERNAL_PLAYLIST,
        updater.SHORT_EXTERNAL_PLAYLIST,
        updater.RESOLVER_CATALOG_PATH,
        updater.DEFAULT_PLAYLIST,
        updater.SHORT_DIRECT_PLAYLIST,
    )
    snapshots = {
        path: path.read_bytes() if path.exists() else None
        for path in affected_paths
    }
    main_before = snapshots[updater.DEFAULT_PLAYLIST]
    try:
        for channel_id, group in missing_sidecar:
            info_line, url_line = m3u_record(channel_id, group)
            catalog_lines.extend((info_line, url_line))
        for channel_id, group in selected:
            sidecar[channel_id] = {
                "name": pretty_name(group.source_name, group.region),
                "aliases": list(group.aliases),
                "region": group.region,
                "sourceName": group.source_name,
                "category": group.category,
                "logo": group.logo,
            }
            info_line, url_line = m3u_record(channel_id, group)
            catalog_lines.extend((info_line, url_line))

        # Reload after the sidecar is written so all updater validators and
        # resolver helpers see the same stable map in this process.
        sidecar_text = json.dumps(
            sidecar_document(sidecar), indent=2, ensure_ascii=False
        ) + "\n"
        write_text_if_changed(DISCOVERY_MAP_PATH, sidecar_text)
        updater = importlib.reload(updater)

        updater.order_channels_by_content(catalog_lines)
        updater.ensure_playlist_epg_url(catalog_lines)
        updater.pin_resolver_metadata(catalog_lines)
        catalog_text = "\n".join(catalog_lines) + "\n"
        catalog_channels = updater.parse_channels(catalog_lines)
        manual_ids = updater.load_manual_main_channel_ids(catalog_channels)
        external_ids = frozenset(
            set(updater.stable_channel_ids(catalog_channels, label=CATALOG_PATH.name))
            - set(manual_ids)
        )
        main_lines = updater.DEFAULT_PLAYLIST.read_text(
            encoding="utf-8-sig"
        ).splitlines()
        external_lines = updater.filter_playlist_to_channel_ids(
            catalog_lines, catalog_channels, external_ids
        )
        updater.write_resolver_catalog()
        updater.validate_resolver_contract(catalog_lines)
        updater.validate_public_playlist_partition(
            catalog_lines, main_lines, external_lines, manual_ids
        )
        if main_before is not None and updater.DEFAULT_PLAYLIST.read_bytes() != main_before:
            raise RuntimeError("el descubrimiento intento modificar la lista principal")
        write_text_if_changed(CATALOG_PATH, catalog_text)
        write_text_if_changed(
            updater.EXTERNAL_PLAYLIST,
            "\n".join(external_lines) + "\n",
        )
        updater.sync_short_playlist_aliases()
        # The contract has to remain valid after the files are materialized,
        # not only in the in-memory candidate list.
        updater.validate_resolver_contract(
            CATALOG_PATH.read_text(encoding="utf-8-sig").splitlines()
        )
        updater.validate_public_playlist_partition(
            CATALOG_PATH.read_text(encoding="utf-8-sig").splitlines(),
            updater.DEFAULT_PLAYLIST.read_text(encoding="utf-8-sig").splitlines(),
            updater.EXTERNAL_PLAYLIST.read_text(encoding="utf-8-sig").splitlines(),
            manual_ids,
        )
    except Exception:
        restore_snapshots(snapshots)
        raise

    print(
        f"Reconciliadas {len(missing_sidecar)} identidades y agregados "
        f"{len(selected)} candidatos nuevos al catalogo externo. "
        f"Total sidecar automatico: {len(sidecar)}/{MAX_TOTAL_DISCOVERED}."
    )
    for channel_id, group in missing_sidecar:
        print(
            f"  [RECONCILIADO] {channel_id}: {pretty_name(group.source_name, group.region)} "
            f"({group.region}, {group.category})"
        )
    for channel_id, group in selected:
        print(
            f"  [NUEVO] {channel_id}: {pretty_name(group.source_name, group.region)} "
            f"({group.region}, {group.category})"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
