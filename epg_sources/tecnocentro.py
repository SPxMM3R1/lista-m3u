"""TecnoCentro: respaldo por canal.

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
    Channel,
    EPG_PROGRAMME_SOURCES,
    TECNOCENTRO_BACKUP_CHANNELS,
    TECNOCENTRO_EPG_URL,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "tecnocentro_schedule_items",
    "fetch_tecnocentro_epg",
]


def tecnocentro_schedule_items(page_html: str) -> list[tuple[str, str, str]]:
    item_pattern = re.compile(
        r'<div class="schedule-item[^>]*>\s*'
        r'<div class="schedule-time">\s*'
        r'(?:<span[^>]*>)?([^<\s]+)(?:</span>)?\s*-\s*([^<]+?)\s*</div>\s*'
        r'<div class="schedule-title">\s*(.*?)\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )
    items: list[tuple[str, str, str]] = []
    for start_text, stop_text, raw_title in item_pattern.findall(page_html):
        title = html.unescape(re.sub(r"<[^>]+>", "", raw_title))
        title = re.sub(r"\s+", " ", title).strip()
        if title:
            items.append((start_text.strip(), stop_text.strip(), title))
    return items


def fetch_tecnocentro_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    available_ids = {channel.tvg_id for channel in channels if channel.tvg_id}
    target_ids = {
        target_id
        for target_id in available_ids
        if EPG_PROGRAMME_SOURCES.get(target_id, ("", ""))[0] == "tecnocentro"
    }
    source_ids = {
        target_id: EPG_PROGRAMME_SOURCES[target_id][1]
        for target_id in target_ids
    }
    # Los respaldos TecnoCentro de canales con fuente oficial/agregada tambien
    # se descargan: si su parrilla queda parcial, el respaldo la completa.
    for target_id in sorted(available_ids & set(TECNOCENTRO_BACKUP_CHANNELS)):
        source_ids.setdefault(target_id, TECNOCENTRO_BACKUP_CHANNELS[target_id])
    target_ids = set(source_ids)
    if not target_ids:
        return None, {}
    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u tecnocentro importer",
            "source-info-name": TECNOCENTRO_EPG_URL,
        },
    )
    errors: dict[str, str] = {}
    found_by_target = {target_id: 0 for target_id in target_ids}
    chile_today = now.astimezone(CHILE_TIMEZONE).date()
    seen: set[tuple[str, str, str, str]] = set()

    for offset in (0, 1):
        schedule_day = chile_today + timedelta(days=offset)
        for target_id, source_id in source_ids.items():
            url = (
                f"{TECNOCENTRO_EPG_URL}?view=schedule&channel={source_id}"
                f"&date={schedule_day.isoformat()}"
            )
            try:
                status, body, _ = fetch_bytes(
                    url,
                    {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/html,*/*"},
                    timeout=60,
                    limit=262_144,
                )
                if status != 200:
                    raise ValueError(f"HTTP {status}")
                items = tecnocentro_schedule_items(decode_web_text(body))
                parsed_items: list[tuple[object, object, str]] = []
                for start_text, stop_text, title in items:
                    try:
                        start_clock = datetime.strptime(start_text, "%H:%M").time()
                        stop_clock = datetime.strptime(stop_text, "%H:%M").time()
                    except ValueError:
                        continue
                    parsed_items.append((start_clock, stop_clock, title))
                if not parsed_items:
                    continue

                first_start_clock, first_stop_clock, _ = parsed_items[0]
                base_day = schedule_day
                if first_start_clock.hour >= 18 and first_stop_clock.hour <= 6:
                    base_day -= timedelta(days=1)
                previous_start: datetime | None = None
                for start_clock, stop_clock, title in parsed_items:
                    start = datetime.combine(
                        base_day, start_clock, tzinfo=CHILE_TIMEZONE
                    )
                    while previous_start is not None and start <= previous_start:
                        start += timedelta(days=1)
                    stop = datetime.combine(
                        start.date(), stop_clock, tzinfo=CHILE_TIMEZONE
                    )
                    while stop <= start:
                        stop += timedelta(days=1)
                    previous_start = start
                    is_requested_day = start.date() == schedule_day
                    is_current_previous_day = (
                        start.date() == schedule_day - timedelta(days=1) and stop > now
                    )
                    if not (is_requested_day or is_current_previous_day):
                        continue
                    if stop < now - timedelta(hours=6) or start > now + timedelta(days=5):
                        continue
                    key = (target_id, start.isoformat(), stop.isoformat(), title)
                    if key in seen:
                        continue
                    seen.add(key)
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": source_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "es"}).text = title
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                        "Programacion diaria consultada en TecnoCentro."
                    )
                    found_by_target[target_id] += 1
            except Exception as error:
                errors[target_id] = f"{type(error).__name__}: {error}"

    for target_id, count in found_by_target.items():
        if count == 0:
            errors[target_id] = "TecnoCentro no publico bloques para este canal"

    if not any(found_by_target.values()):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
