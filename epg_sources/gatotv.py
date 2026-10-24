"""GatoTV: guía pública por canal para señales que Claro y EPGShare no cubren (2026-10-24).

Golden Premiere, Golden Premiere 2, Discovery Familia y TNT Novelas de Lista 2. Cada página
(``/canal/<canal>/<AAAA-MM-DD>``) trae un día con «Hora Inicio / Hora Fin / Programa» en la
hora del visitante; el desfase viene en la misma página (``utcOffset: -3``) y con él se pasa
todo a UTC, así da igual desde dónde corra el runner. Los programas salen con canal
``gatotv:<canal>``; los canales de una misma señal comparten esa clave (epg-l2-map.json).
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

from update_m3u import (
    BROWSER_USER_AGENT,
    GATOTV_CHANNELS,
    GATOTV_ID_PREFIX,
    Channel,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "fetch_gatotv_epg",
    "gatotv_programmes",
]

GATOTV_URL = "https://www.gatotv.com/canal/{slug}/{day:%Y-%m-%d}"
GATOTV_DAYS = 3
_OFFSET = re.compile(r"utcOffset:\s*(-?\d+(?:\.\d+)?)")
_ROW = re.compile(
    r'<time datetime="(\d\d):(\d\d)">.*?<time datetime="(\d\d):(\d\d)">.*?'
    r'div_program_title_on_channel">\s*<span>(.*?)</span>',
    re.S,
)


def gatotv_programmes(page: str, day: date) -> list[tuple[datetime, datetime, str]]:
    """Programas de una página de GatoTV, en UTC."""
    offset_match = _OFFSET.search(page)
    if not offset_match:
        raise ValueError("GatoTV sin utcOffset")
    offset = timedelta(hours=float(offset_match.group(1)))
    result: list[tuple[datetime, datetime, str]] = []
    for index, (sh, sm, eh, em, raw_title) in enumerate(_ROW.findall(page)):
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw_title))).strip()
        if not title:
            continue
        start_local = datetime(day.year, day.month, day.day, int(sh), int(sm))
        stop_local = datetime(day.year, day.month, day.day, int(eh), int(em))
        if index == 0 and start_local > stop_local:
            start_local -= timedelta(days=1)  # el primero empieza el día anterior
        elif stop_local <= start_local:
            stop_local += timedelta(days=1)  # cruza la medianoche
        start = (start_local - offset).replace(tzinfo=timezone.utc)
        stop = (stop_local - offset).replace(tzinfo=timezone.utc)
        if stop > start:
            result.append((start, stop, title))
    return result


def fetch_gatotv_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    slugs = sorted({GATOTV_CHANNELS[channel.tvg_id] for channel in channels
                    if channel.tvg_id in GATOTV_CHANNELS})
    if not slugs:
        return None, {}
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/html"}
    root = ET.Element("tv", {
        "generator-info-name": "lista-m3u GatoTV importer",
        "source-info-name": "GatoTV",
    })
    errors: dict[str, str] = {}
    first_day = (now - timedelta(hours=12)).date()
    for slug in slugs:
        seen: set[tuple[datetime, str]] = set()
        for offset in range(GATOTV_DAYS):
            day = first_day + timedelta(days=offset)
            try:
                status, body, _ = fetch_bytes(
                    GATOTV_URL.format(slug=slug, day=day), headers, timeout=45, limit=2_000_000)
                if status != 200:
                    raise ValueError(f"HTTP {status}")
                items = gatotv_programmes(body.decode("utf-8", errors="replace"), day)
            except Exception as error:  # un día caído no borra los demás
                errors[f"{slug}:{day}"] = f"{type(error).__name__}: {error}"
                continue
            for start, stop, title in items:
                if (start, title) in seen:
                    continue
                seen.add((start, title))
                programme = ET.SubElement(root, "programme", {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": GATOTV_ID_PREFIX + slug,
                })
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
        if not seen:
            errors.setdefault(slug, "GatoTV sin programas")
    if not len(root):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
