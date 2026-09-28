"""Chilevisión: guía oficial.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    CHILE_TIMEZONE,
    CHV_PROGRAMMING_PAGE,
    Channel,
    fetch_bytes,
    normalize_epg_title,
    xmltv_format_chile,
)

__all__ = [
    "chv_html_text",
    "chv_schedule_items",
    "fetch_chv_official_epg",
]


def chv_html_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def chv_schedule_items(page_html: str) -> dict[int, list[tuple[object, str]]]:
    """Extract Chilevision's Monday-to-Sunday official schedule cards."""
    list_marker = re.compile(
        r'<div\b(?=[^>]*\bclass=["\'][^"\']*\bschedule-section__list\b[^"\']*["\'])'
        r'[^>]*>',
        re.IGNORECASE,
    )
    article_pattern = re.compile(
        r"<article\b(?=[^>]*\bclass=[\"'][^\"']*\bschedule-card\b[^\"']*[\"'])"
        r"[^>]*>(.*?)</article\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    hour_pattern = re.compile(
        r'<div\b[^>]*\bclass=["\'][^"\']*\bschedule-card__hour\b[^"\']*["\'][^>]*>'
        r"(.*?)</div\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'<(?:strong|div)\b[^>]*\bclass=["\'][^"\']*\bschedule-card__title\b[^"\']*["\'][^>]*>'
        r".*?<a\b[^>]*>(.*?)</a\s*>",
        re.IGNORECASE | re.DOTALL,
    )

    markers = list(list_marker.finditer(page_html))
    schedules: dict[int, list[tuple[object, str]]] = {}
    for index, marker in enumerate(markers[:7]):
        body_end = markers[index + 1].start() if index + 1 < len(markers) else len(page_html)
        body = page_html[marker.end() : body_end]
        items: list[tuple[object, str]] = []
        for article in article_pattern.finditer(body):
            hour_match = hour_pattern.search(article.group(1))
            title_match = title_pattern.search(article.group(1))
            if not hour_match or not title_match:
                continue
            clock_match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", hour_match.group(1))
            if not clock_match:
                continue
            hour, minute = int(clock_match.group(1)), int(clock_match.group(2))
            if hour > 23 or minute > 59:
                continue
            title = chv_html_text(title_match.group(1))
            if title:
                items.append(
                    (
                        datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time(),
                        title,
                    )
                )
        if items:
            schedules[index] = items
    return schedules


def fetch_chv_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import Chilevision's official weekly schedule for the CHV channel."""
    if not any(channel.tvg_id == "0106" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": CHV_PROGRAMMING_PAGE,
    }
    try:
        status, body, _ = fetch_bytes(
            CHV_PROGRAMMING_PAGE,
            headers,
            timeout=60,
            limit=12_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        schedules = chv_schedule_items(decode_web_text(body))
        if sum(len(items) for items in schedules.values()) < 5:
            raise ValueError("Chilevision no publico suficientes bloques oficiales")

        today = now.astimezone(CHILE_TIMEZONE).date()
        week_start = today - timedelta(days=today.weekday())
        starts_by_day: dict[int, list[tuple[datetime, str]]] = {}
        for day_index, items in schedules.items():
            schedule_date = week_start + timedelta(days=day_index)
            starts: list[tuple[datetime, str]] = []
            previous_start: datetime | None = None
            for clock, title in items:
                start = datetime.combine(schedule_date, clock, tzinfo=CHILE_TIMEZONE)
                if previous_start is not None and start <= previous_start:
                    start += timedelta(days=1)
                starts.append((start, normalize_epg_title(title)))
                previous_start = start
            starts_by_day[day_index] = starts

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u Chilevision importer",
                "source-info-name": CHV_PROGRAMMING_PAGE,
            },
        )
        programme_count = 0
        for day_index, starts in sorted(starts_by_day.items()):
            next_day_first = starts_by_day.get(day_index + 1, [])
            for index, (start, title) in enumerate(starts):
                if index + 1 < len(starts):
                    stop = starts[index + 1][0]
                elif next_day_first:
                    stop = next_day_first[0][0]
                else:
                    stop = start + timedelta(hours=2)
                if stop <= start:
                    stop = start + timedelta(minutes=30)
                if stop < now - timedelta(hours=6) or start > now + timedelta(days=8):
                    continue
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": "0106",
                    },
                )
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                    "Programacion oficial consultada en Chilevision."
                )
                programme_count += 1
        if programme_count < 5:
            raise ValueError("Chilevision no publico bloques vigentes suficientes")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
