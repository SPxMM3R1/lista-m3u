"""Claro Video: sinopsis de canales chilenos (solo donante de descripciones).

La guía pública de Claro Video trae una sinopsis por programa. Se usa solo para
completar descripciones (``donate_epg_descriptions``): sus programas salen con id
``sinopsis:<tvg-id>`` y nunca entran a la parrilla de ningún canal.

La API pide la clave de aplicación del cliente web (``authpt``). No es una
credencial de cuenta: viene escrita en el JavaScript público de clarovideo.com.
Igual no se guarda en el repositorio; se lee de esa web en cada corrida.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from update_m3u import (
    BROWSER_USER_AGENT,
    CLARO_SYNOPSIS_CHANNELS,
    Channel,
    ZAPPING_DESCRIPTION_ID_PREFIX,
    _fold_epg_description,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "claro_web_app_key",
    "claro_synopsis_programmes",
    "fetch_claro_synopsis_epg",
]

CLARO_WEB_URL = "https://www.clarovideo.com/chile/homeuser"
CLARO_WEB_ORIGIN = "https://www.clarovideo.com"
CLARO_EPG_URL = "https://mfwkweb-api.clarovideo.net/services/epg/channel"
CLARO_KEY_PATTERN = re.compile(r'authpt\s*:\s*"([a-z0-9]{6,40})"')


def claro_web_app_key() -> str:
    """Lee la clave pública del cliente web desde los scripts de clarovideo.com."""
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/html,*/*"}
    status, body, _ = fetch_bytes(CLARO_WEB_URL, headers, timeout=30, limit=2_000_000)
    if status != 200:
        raise ValueError(f"web Claro HTTP {status}")
    page = body.decode("utf-8", "replace")
    scripts = re.findall(r'src="(/[A-Za-z0-9_~.-]+\.js)"', page)
    # La clave vive en los paquetes utils/cvlib; se revisan primero.
    scripts.sort(key=lambda path: 0 if re.search(r"utils|cvlib", path) else 1)
    for path in scripts[:30]:
        status, body, _ = fetch_bytes(CLARO_WEB_ORIGIN + path, headers, timeout=30, limit=8_000_000)
        if status != 200:
            continue
        found = CLARO_KEY_PATTERN.search(body.decode("utf-8", "replace"))
        if found:
            return found.group(1)
    raise ValueError("la web de Claro no publicó la clave del cliente")


def _useful_synopsis(title: str, text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    folded = _fold_epg_description(text).casefold()
    if len(text) < 25 or folded == _fold_epg_description(title).casefold():
        return ""
    # «Programación CNN Chile», «Cine La Red»: rótulos, no sinopsis.
    if folded.startswith(("programacion ", "programación ")):
        return ""
    return text


def claro_synopsis_programmes(
    payload: dict, wanted: dict[str, str]
) -> dict[str, list[tuple[datetime, datetime, str, str]]]:
    """Programas con sinopsis útil por tvg-id, desde la respuesta de la API."""
    channels = payload.get("response", {}).get("channels", [])
    by_group = {str(channel.get("group_id")): channel for channel in channels if isinstance(channel, dict)}
    result: dict[str, list[tuple[datetime, datetime, str, str]]] = {}
    for target_id, group_id in wanted.items():
        channel = by_group.get(group_id)
        if not channel:
            continue
        items: list[tuple[datetime, datetime, str, str]] = []
        for event in channel.get("events") or []:
            try:
                start = datetime.fromtimestamp(int(event["unix_begin"]), timezone.utc)
                stop = datetime.fromtimestamp(int(event["unix_end"]), timezone.utc)
            except (KeyError, TypeError, ValueError, OSError):
                continue
            title = str(event.get("name") or "").strip()
            synopsis = _useful_synopsis(title, str(event.get("description") or ""))
            if title and synopsis and stop > start:
                items.append((start, stop, title, synopsis))
        if items:
            result[target_id] = items
    return result


def fetch_claro_synopsis_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    wanted = {
        channel.tvg_id: CLARO_SYNOPSIS_CHANNELS[channel.tvg_id]
        for channel in channels
        if channel.tvg_id in CLARO_SYNOPSIS_CHANNELS
    }
    if not wanted:
        return None, {}
    key = claro_web_app_key()
    begin = (now - timedelta(hours=6)).astimezone(timezone.utc)
    end = (now + timedelta(days=2)).astimezone(timezone.utc)
    query = urlencode({
        "device_id": "web",
        "device_category": "web",
        "device_model": "web",
        "device_type": "web",
        "device_so": "Chrome",
        "format": "json",
        "device_manufacturer": "generic",
        "authpn": "webclient",
        "authpt": key,
        "api_version": "v5.93",
        "region": "chile",
        "date_from": begin.strftime("%Y%m%d%H%M%S"),
        "date_to": end.strftime("%Y%m%d%H%M%S"),
        "quantity": "2000",
    })
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"}
    status, body, _ = fetch_bytes(f"{CLARO_EPG_URL}?{query}", headers, timeout=90, limit=40_000_000)
    if status != 200:
        raise ValueError(f"guía Claro HTTP {status}")
    programmes = claro_synopsis_programmes(json.loads(body.decode("utf-8")), wanted)
    errors = {
        target_id: "Claro no publicó sinopsis para este canal"
        for target_id in wanted
        if target_id not in programmes
    }
    if not programmes:
        return None, errors
    root = ET.Element("tv", {
        "generator-info-name": "lista-m3u Claro Video synopsis importer",
        "source-info-name": "Claro Video (solo sinopsis)",
    })
    for target_id, items in programmes.items():
        for start, stop, title, synopsis in items:
            programme = ET.SubElement(root, "programme", {
                "start": xmltv_format_chile(start),
                "stop": xmltv_format_chile(stop),
                "channel": ZAPPING_DESCRIPTION_ID_PREFIX + target_id,
            })
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            ET.SubElement(programme, "desc", {"lang": "es"}).text = synopsis
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
