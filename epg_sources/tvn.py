"""TVN: guía oficial (JSONP).

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import json
import re
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text

from update_m3u import (
    BROWSER_USER_AGENT,
    CHILE_TIMEZONE,
    Channel,
    TVN_PROGRAMMING_BASE_URL,
    TVN_PROGRAMMING_PAGE,
    fetch_bytes,
    normalize_epg_title,
    xmltv_format_chile,
)

__all__ = [
    "tvn_official_title",
    "tvn_jsonp_items",
    "fetch_tvn_official_epg",
]


def tvn_official_title(value: str) -> str:
    return normalize_epg_title(value)


def tvn_jsonp_items(data: bytes) -> list[dict]:
    text = decode_web_text(data).strip()
    match = re.search(
        r"jsonp\s*\(\s*(\[.*\])\s*\)\s*;?\s*$",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError("TVN no publico un JSONP valido")
    payload = json.loads(match.group(1))
    if not isinstance(payload, list):
        raise ValueError("la parrilla JSON de TVN no es una lista")
    return [item for item in payload if isinstance(item, dict)]


def fetch_tvn_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == "0104" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json,text/javascript,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": TVN_PROGRAMMING_PAGE,
    }
    # El CDN estatico de TVN mantiene vencido su certificado; el endpoint se
    # consulta solo como fuente oficial de parrilla y ya usa este mismo
    # contexto de compatibilidad para la pagina de TVN.
    insecure_context = ssl.create_default_context()
    insecure_context.check_hostname = False
    insecure_context.verify_mode = ssl.CERT_NONE
    try:
        chile_today = now.astimezone(CHILE_TIMEZONE).date()
        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u TVN importer",
                "source-info-name": TVN_PROGRAMMING_PAGE,
            },
        )
        seen: set[tuple[str, str, str]] = set()
        programme_count = 0
        source_errors: list[str] = []
        for offset in range(-1, 8):
            schedule_day = chile_today + timedelta(days=offset)
            url = (
                f"{TVN_PROGRAMMING_BASE_URL}/{schedule_day:%Y/%m/%d}"
                "/programacion.json"
            )
            try:
                status, body, _ = fetch_bytes(
                    url,
                    headers,
                    timeout=60,
                    context=insecure_context,
                    limit=2_000_000,
                )
                if status != 200:
                    raise ValueError(f"HTTP {status}")
                items = tvn_jsonp_items(body)
            except Exception as error:
                source_errors.append(f"{schedule_day}: {error}")
                continue

            for item in items:
                if item.get("senal") not in (5, "5"):
                    continue
                date_text = str(item.get("fecha", "")).strip()
                start_text = str(item.get("horaInicio", "")).strip()
                stop_text = str(item.get("horaTermino", "")).strip()
                title = tvn_official_title(str(item.get("programa", "")))
                if not (date_text and start_text and stop_text and title):
                    continue
                try:
                    start_date = datetime.strptime(
                        date_text, "%d/%m/%Y"
                    ).date()
                    start_clock = datetime.strptime(
                        start_text, "%H:%M:%S"
                    ).time()
                    stop_clock = datetime.strptime(
                        stop_text, "%H:%M:%S"
                    ).time()
                except ValueError:
                    continue

                start = datetime.combine(
                    start_date, start_clock, tzinfo=CHILE_TIMEZONE
                )
                stop_date = (
                    start_date + timedelta(days=1)
                    if stop_clock <= start_clock
                    else start_date
                )
                stop = datetime.combine(
                    stop_date, stop_clock, tzinfo=CHILE_TIMEZONE
                )
                if stop <= start:
                    continue
                if stop < now - timedelta(hours=6):
                    continue
                if start > now + timedelta(days=8):
                    continue
                key = (start.isoformat(), stop.isoformat(), title)
                if key in seen:
                    continue
                seen.add(key)
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": "0104",
                    },
                )
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                    "Programacion oficial consultada en TVN."
                )
                programme_count += 1

        if programme_count < 5:
            detail = "; ".join(source_errors[:2])
            suffix = f" ({detail})" if detail else ""
            raise ValueError(
                f"TVN publico una parrilla oficial demasiado corta{suffix}"
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
