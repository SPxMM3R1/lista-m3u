"""Autentic History: guía oficial.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin

from epg_sources.common import decode_web_text, epg_root

from update_m3u import (
    AUTENTIC_HISTORY_CHANNEL_ID,
    AUTENTIC_HISTORY_PAGE,
    BROWSER_USER_AGENT,
    Channel,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "fetch_autentic_history_epg",
]


def fetch_autentic_history_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Resolve Whale TV+'s public frontend token in memory and import its EPG."""
    if not any(channel.tvg_id == "AutenticHistory.de" for channel in channels):
        return None, None
    try:
        page_headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        }
        status, page_body, page_url = fetch_bytes(
            AUTENTIC_HISTORY_PAGE, page_headers, timeout=45, limit=8_000_000
        )
        if status != 200:
            raise ValueError(f"Whale TV+ HTTP {status}")
        page_html = decode_web_text(page_body)
        script_urls = []
        for script_url in re.findall(
            r"<script[^>]+src=[\"']([^\"']+)[\"']", page_html, re.IGNORECASE
        ):
            absolute = urljoin(page_url or AUTENTIC_HISTORY_PAGE, script_url)
            if absolute not in script_urls:
                script_urls.append(absolute)
        api_token = None
        token_patterns = (
            r"apiToken.{0,160}?[\"']([0-9a-f]{32})[\"']",
            r"apiToken.{0,160}?([0-9a-f]{32})",
        )
        for script_url in script_urls:
            try:
                script_status, script_body, _ = fetch_bytes(
                    script_url,
                    {"User-Agent": BROWSER_USER_AGENT, "Accept": "*/*"},
                    timeout=45,
                    limit=12_000_000,
                )
            except Exception:
                continue
            if script_status != 200:
                continue
            script_text = decode_web_text(script_body)
            for pattern in token_patterns:
                match = re.search(pattern, script_text, re.IGNORECASE | re.DOTALL)
                if match:
                    api_token = match.group(1)
                    break
            if api_token:
                break
        if not api_token:
            raise ValueError("Whale TV+ no publico apiToken en sus scripts")
        api_base = "https://rlaxx.zeasn.tv/livetv/api"
        common_headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json,*/*",
            "Origin": "https://watch.whaletvplus.com",
            "Referer": AUTENTIC_HISTORY_PAGE,
        }
        auth_url = f"{api_base}/v1/auth/access?{urlencode({'uuid': '1', 'apiToken': api_token, 'langCode': 'en'})}"
        auth_status, auth_body, _ = fetch_bytes(
            auth_url, common_headers, timeout=45, limit=2_000_000
        )
        if auth_status != 200:
            raise ValueError(f"Whale TV+ auth HTTP {auth_status}")
        auth_payload = json.loads(decode_web_text(auth_body))
        auth_data = auth_payload.get("data") if isinstance(auth_payload, dict) else None
        session_token = auth_data.get("token") if isinstance(auth_data, dict) else None
        if not session_token:
            raise ValueError("Whale TV+ no devolvio token de sesion")
        start_ms = int((now - timedelta(hours=6)).timestamp() * 1000)
        end_ms = int((now + timedelta(days=5)).timestamp() * 1000)
        epg_url = (
            f"{api_base}/device/browser/v1/epg?"
            + urlencode(
                {
                    "channelIds": AUTENTIC_HISTORY_CHANNEL_ID,
                    "startTime": start_ms,
                    "endTime": end_ms,
                }
            )
        )
        epg_headers = dict(common_headers)
        epg_headers["token"] = str(session_token)
        epg_status, epg_body, _ = fetch_bytes(
            epg_url, epg_headers, timeout=45, limit=8_000_000
        )
        if epg_status != 200:
            raise ValueError(f"Whale TV+ EPG HTTP {epg_status}")
        epg_payload = json.loads(decode_web_text(epg_body))
        groups = epg_payload.get("data") if isinstance(epg_payload, dict) else None
        if not isinstance(groups, list):
            raise ValueError("Whale TV+ no devolvio grupos EPG")
        root = epg_root("Whale TV+ EPG publico de Autentic History")
        count = 0
        for group in groups:
            if not isinstance(group, dict):
                continue
            for item in group.get("ptList", []):
                if not isinstance(item, dict):
                    continue
                try:
                    start = datetime.fromtimestamp(int(item["prgStm"]) / 1000, timezone.utc)
                    stop = datetime.fromtimestamp(int(item["prgEtm"]) / 1000, timezone.utc)
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue
                if stop <= start or stop <= now - timedelta(hours=6) or start >= now + timedelta(days=5):
                    continue
                title = re.sub(r"\s+", " ", str(item.get("prgTitle", "")).strip())
                if not title:
                    continue
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": AUTENTIC_HISTORY_CHANNEL_ID,
                    },
                )
                ET.SubElement(programme, "title", {"lang": "en"}).text = title
                count += 1
        if count == 0:
            raise ValueError("Whale TV+ no devolvio programas vigentes")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
