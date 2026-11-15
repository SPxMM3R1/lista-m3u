"""Parrilla que usa la página oficial de TNT Sports Premium Chile."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlencode

from update_m3u import CHILE_TIMEZONE, Channel, fetch_bytes

__all__ = ["fetch_tnt_sports_premium_epg"]

SOURCE_URL = "https://epg.tapkit.warnermedia.com/cloud-epg-schedule/schedule-sports"
FEED = "CDFH_CL"
TARGET = "PublicDirect.475329883c23116340a88ef6"


def fetch_tnt_sports_premium_epg(channels: list[Channel], now: datetime) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == TARGET for channel in channels):
        return None, None

    today = now.astimezone(CHILE_TIMEZONE).date()
    query = urlencode({"feed": FEED, "from": today - timedelta(days=1), "to": today + timedelta(days=2)})
    status, body, _ = fetch_bytes(
        f"{SOURCE_URL}?{query}", {"Accept": "application/json"}, timeout=20, limit=1_500_000,
    )
    if status != 200:
        return None, f"HTTP {status}"
    schedule = json.loads(body)["com.turner.dmtla.schedule.dto.ScheduleDTO"]
    source_zone = datetime.fromisoformat("2000-01-01T00:00:00" + schedule["offset"]).tzinfo
    if source_zone is None:
        return None, "La parrilla oficial no indicó su zona horaria"
    feed = next((item for item in schedule["feeds"] if item.get("code") == FEED), None)
    if not feed:
        return None, "La fuente no devolvió TNT Sports Premium Chile"

    root = ET.Element("tv", {"source-info-name": "TNT Sports Premium Chile"})
    channel = ET.SubElement(root, "channel", {"id": FEED})
    ET.SubElement(channel, "display-name").text = "TNT Sports Premium"
    seen = set()
    for show in feed.get("shows", []):
        title = (show.get("title") or "").strip() or (show.get("originalTitle") or "").strip()
        try:
            start = datetime.fromisoformat(show["begin"])
            stop = datetime.fromisoformat(show["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=source_zone)
        if stop.tzinfo is None:
            stop = stop.replace(tzinfo=source_zone)
        identity = (start, stop, title)
        if not title or stop <= start or identity in seen:
            continue
        seen.add(identity)
        row = ET.SubElement(root, "programme", {
            "channel": FEED, "start": start.strftime("%Y%m%d%H%M%S %z"),
            "stop": stop.strftime("%Y%m%d%H%M%S %z"),
        })
        ET.SubElement(row, "title", {"lang": "es"}).text = title
        description = (show.get("storyline") or show.get("summary") or "").strip()
        if description:
            ET.SubElement(row, "desc", {"lang": "es"}).text = description
    if not seen:
        return None, "La parrilla oficial no contiene programas válidos"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
