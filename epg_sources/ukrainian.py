"""Canales musicales ucranianos: parrilla semanal oficial.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    Channel,
    UKRAINE_TIMEZONE,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "UKRAINIAN_WEEKDAYS",
    "UKRAINIAN_MUSIC_SCHEDULE_PAGES",
    "ukrainian_weekly_schedule",
    "fetch_ukrainian_music_epg",
]


UKRAINIAN_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


UKRAINIAN_MUSIC_SCHEDULE_PAGES = {
    "M1.ua@SD": ("M1", "https://m1.tv/shedule/"),
    "M2.ua@SD": ("M2", "https://m2.tv/shedule/"),
}


def ukrainian_weekly_schedule(page_html: str) -> dict[int, list[tuple[object, str]]]:
    schedules: dict[int, list[tuple[object, str]]] = {}
    day_pattern = re.compile(
        r'<ul\b[^>]*\bid=["\']day_(monday|tuesday|wednesday|thursday|friday|saturday|sunday)["\'][^>]*>(.*?)</ul\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    item_pattern = re.compile(r"<li\b.*?</li\s*>", re.IGNORECASE | re.DOTALL)
    time_pattern = re.compile(
        r'<div\b[^>]*class=["\']time["\'][^>]*>\s*(\d{1,2}:\d{2})\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'<div\b[^>]*class=["\']title["\'][^>]*>.*?<span\b[^>]*>(.*?)</span\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    for day_name, day_html in day_pattern.findall(page_html):
        items: list[tuple[object, str]] = []
        for item_html in item_pattern.findall(day_html):
            time_match = time_pattern.search(item_html)
            title_match = title_pattern.search(item_html)
            if not time_match or not title_match:
                continue
            try:
                start_clock = datetime.strptime(
                    time_match.group(1), "%H:%M"
                ).time()
            except ValueError:
                continue
            title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1)))
            title = re.sub(r"\s+", " ", title).strip()
            if title:
                items.append((start_clock, title))
        if items:
            schedules[UKRAINIAN_WEEKDAYS[day_name.casefold()]] = sorted(
                items, key=lambda item: item[0]
            )
    return schedules


def fetch_ukrainian_music_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    targets = [
        (channel.tvg_id, channel_name, page_url)
        for channel in channels
        for channel_name, page_url in [
            UKRAINIAN_MUSIC_SCHEDULE_PAGES.get(channel.tvg_id, ("", ""))
        ]
        if channel_name and page_url
    ]
    if not targets:
        return None, {}

    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u Ukrainian music importer",
            "source-info-name": "M1 y M2 oficiales",
        },
    )
    errors: dict[str, str] = {}
    found_by_target = {target_id: 0 for target_id, _, _ in targets}
    now_ukraine = now.astimezone(UKRAINE_TIMEZONE)
    today = now_ukraine.date()

    for target_id, channel_name, page_url in targets:
        try:
            status, body, _ = fetch_bytes(
                page_url,
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
                timeout=60,
                limit=2_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            weekly = ukrainian_weekly_schedule(decode_web_text(body))
            if len(weekly) < 5:
                raise ValueError("la parrilla semanal no contiene suficientes dias")

            for offset in range(-1, 8):
                schedule_day = today + timedelta(days=offset)
                items = weekly.get(schedule_day.weekday(), [])
                if not items:
                    continue
                for index, (start_clock, title) in enumerate(items):
                    start = datetime.combine(
                        schedule_day, start_clock, tzinfo=UKRAINE_TIMEZONE
                    )
                    if index + 1 < len(items):
                        stop = datetime.combine(
                            schedule_day,
                            items[index + 1][0],
                            tzinfo=UKRAINE_TIMEZONE,
                        )
                        while stop <= start:
                            stop += timedelta(days=1)
                    else:
                        next_items = weekly.get((schedule_day.weekday() + 1) % 7, [])
                        if next_items:
                            stop = datetime.combine(
                                schedule_day + timedelta(days=1),
                                next_items[0][0],
                                tzinfo=UKRAINE_TIMEZONE,
                            )
                        else:
                            stop = start + timedelta(hours=6)
                    if stop <= start:
                        stop = start + timedelta(minutes=30)
                    if stop < now - timedelta(hours=6) or start > now + timedelta(days=5):
                        continue
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": target_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "uk"}).text = title
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                        f"Programacion semanal consultada en el sitio oficial de {channel_name}."
                    )
                    found_by_target[target_id] += 1
        except Exception as error:
            errors[target_id] = f"{type(error).__name__}: {error}"

    for target_id, count in found_by_target.items():
        if count == 0:
            errors[target_id] = "la fuente oficial no publico bloques utilizables"
    if not any(found_by_target.values()):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
