"""La Red: guía oficial de lared.cl (pestañas lun..dom = próximos 7 días).

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import html
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    CHILE_TIMEZONE,
    Channel,
    LA_RED_PROGRAMMING_PAGE,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "LA_RED_DAY_INDEX",
    "la_red_html_text",
    "la_red_schedule_items",
    "fetch_la_red_official_epg",
]


LA_RED_DAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def la_red_html_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def la_red_schedule_items(page_html: str) -> dict[int, list[tuple[object, str]]]:
    """Extract the official La Red weekly tabs keyed by weekday index."""
    day_pattern = re.compile(
        r'<div\b'
        r'(?=[^>]*\bid=["\'](?P<day>mon|tue|wed|thu|fri|sat|sun)["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\btab_content\b[^"\']*\bshows-list\b[^"\']*["\'])'
        r'[^>]*>',
        re.IGNORECASE,
    )
    item_pattern = re.compile(
        r'<div\b'
        r'(?=[^>]*\bclass=["\'][^"\']*\bitem\b[^"\']*["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\bparent\b[^"\']*["\'])'
        r'[^>]*>(.*?)'
        r'(?=<div\b'
        r'(?=[^>]*\bclass=["\'][^"\']*\bitem\b[^"\']*["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\bparent\b[^"\']*["\'])'
        r'[^>]*>|$)',
        re.IGNORECASE | re.DOTALL,
    )
    time_pattern = re.compile(
        r'<div\b[^>]*\bclass=["\'][^"\']*\bhour\b[^"\']*["\'][^>]*>'
        r'.*?<p\b[^>]*>(\d{1,2}):(\d{2})</p\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'<[^>]*\bclass=["\'][^"\']*\bprograma-name\b[^"\']*["\'][^>]*>'
        r'(.*?)</p\s*>',
        re.IGNORECASE | re.DOTALL,
    )

    day_markers = list(day_pattern.finditer(page_html))
    schedules: dict[int, list[tuple[object, str]]] = {}
    for index, marker in enumerate(day_markers):
        day_index = LA_RED_DAY_INDEX[marker.group("day").casefold()]
        body_end = (
            day_markers[index + 1].start()
            if index + 1 < len(day_markers)
            else len(page_html)
        )
        day_html = page_html[marker.end() : body_end]
        items: list[tuple[object, str]] = []
        for item_match in item_pattern.finditer(day_html):
            time_match = time_pattern.search(item_match.group(1))
            title_match = title_pattern.search(item_match.group(1))
            if not time_match or not title_match:
                continue
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            if hour > 23 or minute > 59:
                continue
            title = la_red_html_text(title_match.group(1))
            if title:
                items.append(
                    (
                        datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time(),
                        title,
                    )
                )
        if items:
            schedules[day_index] = items
    return schedules


def fetch_la_red_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == "0102" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": LA_RED_PROGRAMMING_PAGE,
    }
    try:
        try:
            status, body, _ = fetch_bytes(
                LA_RED_PROGRAMMING_PAGE,
                headers,
                timeout=60,
                limit=8_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
        except Exception as primary_error:
            # Algunos runners reciben un bloqueo transitorio con urllib. Se
            # reintenta la misma pagina oficial con curl, sin cookies, login,
            # tokens ni relajacion TLS. No se cambia la fuente por Zapping.
            try:
                completed = subprocess.run(
                    [
                        "curl",
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--location",
                        "--max-time",
                        "60",
                        "--user-agent",
                        BROWSER_USER_AGENT,
                        "--header",
                        "Accept: text/html,application/xhtml+xml,*/*;q=0.8",
                        "--header",
                        "Accept-Language: es-CL,es;q=0.9,en;q=0.8",
                        "--header",
                        f"Referer: {LA_RED_PROGRAMMING_PAGE}",
                        LA_RED_PROGRAMMING_PAGE,
                    ],
                    check=True,
                    capture_output=True,
                    timeout=65,
                )
                body = completed.stdout
            except Exception as curl_error:
                raise RuntimeError(
                    f"urllib: {type(primary_error).__name__}: {primary_error}; "
                    f"curl oficial: {type(curl_error).__name__}: {curl_error}"
                ) from curl_error

        schedules = la_red_schedule_items(decode_web_text(body))
        if sum(len(items) for items in schedules.values()) < 5:
            raise ValueError("La Red no publico una parrilla oficial suficiente")

        chile_today = now.astimezone(CHILE_TIMEZONE).date()
        starts: list[tuple[datetime, str]] = []
        for day_index, items in schedules.items():
            # La página publica una parrilla semanal fija (pestañas lun..dom sin
            # fecha, con la de hoy marcada). Cada pestaña es el próximo día con ese
            # nombre a partir de hoy: el domingo en la noche "lunes" es mañana, no
            # el lunes pasado; si no, la guía quedaba sin horas futuras y se descartaba.
            schedule_day = chile_today + timedelta(
                days=(day_index - chile_today.weekday()) % 7
            )
            previous_start: datetime | None = None
            for start_clock, title in items:
                start = datetime.combine(
                    schedule_day, start_clock, tzinfo=CHILE_TIMEZONE
                )
                if previous_start is not None and start <= previous_start:
                    start += timedelta(days=1)
                starts.append((start, title))
                previous_start = start

        unique_starts: dict[datetime, str] = {}
        for start, title in starts:
            unique_starts.setdefault(start, title)
        ordered = sorted(unique_starts.items())

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u La Red importer",
                "source-info-name": LA_RED_PROGRAMMING_PAGE,
            },
        )
        lower_limit = now - timedelta(hours=6)
        upper_limit = now + timedelta(days=8)
        programme_count = 0
        last_stop: datetime | None = None
        for index, (start, title) in enumerate(ordered):
            stop = (
                ordered[index + 1][0]
                if index + 1 < len(ordered)
                else start + timedelta(hours=2)
            )
            if stop <= start:
                continue
            if stop < lower_limit or start > upper_limit:
                continue
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": "0102",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                "Programacion oficial consultada en La Red."
            )
            programme_count += 1
            last_stop = stop if last_stop is None or stop > last_stop else last_stop

        future_limit = now + timedelta(hours=24)
        if programme_count < 5 or last_stop is None or last_stop < future_limit:
            raise ValueError(
                "La Red no publico una parrilla oficial con 24 horas futuras"
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
