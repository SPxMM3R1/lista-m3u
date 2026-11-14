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
    r'div_program_title_on_channel">\s*(?:<a[^>]*>)?\s*<span>(.*?)</span>(.*)',
    re.S,
)
# Después del título, la fila trae la sinopsis antes de cerrar la columna (2026-11-14, HBO
# casi no tenía detalle: GatoTV lo publicaba y el lector solo tomaba el título).
_DESC = re.compile(r"^\s*(?:</a>)?\s*</div>(.*?)</div>", re.S)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def gatotv_programmes(page: str, day: date) -> list[tuple[datetime, datetime, str, str]]:
    """Programas de una página de GatoTV, en UTC: (inicio, fin, título, sinopsis o "")."""
    offset_match = _OFFSET.search(page)
    if not offset_match:
        raise ValueError("GatoTV sin utcOffset")
    offset = timedelta(hours=float(offset_match.group(1)))
    result: list[tuple[datetime, datetime, str, str]] = []
    # Una fila por <tr>: así una sinopsis nunca se cuela de una fila a la siguiente.
    rows = [match for match in (_ROW.search(chunk) for chunk in re.split(r"<tr\b", page)) if match]
    for index, match in enumerate(rows):
        sh, sm, eh, em, raw_title, rest = match.groups()
        title = _clean(raw_title)
        if not title:
            continue
        description_match = _DESC.match(rest)
        description = _clean(description_match.group(1)) if description_match else ""
        if len(description) < 25 or description.casefold() == title.casefold():
            description = ""  # «Película.», el título repetido: rótulos, no sinopsis
        start_local = datetime(day.year, day.month, day.day, int(sh), int(sm))
        stop_local = datetime(day.year, day.month, day.day, int(eh), int(em))
        if index == 0 and start_local > stop_local:
            start_local -= timedelta(days=1)  # el primero empieza el día anterior
        elif stop_local <= start_local:
            stop_local += timedelta(days=1)  # cruza la medianoche
        start = (start_local - offset).replace(tzinfo=timezone.utc)
        stop = (stop_local - offset).replace(tzinfo=timezone.utc)
        if stop > start:
            result.append((start, stop, title, description))
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
            for start, stop, title, description in items:
                if (start, title) in seen:
                    continue
                seen.add((start, title))
                programme = ET.SubElement(root, "programme", {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": GATOTV_ID_PREFIX + slug,
                })
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                if description:
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = description
        if not seen:
            errors.setdefault(slug, "GatoTV sin programas")
    if not len(root):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors
