"""Canal 13, 13C y 13Go: guías oficiales.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from epg_sources.common import decode_web_text, epg_root, external_epg_datetime

from update_m3u import (
    BROWSER_USER_AGENT,
    CANAL13_13C_PROGRAMMING_PAGE,
    CANAL13_13GO_EPG_URLS,
    CANAL13_MAIN_EPG_URL,
    CHILE_TIMEZONE,
    Channel,
    fetch_bytes,
    xmltv_format_chile,
)

__all__ = [
    "CANAL13_WEEKDAY_INDEX",
    "CANAL13_MONTH_INDEX",
    "canal13_official_payload",
    "canal13_schedule_date",
    "fetch_13c_official_epg",
    "fetch_canal13_main_official_epg",
    "fetch_13go_epg",
]


CANAL13_WEEKDAY_INDEX = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


CANAL13_MONTH_INDEX = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def round_to_minute(value: datetime) -> datetime:
    """Redondea al minuto más cercano (30 s o más suben)."""
    floored = value.replace(second=0, microsecond=0)
    return floored + timedelta(minutes=1) if value - floored >= timedelta(seconds=30) else floored


def canal13_official_payload(page_html: str) -> dict:
    """Extract the JSON object embedded by the official 13C guide page."""
    match = re.search(
        r"const\s+programacionJson\s*=\s*(\{.*?\})\s*;\s*"
        r"console\.log\(programacionJson(?:\.titulo)?\)",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError("Canal 13 no publico programacionJson para 13C")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict) or not isinstance(payload.get("dias"), dict):
        raise ValueError("el JSON oficial de 13C no contiene dias validos")
    return payload


def canal13_schedule_date(
    day_name: str, day_number: int, title: str, now: datetime
) -> object:
    """Resolve the date printed by 13.cl and tolerate a stale week label."""
    normalized_day = re.sub(r"\s+", "", day_name.casefold())
    weekday = CANAL13_WEEKDAY_INDEX.get(normalized_day)
    if weekday is None:
        raise ValueError(f"dia no reconocido en la guia 13C: {day_name}")
    title_match = re.search(
        r"\b([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(20\d{2})\b", title
    )
    if not title_match:
        raise ValueError("la guia oficial de 13C no contiene mes y ano")
    month_name = title_match.group(1).casefold()
    month = CANAL13_MONTH_INDEX.get(month_name)
    if month is None:
        raise ValueError(f"mes no reconocido en la guia 13C: {month_name}")
    year = int(title_match.group(2))
    try:
        candidate = datetime(year, month, day_number, tzinfo=CHILE_TIMEZONE).date()
    except ValueError as error:
        raise ValueError(f"fecha invalida en la guia oficial de 13C: {error}") from error
    if candidate.weekday() == weekday:
        return candidate

    # A stale cached title can carry the wrong month/year. Search a narrow
    # window while retaining the day number and weekday printed by the page.
    reference = now.astimezone(CHILE_TIMEZONE).date()
    for delta in range(-370, 371):
        alternative = reference + timedelta(days=delta)
        if alternative.day == day_number and alternative.weekday() == weekday:
            return alternative
    raise ValueError(f"no se pudo ubicar la fecha de {day_name} {day_number}")


def fetch_13c_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the real weekly 13C guide from Canal 13 before Zapping."""
    if not any(channel.tvg_id == "13C.cl@SD" for channel in channels):
        return None, None
    try:
        status, body, _ = fetch_bytes(
            CANAL13_13C_PROGRAMMING_PAGE,
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
                "Referer": "https://www.13.cl/c",
            },
            timeout=60,
            limit=10_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        payload = canal13_official_payload(decode_web_text(body))
        title = str(payload.get("titulo", "")).strip()
        raw_days = payload.get("dias")
        if not isinstance(raw_days, dict):
            raise ValueError("la guia oficial de 13C no contiene un objeto dias")

        records: list[tuple[datetime, str]] = []
        for day_name, date_objects in raw_days.items():
            if not isinstance(date_objects, dict):
                continue
            for date_text, schedule in date_objects.items():
                if not isinstance(schedule, dict):
                    continue
                day_match = re.search(r"(\d{1,2})", str(date_text))
                if not day_match:
                    continue
                schedule_date = canal13_schedule_date(
                    str(day_name), int(day_match.group(1)), title, now
                )
                parsed: list[tuple[object, str]] = []
                for clock_text, raw_title in schedule.items():
                    clock_match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(clock_text).strip())
                    if not clock_match:
                        continue
                    hour, minute = int(clock_match.group(1)), int(clock_match.group(2))
                    if hour > 23 or minute > 59:
                        continue
                    clean_title = re.sub(r"\s+", " ", str(raw_title)).strip()
                    if not clean_title:
                        continue
                    marker = ""
                    marker_match = re.search(r"\s+([RE])\s*$", clean_title, re.IGNORECASE)
                    if marker_match:
                        marker = " (Estreno)" if marker_match.group(1).upper() == "E" else " (R)"
                        clean_title = clean_title[: marker_match.start()].rstrip()
                    parsed.append(
                        (
                            datetime.strptime(
                                f"{hour:02d}:{minute:02d}", "%H:%M"
                            ).time(),
                            clean_title + marker,
                        )
                    )
                previous_start: datetime | None = None
                for start_clock, clean_title in parsed:
                    start = datetime.combine(
                        schedule_date, start_clock, tzinfo=CHILE_TIMEZONE
                    )
                    if previous_start is not None and start <= previous_start:
                        start += timedelta(days=1)
                    records.append((start, clean_title))
                    previous_start = start

        unique_records: dict[datetime, str] = {}
        for start, clean_title in records:
            unique_records.setdefault(start, clean_title)
        ordered = sorted(unique_records.items())
        lower_limit = now - timedelta(hours=6)
        upper_limit = now + timedelta(days=8)
        filtered = [
            (start, clean_title)
            for start, clean_title in ordered
            if start <= upper_limit and start + timedelta(minutes=1) >= lower_limit
        ]
        if len(filtered) < 5:
            raise ValueError("Canal 13 no publico una parrilla oficial vigente suficiente")

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u Canal 13 13C importer",
                "source-info-name": CANAL13_13C_PROGRAMMING_PAGE,
            },
        )
        programme_count = 0
        for index, (start, clean_title) in enumerate(filtered):
            stop = (
                filtered[index + 1][0]
                if index + 1 < len(filtered)
                else start + timedelta(hours=2)
            )
            if stop <= start:
                continue
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": "13C.cl@SD",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = clean_title
            ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                "Programacion oficial consultada en Canal 13 para 13C."
            )
            programme_count += 1
        if programme_count < 5:
            raise ValueError("la guia oficial de 13C no contiene bloques utilizables")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_canal13_main_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the public structured guide used by Canal 13's official player."""
    if not any(channel.tvg_id == "0107" for channel in channels):
        return None, None
    try:
        status, body, _ = fetch_bytes(
            CANAL13_MAIN_EPG_URL,
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
                "Referer": "https://www.13.cl/",
            },
            timeout=45,
            limit=4_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        payload = json.loads(decode_web_text(body))
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise ValueError("el JSON oficial de Canal 13 no contiene events")

        lower_limit = now - timedelta(hours=6)
        upper_limit = now + timedelta(days=8)
        records: list[dict[str, object]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            try:
                start = external_epg_datetime(event["beginTime"])
                stop = external_epg_datetime(event["endTime"])
            except (KeyError, TypeError, ValueError):
                continue
            if stop <= start or stop <= lower_limit or start >= upper_limit:
                continue
            generic_title = re.sub(
                r"\s+",
                " ",
                html.unescape(str(event.get("title", ""))).strip(),
            )
            episode_title = re.sub(
                r"\s+",
                " ",
                html.unescape(str(event.get("episodeTitle", ""))).strip(),
            )
            title = episode_title or generic_title
            if not title:
                continue
            records.append(
                {
                    "start": start,
                    "stop": stop,
                    "title": title,
                    "synopsis": re.sub(
                        r"\s+",
                        " ",
                        html.unescape(str(event.get("synopsis", ""))).strip(),
                    ),
                    "genre": re.sub(
                        r"\s+",
                        " ",
                        html.unescape(str(event.get("genre", ""))).strip(),
                    ),
                }
            )

        normalized: list[dict[str, object]] = []
        seen: set[tuple[datetime, datetime, str]] = set()
        for record in sorted(records, key=lambda item: item["start"]):
            start = record["start"]
            stop = record["stop"]
            title = record["title"]
            if not isinstance(start, datetime) or not isinstance(stop, datetime):
                continue
            if not isinstance(title, str):
                continue
            key = (start, stop, title)
            if key in seen:
                continue
            seen.add(key)
            if normalized:
                previous = normalized[-1]
                previous_start = previous["start"]
                previous_stop = previous["stop"]
                if (
                    isinstance(previous_start, datetime)
                    and isinstance(previous_stop, datetime)
                    and start < previous_stop
                ):
                    if stop <= previous_stop:
                        continue
                    previous["stop"] = start
                    if start <= previous_start:
                        normalized.pop()
            if stop > start:
                normalized.append(record)

        if len(normalized) < 5:
            raise ValueError("Canal 13 publico una parrilla oficial demasiado corta")
        last_stop = max(
            record["stop"]
            for record in normalized
            if isinstance(record["stop"], datetime)
        )
        if not isinstance(last_stop, datetime) or last_stop < now + timedelta(hours=24):
            raise ValueError("Canal 13 no publico 24 horas futuras")

        root = epg_root("Canal 13 EPG JSON oficial")
        for record in normalized:
            start = record["start"]
            stop = record["stop"]
            title = record["title"]
            if not isinstance(start, datetime) or not isinstance(stop, datetime):
                continue
            if not isinstance(title, str):
                continue
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": "0107",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            synopsis = record["synopsis"]
            if isinstance(synopsis, str) and synopsis:
                ET.SubElement(programme, "desc", {"lang": "es"}).text = synopsis
            genre = record["genre"]
            if isinstance(genre, str) and genre:
                ET.SubElement(programme, "category", {"lang": "es"}).text = genre
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_13go_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the public JSON EPG used by the 13Go streams for 13Cultura/13Kids."""
    targets = {
        channel.tvg_id: CANAL13_13GO_EPG_URLS[channel.tvg_id]
        for channel in channels
        if channel.tvg_id in CANAL13_13GO_EPG_URLS
    }
    if not targets:
        return None, None
    try:
        root = epg_root("Canal 13 13Go EPG JSON oficial")
        minimum_start = now - timedelta(hours=6)
        maximum_stop = now + timedelta(days=8)
        counts = {channel_id: 0 for channel_id in targets}
        for channel_id, url in targets.items():
            status, body, _ = fetch_bytes(
                url,
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": "https://old.13go.cl/",
                },
                timeout=45,
                limit=4_000_000,
            )
            if status != 200:
                raise ValueError(f"{channel_id}: HTTP {status}")
            payload = json.loads(decode_web_text(body))
            events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(events, list):
                raise ValueError(f"{channel_id}: el JSON no contiene events")
            source_id = "13cultura" if channel_id == "13Cultura.cl@DPS" else "13kids"
            for event in events:
                if not isinstance(event, dict):
                    continue
                try:
                    # 13Go publica segundos (21:58:22 -> 21:58:23); al minuto
                    # los bloques quedan contiguos, sin huecos de un segundo.
                    start = round_to_minute(external_epg_datetime(event["beginTime"]))
                    stop = round_to_minute(external_epg_datetime(event["endTime"]))
                except (KeyError, TypeError, ValueError):
                    continue
                if stop <= minimum_start or start >= maximum_stop or stop <= start:
                    continue
                title = re.sub(r"\s+", " ", str(event.get("title", "")).strip())
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
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                episode_title = str(event.get("episodeTitle", "")).strip()
                if episode_title and episode_title.casefold() != title.casefold():
                    ET.SubElement(programme, "sub-title", {"lang": "es"}).text = (
                        episode_title
                    )
                synopsis = re.sub(
                    r"\s+", " ", str(event.get("synopsis", "")).strip()
                )
                if synopsis:
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = synopsis
                genre = str(event.get("genre", "")).strip()
                if genre:
                    ET.SubElement(programme, "category", {"lang": "es"}).text = genre
                counts[channel_id] += 1
        missing = [channel_id for channel_id, count in counts.items() if count == 0]
        if missing:
            raise ValueError("13Go sin eventos vigentes: " + ", ".join(missing))
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
