"""Sky Sports: guía oficial.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from epg_sources.common import decode_web_text, epg_root

from update_m3u import (
    BROWSER_USER_AGENT,
    Channel,
    SKY_OFFICIAL_EPG_CHANNELS,
    SKY_OFFICIAL_EPG_SCHEDULE_URL,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "fetch_sky_official_epg",
]


def fetch_sky_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the public Sky linear schedule for the four TvVoo Sky channels."""
    targets = {
        channel.tvg_id: SKY_OFFICIAL_EPG_CHANNELS[channel.tvg_id]
        for channel in channels
        if channel.tvg_id in SKY_OFFICIAL_EPG_CHANNELS
    }
    if not targets:
        return None, None
    try:
        root = epg_root("Sky Sports EPG oficial")
        counts = {channel_id: 0 for channel_id in targets}
        seen: set[tuple[str, str, int]] = set()
        start_limit = now - timedelta(hours=6)
        stop_limit = now + timedelta(days=5)
        query_sids = ",".join(sorted(set(targets.values())))
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json,*/*",
            "X-SkyOTT-Territory": "GB",
            "Referer": "https://www.skysports.com/watch/tv-guide",
        }
        for day_offset in range(3):
            schedule_date = (now + timedelta(days=day_offset)).astimezone(timezone.utc).date()
            url = (
                f"{SKY_OFFICIAL_EPG_SCHEDULE_URL}/"
                f"{schedule_date:%Y%m%d}/{query_sids}"
            )
            status, body, _ = fetch_bytes(
                url, headers, timeout=45, limit=8_000_000
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            payload = json.loads(decode_web_text(body))
            schedules = payload.get("schedule") if isinstance(payload, dict) else None
            if not isinstance(schedules, list):
                raise ValueError("Sky no devolvio schedule")
            for schedule in schedules:
                if not isinstance(schedule, dict):
                    continue
                source_id = str(schedule.get("sid", ""))
                target_id = next(
                    (
                        channel_id
                        for channel_id, sid in targets.items()
                        if sid == source_id
                    ),
                    None,
                )
                if target_id is None:
                    continue
                events = schedule.get("events")
                if not isinstance(events, list):
                    continue
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    try:
                        start = datetime.fromtimestamp(
                            int(event["st"]), timezone.utc
                        )
                        stop = start + timedelta(seconds=int(event["d"]))
                    except (KeyError, TypeError, ValueError, OverflowError):
                        continue
                    if stop <= start_limit or start >= stop_limit or stop <= start:
                        continue
                    event_key = (source_id, str(event.get("eid", "")), int(event["st"]))
                    if event_key in seen:
                        continue
                    seen.add(event_key)
                    title = re.sub(r"\s+", " ", str(event.get("t", "")).strip())
                    if not title:
                        continue
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": source_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "en"}).text = title
                    description = re.sub(
                        r"\s+", " ", str(event.get("sy", "")).strip()
                    )
                    if description:
                        ET.SubElement(programme, "desc", {"lang": "en"}).text = description
                    season = event.get("seasonnumber")
                    episode = event.get("episodenumber")
                    if season is not None or episode is not None:
                        episode_element = ET.SubElement(programme, "episode-num", {"system": "onscreen"})
                        episode_element.text = (
                            f"S{int(season):02d}E{int(episode):02d}"
                            if season is not None and episode is not None
                            else str(season if season is not None else episode)
                        )
                    counts[target_id] += 1
        missing = [channel_id for channel_id, count in counts.items() if count == 0]
        if missing:
            raise ValueError("Sky sin eventos vigentes: " + ", ".join(missing))
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
