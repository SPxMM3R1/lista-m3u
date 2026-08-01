#!/usr/bin/env python3
"""Build the optional public sports block for the main M3U playlist."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse


SPORTS_BLOCK_START = "# AUTO SPORTS EVENTS BEGIN"
SPORTS_BLOCK_END = "# AUTO SPORTS EVENTS END"
IPTV_ORG_STREAMS_URL = "https://iptv-org.github.io/api/streams.json"
SPORTS_EVENT_FEED_ENV = "SPORTS_EVENT_FEED_URL"
SPORTS_TIMEOUT = int(os.environ.get("SPORTS_HLS_TIMEOUT", "15"))

SPORTS_CHANNELS = {
    "beINSPORTSXTRA.us": {
        "name": "beIN SPORTS XTRA",
        "tvg_id": "beINSPORTSXTRA.us",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/bein-sports-xtra-us.png",
    },
    "beINSPORTSXTRAenEspanol.us": {
        "name": "beIN SPORTS XTRA en Espanol",
        "tvg_id": "beINSPORTSXTRAenEspanol.us",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/bein-sports-xtra-espanol-us.png",
    },
    "FUELTV.pt": {
        "name": "FUEL TV",
        "tvg_id": "FUELTV.pt",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/portugal/fueltv-hd-pt.png",
    },
    "ESPN8TheOcho.us": {
        "name": "ESPN8: The Ocho",
        "tvg_id": "ESPN8TheOcho.us",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/espn-us.png",
    },
    "NHLNetwork.us": {
        "name": "NHL Network",
        "tvg_id": "NHLNetwork.us",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/nhl-network-us.png",
    },
    "NBCSportsNOW.us": {
        "name": "NBC Sports NOW",
        "tvg_id": "NBCSportsNOW.us",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/nbc-sports-live-extra-us.png",
    },
    "TSNTheOcho.ca": {
        "name": "TSN The Ocho",
        "tvg_id": "TSNTheOcho.ca",
        "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/canada/tsn-ca.png",
    },
}

# These are public CDN families used by the curated sports channel sources.
# Arbitrary embeds, shortened links, and player pages are deliberately ignored.
TRUSTED_HOST_SUFFIXES = (
    "amagi.tv",
    "akamaized.net",
    "akamaihd.net",
    "cloudfront.net",
    "cbsivideo.com",
    "mediatailor.us-west-2.amazonaws.com",
    "tubi.video",
    "wurl.com",
)


@dataclass(frozen=True)
class SportsEntry:
    channel_id: str
    name: str
    tvg_id: str
    logo: str
    url: str
    resolution: str
    source_url: str
    detail: str


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
    }


def _fetch_bytes(url: str, *, limit: int = 524_288) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(request, timeout=SPORTS_TIMEOUT) as response:
        return response.status, response.read(limit), response.geturl()


def _fetch_json(url: str) -> object:
    status, body, _ = _fetch_bytes(url, limit=20_971_520)
    if status != 200:
        raise RuntimeError(f"HTTP {status} al consultar la fuente deportiva")
    return json.loads(body.decode("utf-8", "replace"))


def _clean(value: object, fallback: str = "") -> str:
    text = str(value or fallback).replace("\r", " ").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text).replace('"', "'")


def _trusted_direct_url(url: object) -> bool:
    if not isinstance(url, str) or not url.lower().startswith("https://"):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return bool(host) and any(host == suffix or host.endswith("." + suffix) for suffix in TRUSTED_HOST_SUFFIXES)


def _https_url(url: object) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://") and bool(urlparse(url).hostname)


def _quality_score(value: object) -> int:
    match = re.search(r"(?:^|[^0-9])(\d{3,4})p(?:$|[^0-9])", str(value or ""), re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _host_score(url: str) -> int:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("amagi.tv") or host.endswith("cloudfront.net"):
        return 4
    if host.endswith("akamaized.net") or host.endswith("akamaihd.net"):
        return 3
    if host.endswith("mediatailor.us-west-2.amazonaws.com") or host.endswith("wurl.com"):
        return 2
    return 1


def _variants(text: str, base_url: str) -> list[tuple[int, str, str]]:
    lines = [line.strip() for line in text.splitlines()]
    variants: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        resolution = re.search(r"\bRESOLUTION=(\d+)x(\d+)", line)
        height = int(resolution.group(2)) if resolution else 0
        for candidate in lines[index + 1 :]:
            if not candidate or candidate.startswith("#"):
                continue
            variants.append((height, urljoin(base_url, candidate), resolution.group(0).split("=", 1)[-1] if resolution else "Auto"))
            break
    return variants


def _first_segment(text: str, base_url: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            for candidate in lines[index + 1 :]:
                if candidate and not candidate.startswith("#"):
                    return urljoin(base_url, candidate)
            break
    return ""


def validate_hls(url: str) -> tuple[bool, str, str, str]:
    """Return ok, best playable URL, resolution, and a compact diagnostic."""
    try:
        status, body, final_url = _fetch_bytes(url)
        text = body.decode("utf-8", "replace").lstrip("\ufeff\r\n ")
        if status != 200 or not text.startswith("#EXTM3U"):
            return False, "", "", f"HTTP {status}, contenido no HLS"

        variants = _variants(text, final_url)
        target_url = final_url
        resolution = "Auto"
        if variants:
            _, target_url, resolution = max(variants, key=lambda item: (item[0], item[1]))
            child_status, child_body, child_final_url = _fetch_bytes(target_url)
            child_text = child_body.decode("utf-8", "replace").lstrip("\ufeff\r\n ")
            if child_status != 200 or not child_text.startswith("#EXTM3U"):
                return False, "", "", f"variante {resolution}: HTTP {child_status}"
            target_url = child_final_url
        else:
            child_text = text

        segment_url = _first_segment(child_text, target_url)
        if segment_url:
            segment_status, segment_body, _ = _fetch_bytes(segment_url, limit=8_192)
            if segment_status != 200 or not segment_body:
                return False, "", "", f"primer segmento: HTTP {segment_status}"

        return True, target_url, resolution, f"HLS {resolution}; segmento OK"
    except urllib.error.HTTPError as error:
        return False, "", "", f"HTTP {error.code} {error.reason}"
    except Exception as error:
        return False, "", "", f"{type(error).__name__}: {error}"


def _event_time(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _event_entries(existing_names: set[str]) -> tuple[list[SportsEntry], list[str]]:
    feed_url = os.environ.get(SPORTS_EVENT_FEED_ENV, "").strip()
    if not feed_url:
        return [], []
    if not _https_url(feed_url):
        return [], [f"{SPORTS_EVENT_FEED_ENV} no usa una URL HTTPS valida"]

    try:
        payload = _fetch_json(feed_url)
    except Exception as error:
        return [], [f"feed de eventos: {error}"]

    if isinstance(payload, dict):
        items = payload.get("events", payload.get("items", []))
    else:
        items = payload
    if not isinstance(items, list):
        return [], ["feed de eventos: se esperaba una lista JSON"]

    now = datetime.now(timezone.utc)
    entries: list[SportsEntry] = []
    errors: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("name") or item.get("title"), "Evento deportivo")
        start = _event_time(item.get("start") or item.get("start_time"))
        stop = _event_time(item.get("end") or item.get("end_time"))
        if start and start > now + timedelta(hours=6):
            continue
        if stop and stop < now - timedelta(hours=2):
            continue
        url = item.get("url") or item.get("stream") or item.get("m3u8")
        if not _trusted_direct_url(url) or ".m3u8" not in url.lower():
            continue
        if name in existing_names:
            continue
        ok, playable_url, resolution, detail = validate_hls(url)
        if not ok:
            errors.append(f"{name}: {detail}")
            continue
        event_id = hashlib.sha1(f"{name}|{playable_url}".encode("utf-8")).hexdigest()[:12]
        entries.append(
            SportsEntry(
                channel_id=f"sports-event-{event_id}",
                name=name,
                tvg_id=f"sports-event-{event_id}",
                logo=_clean(item.get("logo") or item.get("tvg_logo")),
                url=playable_url,
                resolution=resolution,
                source_url=feed_url,
                detail=detail,
            )
        )
    return entries, errors


def build_sports_entries(existing_names: set[str] | None = None) -> tuple[list[SportsEntry], dict]:
    existing_names = existing_names or set()
    entries: list[SportsEntry] = []
    errors: list[str] = []
    source_ok = False
    try:
        payload = _fetch_json(IPTV_ORG_STREAMS_URL)
        source_ok = True
    except Exception as error:
        return [], {"ok": False, "channels": 0, "events": 0, "errors": [str(error)]}

    streams = payload if isinstance(payload, list) else []
    candidates: dict[str, list[dict]] = {channel_id: [] for channel_id in SPORTS_CHANNELS}
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        channel_id = stream.get("channel")
        url = stream.get("url")
        if channel_id not in candidates or not _trusted_direct_url(url):
            continue
        if ".m3u8" not in url.lower() or stream.get("status") in {"error", "timeout"}:
            continue
        candidates[channel_id].append(stream)

    for channel_id, spec in SPORTS_CHANNELS.items():
        if spec["name"] in existing_names:
            continue
        ordered = sorted(
            candidates[channel_id],
            key=lambda stream: (
                _quality_score(stream.get("quality")),
                _host_score(stream.get("url", "")),
                stream.get("url", ""),
            ),
            reverse=True,
        )
        chosen: SportsEntry | None = None
        for stream in ordered[:8]:
            url = stream.get("url", "")
            ok, playable_url, resolution, detail = validate_hls(url)
            if not ok:
                errors.append(f"{spec['name']}: {detail}")
                continue
            chosen = SportsEntry(
                channel_id=channel_id,
                name=spec["name"],
                tvg_id=spec["tvg_id"],
                logo=spec["logo"],
                url=playable_url,
                resolution=resolution,
                source_url=url,
                detail=detail,
            )
            break
        if chosen:
            entries.append(chosen)

    event_entries, event_errors = _event_entries(existing_names | {entry.name for entry in entries})
    entries.extend(event_entries)
    errors.extend(event_errors)
    return entries, {
        "ok": source_ok,
        "channels": len(entries),
        "iptv_org_channels": len([entry for entry in entries if entry.channel_id in SPORTS_CHANNELS]),
        "events": len(event_entries),
        "errors": errors[:30],
    }


def _blockless(lines: list[str]) -> list[str]:
    output: list[str] = []
    inside = False
    for line in lines:
        marker = line.strip()
        if marker == SPORTS_BLOCK_START:
            if inside:
                raise ValueError("bloque deportivo anidado")
            inside = True
            continue
        if marker == SPORTS_BLOCK_END:
            if not inside:
                raise ValueError("bloque deportivo sin inicio")
            inside = False
            continue
        if not inside:
            output.append(line)
    if inside:
        raise ValueError("bloque deportivo sin cierre")
    while output and not output[-1].strip():
        output.pop()
    return output


def _attr(value: str) -> str:
    return _clean(value)


def render_sports_block(entries: list[SportsEntry]) -> list[str]:
    if not entries:
        return []
    block = [SPORTS_BLOCK_START, "# Fuentes deportivas publicas verificadas por HLS"]
    for entry in entries:
        block.append(
            '#EXTINF:-1 tvg-id="{}" tvg-name="{}" tvg-logo="{}" group-title="Deportes",{}'.format(
                _attr(entry.tvg_id),
                _attr(entry.name),
                _attr(entry.logo),
                _attr(entry.name),
            )
        )
        block.append(entry.url)
        block.append("")
    block.append(SPORTS_BLOCK_END)
    return block


def replace_sports_block(lines: list[str], entries: list[SportsEntry]) -> list[str]:
    output = _blockless(lines)
    block = render_sports_block(entries)
    if not block:
        return output
    return output + [""] + block


def report_entries(entries: list[SportsEntry]) -> list[dict]:
    return [asdict(entry) for entry in entries]
