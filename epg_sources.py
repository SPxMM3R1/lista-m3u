"""Fuentes EPG activas y adaptadores historicos.

El camino activo consulta solamente adaptadores oficiales por canal de Lista 1.
Una fuente que deje de responder no bloquea las demas: el canal conserva una
cobertura tecnica ``Live`` hasta la siguiente ejecucion, sin inventar una
parrilla ni recurrir a agregadores.

No se hace asociacion por coincidencia parcial del nombre visible. Cada
adaptador usa IDs exactos de la M3U; el mapa de Zapping queda solo como
adaptador historico y punto de prueba compatible.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any


EPG_SOURCE_MODE = "official-only"
ZAPPING_EPG_SOURCE = "zapping-guia-publica"
ZAPPING_EPG_BASE_URL = "https://guia.zappingtv.com"
ZAPPING_NOWPLAYING_URL = (
    "https://charly.zappingtv.com/v3/webplayer/nowplaying"
)
ZAPPING_NOWPLAYING_CONNECT_HOSTS = (
    "br-apig.zappingtv.com",
    "ec-apig.zappingtv.com",
)

# Asociaciones exactas verificadas con el alias publico de Zapping. No se
# debe completar este mapa con una heuristica basada solo en el nombre.
ZAPPING_EPG_CHANNELS: dict[str, str] = {
    # Senales nacionales y guias ya verificadas.
    "0102": "lared",
    "0104": "tvn",
    "0105": "mega",
    "0106": "chv",
    "0107": "canal13",
    "0201": "24horas",
    "Meganoticias.cl": "meganoticias",
    "1153": "chvnoticias",
    "0124": "t13",
    "45": "ntv",
    "1437": "tvn3",
    "13C.cl@SD": "13cable",
    # Noticias y senales internacionales cuya pagina de guia fue comprobada.
    "DW.de": "dwe",
    "ArirangTV.kr": "arirang",
    "NHKWorldJapan.jp": "nhk",
    "France24.fr": "fr24es",
    "CNN.us@TvVoo": "cnni",
    "AlJazeera.qa": "aljazeeracl",
    "BBCNews.uk": "bbcnews",
    "Vavoo.uk.BBCWORLDNEWS@TvVoo": "bbcnews",
    "Vavoo.pl.CNN@TvVoo": "cnni",
    "Vavoo.ar.ALJAZEERAEN@TvVoo": "aljazeeracl",
    "Vavoo.fr.FRANCE24@TvVoo": "france24frbr",
    # Deportes que Zapping publica con una guia inequívoca.
    "TNTSports3.uk@TvVoo": "tntsports3",
    "TNTSports1.uk@TvVoo": "tntsportshd",
    "ESPN3.ar@TvVoo": "espn3",
    "Vavoo.es.ESPN2@TvVoo": "espn2",
    "Vavoo.nl.ESPN2@TvVoo": "espn2",
    "TyCSports.ar": "tycsports",
    # Otras senales cuyo nombre publico coincide de forma exacta.
    "RedBullWorldEnglish.int": "redbulltv",
    "Vavoo.it.CARTOONITO@TvVoo": "cartoonito",
}

# Nombre descriptivo de las fuentes antiguas. Se usa en informes para que no
# se confunda "sin asociacion Zapping" con "canal eliminado".
LEGACY_SOURCE_GROUPS: Mapping[str, str] = {
    "epgshare": "feeds EPGShare por pais",
    "official": "adaptadores oficiales individuales",
    "tecnocentro": "TecnoCentro",
    "ukrainian": "parrillas oficiales M1/M2",
    "redbull": "EPG oficial/relay de Red Bull",
    "published": "epg.xml publicada anteriormente",
}

# Fuentes antiguas conservadas solo para auditoria y eventual recuperacion. No
# se descargan cuando EPG_SOURCE_MODE es "official-only". Mantenerlas aqui
# evita que una futura recuperacion dependa de URLs repartidas por el
# actualizador principal.
LEGACY_EPG_BACKUP_URLS: Mapping[str, str] = {
    "cl": "https://epgshare01.online/epgshare01/epg_ripper_CL1.xml.gz",
    "es": "https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz",
    "fr": "https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
    "de": "https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz",
    "uk1": "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "ar1": "https://epgshare01.online/epgshare01/epg_ripper_AR1.xml.gz",
    "pt1": "https://epgshare01.online/epgshare01/epg_ripper_PT1.xml.gz",
    "nz1": "https://epgshare01.online/epgshare01/epg_ripper_NZ1.xml.gz",
    "au1": "https://epgshare01.online/epgshare01/epg_ripper_AU1.xml.gz",
    "us2": "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "pl": "https://epgshare01.online/epgshare01/epg_ripper_PL1.xml.gz",
    "lv": "https://epgshare01.online/epgshare01/epg_ripper_LV1.xml.gz",
    "nl": "https://epgshare01.online/epgshare01/epg_ripper_NL1.xml.gz",
    "plex1": "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz",
    "tr1": "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "sg1": "https://epgshare01.online/epgshare01/epg_ripper_SG1.xml.gz",
    "ng1": "https://epgshare01.online/epgshare01/epg_ripper_NG1.xml.gz",
    "it1": "https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz",
    "pluto": "https://i.mjh.nz/PlutoTV/all.xml.gz",
}


FetchBytes = Callable[..., tuple[int, bytes, str]]
ScheduleRows = Callable[[str], list[tuple[datetime, str]]]
DecodeText = Callable[[bytes], str]
FormatTimestamp = Callable[[datetime], str]
RunProcess = Callable[..., Any]


def zapping_coverage(
    channel_ids: Iterable[str],
    *,
    aliases: Mapping[str, str] = ZAPPING_EPG_CHANNELS,
) -> dict[str, object]:
    """Return deterministic coverage without guessing channel identities."""

    unique_ids = sorted({str(channel_id) for channel_id in channel_ids if channel_id})
    mapped = {
        channel_id: aliases[channel_id]
        for channel_id in unique_ids
        if channel_id in aliases
    }
    unmapped = [channel_id for channel_id in unique_ids if channel_id not in mapped]
    return {
        "source": ZAPPING_EPG_SOURCE,
        "mode": EPG_SOURCE_MODE,
        "catalog_ids": len(unique_ids),
        "mapped_ids": len(mapped),
        "unmapped_ids": len(unmapped),
        "mapped": mapped,
        "unmapped": unmapped,
    }


def zapping_html_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def zapping_schedule_rows(page_html: str) -> list[tuple[datetime, str]]:
    """Extract absolute-start programmes from a public Zapping guide page."""

    today_marker = re.search(
        r'<div\b[^>]*class=["\'][^"\']*\btoday-schedule\b[^"\']*["\']',
        page_html,
        re.IGNORECASE,
    )
    if not today_marker:
        raise ValueError("la guia Zapping no contiene la parrilla del dia")

    rows: list[tuple[datetime, str]] = []
    current_html = page_html[: today_marker.start()]
    current_info = re.search(r'href=["\']info/(\d+)["\']', current_html, re.IGNORECASE)
    current_title = re.search(
        r"<h4\b[^>]*>(.*?)</h4\s*>",
        current_html,
        re.IGNORECASE | re.DOTALL,
    )
    if current_info and current_title:
        rows.append(
            (
                datetime.fromtimestamp(int(current_info.group(1)), timezone.utc),
                zapping_html_text(current_title.group(1)),
            )
        )

    item_pattern = re.compile(
        r'<a\b'
        r'(?=[^>]*\bhref=["\']info/(\d+)["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\bepg-item\b[^"\']*["\'])'
        r'[^>]*>(.*?)</a\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'class=["\'][^"\']*\bepg-schedule-title\b[^"\']*["\'][^>]*>(.*?)</p\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in item_pattern.finditer(page_html[today_marker.start() :]):
        title_match = title_pattern.search(match.group(2))
        if not title_match:
            continue
        title = zapping_html_text(title_match.group(1))
        if not title:
            continue
        start = datetime.fromtimestamp(int(match.group(1)), timezone.utc)
        rows.append((start, title))

    unique: dict[datetime, str] = {}
    for start, title in rows:
        unique.setdefault(start, title)
    return sorted(unique.items())


def fetch_zapping_nowplaying_bytes(
    *,
    fetch_bytes: FetchBytes,
    user_agent: str,
    run_process: RunProcess = subprocess.run,
) -> bytes:
    """Fetch the public schedule once, preserving normal TLS validation."""

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json,*/*",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    primary_error: Exception | None = None
    try:
        status, body, _ = fetch_bytes(
            ZAPPING_NOWPLAYING_URL,
            headers,
            timeout=60,
            limit=4_000_000,
            data=b"data=",
        )
        if status == 200:
            return body
        primary_error = ValueError(f"HTTP {status}")
    except Exception as error:
        primary_error = error

    # GitHub puede recibir un rechazo regional. Los destinos son fijos y solo
    # cambian el peer TCP; la URL, el Host y el SNI siguen siendo los oficiales.
    curl_errors: list[str] = []
    for connect_host in ZAPPING_NOWPLAYING_CONNECT_HOSTS:
        try:
            completed = run_process(
                [
                    "curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--max-time",
                    "30",
                    "--connect-to",
                    f"charly.zappingtv.com:443:{connect_host}:443",
                    "--header",
                    "Content-Type: application/x-www-form-urlencoded",
                    "--data",
                    "data=",
                    ZAPPING_NOWPLAYING_URL,
                ],
                check=True,
                capture_output=True,
                timeout=35,
            )
            if not completed.stdout:
                raise ValueError("nowplaying respondio sin contenido")
            if len(completed.stdout) > 4_000_000:
                raise ValueError("nowplaying excede el limite de 4 MB")
            return completed.stdout
        except Exception as curl_error:
            curl_errors.append(
                f"{connect_host}: {type(curl_error).__name__}: {curl_error}"
            )
    raise RuntimeError(
        f"urllib: {type(primary_error).__name__}: {primary_error}; "
        "curl regional: " + " | ".join(curl_errors)
    )


def fetch_zapping_epg(
    channels: Sequence[object],
    now: datetime,
    *,
    fetch_bytes: FetchBytes,
    user_agent: str,
    schedule_rows: ScheduleRows = zapping_schedule_rows,
    decode_text: DecodeText,
    format_timestamp: FormatTimestamp,
    nowplaying_fetcher: Callable[[], bytes] | None = None,
    run_process: RunProcess = subprocess.run,
) -> tuple[bytes | None, dict[str, str]]:
    """Fetch each mapped Zapping page independently.

    ``nowplaying`` is requested once and is used only as the per-channel
    fallback. One failed page therefore cannot discard the valid schedules of
    all the other channels.
    """

    targets = [
        (str(getattr(channel, "tvg_id", "")), ZAPPING_EPG_CHANNELS[getattr(channel, "tvg_id", "")])
        for channel in channels
        if getattr(channel, "tvg_id", "") in ZAPPING_EPG_CHANNELS
    ]
    if not targets:
        return None, {}

    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u Zapping guide importer",
            "source-info-name": ZAPPING_EPG_BASE_URL,
        },
    )

    nowplaying_blocks: dict[str, list[tuple[datetime, datetime, str]]] = {}
    nowplaying_error: str | None = None
    try:
        if nowplaying_fetcher is None:
            nowplaying_fetcher = lambda: fetch_zapping_nowplaying_bytes(
                fetch_bytes=fetch_bytes,
                user_agent=user_agent,
                run_process=run_process,
            )
        body = nowplaying_fetcher()
        payload = json.loads(body.decode("utf-8"))
        schedule = payload.get("data", {}).get("schedule", {})
        if not isinstance(schedule, dict):
            raise ValueError("nowplaying no contiene un mapa schedule")
        for target_id, alias in targets:
            entry = schedule.get(alias)
            if not isinstance(entry, dict):
                continue
            cards: list[dict[str, object]] = []
            for key in ("past", "now", "next"):
                value = entry.get(key)
                if isinstance(value, list):
                    cards.extend(card for card in value if isinstance(card, dict))
                elif isinstance(value, dict):
                    cards.append(value)
            unique_cards: dict[tuple[datetime, datetime], str] = {}
            for card in cards:
                try:
                    start = datetime.fromtimestamp(
                        int(card["start_time"]), timezone.utc
                    )
                    stop = datetime.fromtimestamp(
                        int(card["end_time"]), timezone.utc
                    )
                except (KeyError, TypeError, ValueError, OSError):
                    continue
                title = str(
                    card.get("title") or card.get("program_title") or ""
                ).strip()
                if not title or stop <= start:
                    continue
                if stop < now - timedelta(hours=6) or start > now + timedelta(days=4):
                    continue
                unique_cards[(start, stop)] = title
            blocks = [
                (start, stop, title)
                for (start, stop), title in sorted(unique_cards.items())
            ]
            if blocks:
                nowplaying_blocks[target_id] = blocks
    except Exception as error:
        nowplaying_error = f"{type(error).__name__}: {error}"

    def fetch_target(
        target_id: str, slug: str
    ) -> tuple[str, list[tuple[datetime, datetime, str]], str | None]:
        url = f"{ZAPPING_EPG_BASE_URL}/{slug}/"
        try:
            status, body, _ = fetch_bytes(
                url,
                {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
                timeout=60,
                limit=4_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            rows = schedule_rows(decode_text(body))
            if len(rows) < 3:
                raise ValueError("la guia Zapping contiene muy pocos bloques")

            blocks: list[tuple[datetime, datetime, str]] = []
            for index, (start, title) in enumerate(rows):
                stop = (
                    rows[index + 1][0]
                    if index + 1 < len(rows)
                    else start + timedelta(hours=3)
                )
                if stop <= start:
                    continue
                if stop < now - timedelta(hours=6) or start > now + timedelta(days=4):
                    continue
                blocks.append((start, stop, title))
            if not blocks:
                raise ValueError("la guia Zapping no publico bloques utilizables")
            return target_id, blocks, None
        except Exception as error:
            fallback = nowplaying_blocks.get(target_id, [])
            if fallback:
                return target_id, fallback, None
            details = f"{type(error).__name__}: {error}"
            if nowplaying_error:
                details += f"; nowplaying: {nowplaying_error}"
            return target_id, [], details

    results: dict[str, list[tuple[datetime, datetime, str]]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(targets))) as pool:
        futures = {
            pool.submit(fetch_target, target_id, slug): target_id
            for target_id, slug in targets
        }
        for future in as_completed(futures):
            target_id, blocks, error = future.result()
            if blocks:
                results[target_id] = blocks
            if error:
                errors[target_id] = error

    for target_id, _ in targets:
        for start, stop, title in results.get(target_id, []):
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": format_timestamp(start),
                    "stop": format_timestamp(stop),
                    "channel": target_id,
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            description = (
                "Parrilla publica de Zapping Chile y Simply.TV para TVN3, "
                "senal oficial de TVN."
                if target_id == "1437"
                else "Programacion publica consultada en la guia de Zapping Chile."
            )
            ET.SubElement(programme, "desc", {"lang": "es"}).text = description

    if not results:
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
