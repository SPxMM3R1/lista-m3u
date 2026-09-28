"""NHK World Japan: guía oficial.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    Channel,
    NHK_TIMEZONE,
    NHK_WORLD_EPG_BASE_URL,
    NHK_WORLD_LIVE_PAGE,
    fetch_bytes,
    xmltv_format,
)

__all__ = [
    "fetch_nhk_official_epg",
]


def fetch_nhk_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the English NHK World schedule instead of domestic NHK XMLTV."""
    if not any(channel.tvg_id == "NHKWorldJapan.jp" for channel in channels):
        return None, None

    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": NHK_WORLD_LIVE_PAGE,
    }
    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u NHK World importer",
            "source-info-name": NHK_WORLD_LIVE_PAGE,
        },
    )
    records: list[dict[str, object]] = []
    source_errors: list[str] = []
    nhk_today = now.astimezone(NHK_TIMEZONE).date()

    for offset in range(-1, 10):
        schedule_day = nhk_today + timedelta(days=offset)
        url = f"{NHK_WORLD_EPG_BASE_URL}/{schedule_day:%Y%m%d}.json"
        try:
            status, body, _ = fetch_bytes(
                url,
                headers,
                timeout=60,
                limit=2_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            payload = json.loads(decode_web_text(body))
            items = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                raise ValueError("NHK no publico un campo data valido")
        except Exception as error:
            source_errors.append(f"{schedule_day}: {error}")
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            start_text = str(item.get("startTime", "")).strip()
            stop_text = str(item.get("endTime", "")).strip()
            if not start_text or not stop_text:
                continue
            try:
                start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
                stop = datetime.fromisoformat(stop_text.replace("Z", "+00:00"))
            except ValueError:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=NHK_TIMEZONE)
            if stop.tzinfo is None:
                stop = stop.replace(tzinfo=NHK_TIMEZONE)
            if stop <= start:
                continue

            is_extract_marker = item.get("extractProgram") in (1, "1", True)
            if is_extract_marker:
                # NHK World uses one-minute INFO markers between some shows.
                # Its official page extends the preceding show to the marker's
                # end and hides the marker itself.
                if records and stop > records[-1]["stop"]:
                    records[-1]["stop"] = stop
                continue
            if item.get("wstrm") not in (1, "1", True):
                continue

            title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
            if not title or title.casefold() == "info":
                continue
            episode_title = re.sub(
                r"\s+", " ", str(item.get("episodeTitle", ""))
            ).strip()
            description = re.sub(
                r"\s+", " ", str(item.get("description", ""))
            ).strip()
            records.append(
                {
                    "start": start,
                    "stop": stop,
                    "title": title,
                    "episode_title": episode_title,
                    "description": description,
                    "link": str(item.get("link", "")).strip(),
                }
            )

    seen: set[tuple[str, str, str]] = set()
    programme_count = 0
    lower_limit = now - timedelta(hours=6)
    upper_limit = now + timedelta(days=8)
    # El JSON oficial puede entregar una tarjeta tardia encima de otra en
    # los cambios de bloque. Conservamos el programa que comienza despues,
    # recortamos solo el borde del anterior y descartamos tarjetas totalmente
    # contenidas; asi la fuente sigue siendo oficial y XMLTV no se solapa.
    ordered_records: list[dict[str, object]] = []
    for record in sorted(records, key=lambda value: value["start"]):
        start = record["start"]
        stop = record["stop"]
        title = record["title"]
        if not isinstance(start, datetime) or not isinstance(stop, datetime):
            continue
        if not isinstance(title, str) or stop < lower_limit or start > upper_limit:
            continue
        key = (start.isoformat(), stop.isoformat(), title)
        if key in seen:
            continue
        seen.add(key)
        if ordered_records:
            previous = ordered_records[-1]
            previous_start = previous["start"]
            previous_stop = previous["stop"]
            if isinstance(previous_start, datetime) and isinstance(previous_stop, datetime):
                if start < previous_stop:
                    if stop <= previous_stop:
                        continue
                    previous["stop"] = start
                    if start <= previous_start:
                        ordered_records.pop()
        if stop <= start:
            continue
        ordered_records.append(record)

    for record in ordered_records:
        start = record["start"]
        stop = record["stop"]
        title = record["title"]
        if not isinstance(start, datetime) or not isinstance(stop, datetime):
            continue
        if not isinstance(title, str) or stop < lower_limit or start > upper_limit:
            continue
        programme = ET.SubElement(
            root,
            "programme",
            {
                "start": xmltv_format(start),
                "stop": xmltv_format(stop),
                "channel": "NHKWorldJapan.jp",
            },
        )
        ET.SubElement(programme, "title", {"lang": "en"}).text = title
        episode_title = record["episode_title"]
        if isinstance(episode_title, str) and episode_title:
            ET.SubElement(programme, "sub-title", {"lang": "en"}).text = (
                episode_title
            )
        description = record["description"]
        if isinstance(description, str) and description:
            ET.SubElement(programme, "desc", {"lang": "en"}).text = description
        link = record["link"]
        if isinstance(link, str) and link:
            ET.SubElement(programme, "url").text = link
        programme_count += 1

    future_limit = now + timedelta(hours=24)
    has_future_schedule = any(
        isinstance(record["stop"], datetime) and record["stop"] >= future_limit
        for record in records
    )
    if programme_count < 5 or not has_future_schedule:
        detail = "; ".join(source_errors[:2])
        suffix = f" ({detail})" if detail else ""
        raise_error = (
            "NHK World publico una parrilla oficial demasiado corta"
            if programme_count < 5
            else "NHK World no publico 24 horas futuras"
        )
        return None, f"ValueError: {raise_error}{suffix}"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
