"""DW English y DW Español: guías oficiales.

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
    Channel,
    DW_ENGLISH_PROGRAMMING_PAGE,
    DW_SPANISH_PROGRAMMING_PAGE,
    fetch_bytes,
    normalize_epg_title,
    xmltv_format,
)

__all__ = [
    "dw_english_schedule_slots",
    "fetch_dw_english_official_epg",
    "fetch_dw_spanish_official_epg",
]


def dw_english_schedule_slots(page_html: str) -> list[tuple[datetime, datetime, str]]:
    """Extract the current DW English slots embedded in the official page."""
    slot_pattern = re.compile(
        r'"startDate":"(?P<start>20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"'
        r'.*?"endDate":"(?P<stop>20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"'
        r'.*?"program":\{"name":"(?P<program>(?:\\.|[^"\\])*)"'
        r'.*?"programElement":\{"name":"(?P<detail>(?:\\.|[^"\\])*)"',
        re.IGNORECASE | re.DOTALL,
    )

    def decode_fragment(value: str) -> str:
        try:
            return str(json.loads(f'"{value}"'))
        except json.JSONDecodeError:
            return html.unescape(value)

    slots: list[tuple[datetime, datetime, str]] = []
    seen: set[tuple[datetime, datetime, str]] = set()
    for match in slot_pattern.finditer(page_html):
        try:
            start = datetime.fromisoformat(match.group("start").replace("Z", "+00:00"))
            stop = datetime.fromisoformat(match.group("stop").replace("Z", "+00:00"))
        except ValueError:
            continue
        if stop <= start:
            continue
        program = re.sub(r"\s+", " ", decode_fragment(match.group("program"))).strip()
        detail = re.sub(r"\s+", " ", decode_fragment(match.group("detail"))).strip()
        if not program:
            continue
        title = program
        if detail and detail.casefold() not in {"news", program.casefold()}:
            title = f"{program}: {detail}"
        item = (start, stop, normalize_epg_title(title))
        if item in seen:
            continue
        seen.add(item)
        slots.append(item)
    return sorted(slots, key=lambda item: (item[0], item[1], item[2]))


def fetch_dw_english_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import DW English's live schedule instead of the empty LV feed."""
    if not any(channel.tvg_id == "DWEnglish.de" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": DW_ENGLISH_PROGRAMMING_PAGE,
    }
    try:
        status, body, _ = fetch_bytes(
            DW_ENGLISH_PROGRAMMING_PAGE,
            headers,
            timeout=60,
            limit=20_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        slots = dw_english_schedule_slots(decode_web_text(body))
        current_slots = [
            slot
            for slot in slots
            if slot[1] > now - timedelta(hours=6)
            and slot[0] < now + timedelta(days=8)
        ]
        if len(current_slots) < 5:
            raise ValueError("DW English no publico suficientes bloques oficiales")
        if max(slot[1] for slot in current_slots) < now + timedelta(hours=4):
            raise ValueError("DW English no publico una ventana futura util")

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u DW English importer",
                "source-info-name": DW_ENGLISH_PROGRAMMING_PAGE,
            },
        )
        for start, stop, title in current_slots:
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format(start),
                    "stop": xmltv_format(stop),
                    "channel": "DWEnglish.de",
                },
            )
            ET.SubElement(programme, "title", {"lang": "en"}).text = title
            ET.SubElement(programme, "desc", {"lang": "en"}).text = (
                "Programacion oficial consultada en DW English."
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_dw_spanish_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import DW Español's official schedule without the DW International feed."""
    if not any(channel.tvg_id == "DW.de" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": DW_SPANISH_PROGRAMMING_PAGE,
    }
    try:
        status, body, _ = fetch_bytes(
            DW_SPANISH_PROGRAMMING_PAGE,
            headers,
            timeout=60,
            limit=20_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        slots = dw_english_schedule_slots(decode_web_text(body))
        current_slots = [
            slot
            for slot in slots
            if slot[1] > now - timedelta(hours=6)
            and slot[0] < now + timedelta(days=8)
        ]
        if len(current_slots) < 5:
            raise ValueError("DW Español no publico suficientes bloques oficiales")
        if max(slot[1] for slot in current_slots) < now + timedelta(hours=4):
            raise ValueError("DW Español no publico una ventana futura util")

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u DW Español importer",
                "source-info-name": DW_SPANISH_PROGRAMMING_PAGE,
            },
        )
        for start, stop, title in current_slots:
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format(start),
                    "stop": xmltv_format(stop),
                    "channel": "DW.de",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                "Programacion oficial consultada en DW Español."
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
