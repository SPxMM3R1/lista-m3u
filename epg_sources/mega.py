"""Mega: parrilla oficial publicada como artículo.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    CHILE_TIMEZONE,
    Channel,
    MEGA_PROGRAMMING_PAGE,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "MEGA_MONTHS",
    "mega_jsonld_objects",
    "mega_article_payloads",
    "mega_article_date",
    "mega_schedule_items",
    "fetch_mega_official_epg",
]


MEGA_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def mega_jsonld_objects(value):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from mega_jsonld_objects(graph)
    elif isinstance(value, list):
        for item in value:
            yield from mega_jsonld_objects(item)


def mega_article_payloads(page_html: str) -> list[tuple[str, str]]:
    payloads: list[tuple[str, str]] = []
    blocks = re.findall(
        r'<script\b(?=[^>]*application/ld\+json)[^>]*>(.*?)</script\s*>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for block in blocks:
        try:
            # Mega publica saltos de linea literales dentro de articleBody.
            data = json.loads(html.unescape(block), strict=False)
        except json.JSONDecodeError:
            continue
        for item in mega_jsonld_objects(data):
            headline = item.get("headline") if isinstance(item, dict) else None
            body = item.get("articleBody") if isinstance(item, dict) else None
            if isinstance(headline, str) and isinstance(body, str):
                payloads.append((headline, body))
    return payloads


def mega_article_date(headline: str, year: int):
    match = re.search(
        r"\b(\d{1,2})\s+de\s+([a-z]+)", headline.casefold()
    )
    if not match:
        return None
    month = MEGA_MONTHS.get(match.group(2))
    if month is None:
        return None
    try:
        return datetime(year, month, int(match.group(1))).date()
    except ValueError:
        return None


def mega_schedule_items(article_body: str) -> list[tuple[object, str]]:
    text = html.unescape(article_body)
    text = re.sub(r"<br\s*/?>|</(?:p|li)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    items: list[tuple[object, str]] = []
    for raw_line in re.split(r"\r?\n", text):
        line = re.sub(r"\s+", " ", raw_line).strip(" \t-*\u2022")
        match = re.match(
            r"(.+?):\s*(\d{1,2}):(\d{2})\s*(?:horas?)?\.?$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        hour, minute = int(match.group(2)), int(match.group(3))
        if hour > 23 or minute > 59:
            continue
        title = re.sub(r"\s+", " ", match.group(1)).strip(" .")
        if title:
            items.append((datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time(), title))
    return items


def fetch_mega_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == "0105" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        status, body, _ = fetch_bytes(
            MEGA_PROGRAMMING_PAGE, headers, timeout=60, limit=8_388_608
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        page_html = decode_web_text(body)
        article_urls: list[str] = []
        for raw_url in re.findall(
            r"https://www\.mega\.cl/programacion/[^\"'<>\s]+?\.html",
            page_html,
            flags=re.IGNORECASE,
        ):
            url = html.unescape(raw_url).replace("\\/", "/")
            if url not in article_urls:
                article_urls.append(url)

        payloads = mega_article_payloads(page_html)
        for article_url in article_urls:
            status, article_body, _ = fetch_bytes(
                article_url, headers, timeout=60, limit=8_388_608
            )
            if status == 200:
                payloads.extend(mega_article_payloads(decode_web_text(article_body)))

        today = now.astimezone(CHILE_TIMEZONE).date()
        valid_dates = {
            today + timedelta(days=offset) for offset in range(-1, 8)
        }
        schedules: dict[object, list[tuple[object, str]]] = {}
        for headline, article_body in payloads:
            schedule_day = mega_article_date(headline, today.year)
            if schedule_day not in valid_dates:
                continue
            items = mega_schedule_items(article_body)
            if len(items) >= 3 and schedule_day not in schedules:
                schedules[schedule_day] = items
        if len(schedules) < 2:
            raise ValueError("Mega no publico dos dias de parrilla oficial")

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u Mega importer",
                "source-info-name": MEGA_PROGRAMMING_PAGE,
            },
        )
        for schedule_day in sorted(schedules):
            starts: list[tuple[datetime, str]] = []
            previous_start: datetime | None = None
            for start_clock, title in schedules[schedule_day]:
                start = datetime.combine(
                    schedule_day, start_clock, tzinfo=CHILE_TIMEZONE
                )
                if previous_start is not None and start <= previous_start:
                    start += timedelta(days=1)
                starts.append((start, title))
                previous_start = start
            for index, (start, title) in enumerate(starts):
                stop = (
                    starts[index + 1][0]
                    if index + 1 < len(starts)
                    else start + timedelta(hours=2)
                )
                if stop <= start:
                    stop = start + timedelta(minutes=30)
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": "0105",
                    },
                )
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                    "Programacion oficial consultada en Mega."
                )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
