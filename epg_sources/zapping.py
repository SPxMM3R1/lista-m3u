"""Zapping: guía por canal.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    Channel,
    ZAPPING_EPG_BASE_URL,
    ZAPPING_EPG_CHANNELS,
    ZAPPING_NOWPLAYING_CONNECT_HOSTS,
    ZAPPING_NOWPLAYING_URL,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "zapping_html_text",
    "zapping_schedule_rows",
    "fetch_zapping_nowplaying_bytes",
    "fetch_zapping_page_bytes",
    "fetch_zapping_epg",
]


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
    current_title = re.search(r"<h4\b[^>]*>(.*?)</h4\s*>", current_html, re.IGNORECASE | re.DOTALL)
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


def fetch_zapping_nowplaying_bytes() -> bytes:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
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

    # El runner ya incluye curl. Los argumentos son fijos, no usan shell y
    # prueban frontales regionales equivalentes sin relajar la verificacion TLS.
    curl_errors: list[str] = []
    for connect_host in ZAPPING_NOWPLAYING_CONNECT_HOSTS:
        try:
            completed = subprocess.run(
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


def fetch_zapping_page_bytes(url: str) -> bytes:
    """Fetch a public Zapping guide page, with regional fronts as fallback.

    Zapping bloquea por pais: el acceso directo puede fallar fuera de Chile.
    Los frontales regionales (hosts de la propia Zapping) mantienen TLS
    verificado y se intentan solo si el acceso directo falla.
    """
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    primary_error: Exception | None = None
    try:
        status, body, _ = fetch_bytes(url, headers, timeout=60, limit=6_000_000)
        if status == 200:
            return body
        primary_error = ValueError(f"HTTP {status}")
    except Exception as error:
        primary_error = error

    parsed = urlparse(url)
    if parsed.hostname != "guia.zappingtv.com":
        raise primary_error
    curl_errors: list[str] = []
    for connect_host in ZAPPING_NOWPLAYING_CONNECT_HOSTS:
        try:
            completed = subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--max-time",
                    "30",
                    "--connect-to",
                    f"guia.zappingtv.com:443:{connect_host}:443",
                    "--header",
                    "Accept: text/html,application/xhtml+xml,*/*",
                    url,
                ],
                check=True,
                capture_output=True,
                timeout=35,
            )
            if not completed.stdout:
                raise ValueError("la guia Zapping respondio sin contenido")
            if len(completed.stdout) > 6_000_000:
                raise ValueError("la guia Zapping excede el limite de 6 MB")
            return completed.stdout
        except Exception as curl_error:
            curl_errors.append(
                f"{connect_host}: {type(curl_error).__name__}: {curl_error}"
            )
    raise RuntimeError(
        f"directo: {type(primary_error).__name__}: {primary_error}; "
        "curl regional: " + " | ".join(curl_errors)
    )


def fetch_zapping_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    targets = [
        (channel.tvg_id, ZAPPING_EPG_CHANNELS[channel.tvg_id])
        for channel in channels
        if channel.tvg_id in ZAPPING_EPG_CHANNELS
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

    # El HTML de la guia contiene hoy y manana, pero bloquea por pais a los
    # runners de GitHub. El endpoint publico nowplaying no requiere sesion y
    # entrega pasado inmediato, programa actual y proximos con inicio/fin
    # absolutos. Se consulta una sola vez y se usa solo si falla la pagina
    # completa de un canal.
    nowplaying_blocks: dict[str, list[tuple[datetime, datetime, str]]] = {}
    nowplaying_error: str | None = None
    try:
        body = fetch_zapping_nowplaying_bytes()
        payload = json.loads(body.decode("utf-8"))
        schedule = payload.get("data", {}).get("schedule", {})
        if not isinstance(schedule, dict):
            raise ValueError("nowplaying no contiene un mapa schedule")
        for target_id, alias in targets:
            entry = schedule.get(alias)
            if not isinstance(entry, dict):
                continue
            cards: list[dict] = []
            for key in ("past", "now", "next"):
                value = entry.get(key)
                if isinstance(value, list):
                    cards.extend(card for card in value if isinstance(card, dict))
                elif isinstance(value, dict):
                    cards.append(value)
            unique_cards: dict[tuple[datetime, datetime], str] = {}
            for card in cards:
                try:
                    start = datetime.fromtimestamp(int(card["start_time"]), timezone.utc)
                    stop = datetime.fromtimestamp(int(card["end_time"]), timezone.utc)
                except (KeyError, TypeError, ValueError, OSError):
                    continue
                title = str(card.get("title") or card.get("program_title") or "").strip()
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
            body = fetch_zapping_page_bytes(url)
            rows = zapping_schedule_rows(decode_web_text(body))
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

    # Cada pagina es una fuente independiente. La concurrencia reduce la
    # duracion del unico run de Actions sin mezclar resultados ni permitir que
    # un fallo de otro canal descarte la parrilla valida de TVN3.
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
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
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

    # La fuente es opcional y se selecciona por canal. Una pagina que falle no
    # invalida los bloques validos de las otras paginas; build_epg usa esos
    # bloques y deja el fallback configurado para los canales sin cobertura.
    if not results:
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
