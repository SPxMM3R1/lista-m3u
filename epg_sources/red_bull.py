"""Red Bull TV: página oficial, API y relay.

La página es_CL depende del país de la IP: sin IP chilena se usa la copia
subida desde Chile (data/redbull-cl-epg.json)."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from update_m3u import (
    BROWSER_USER_AGENT,
    RED_BULL_CHANNEL_LOCALES,
    RED_BULL_CHILE_EPG_SNAPSHOT_PATH,
    RED_BULL_CHILE_ID,
    RED_BULL_OFFICIAL_EPG_URL,
    RED_BULL_RELAY_EPG_URL,
    RED_BULL_SESSION_URL,
    RED_BULL_SPANISH_EPG_PAGE,
    RED_BULL_WORLD_ID,
    fetch_bytes,
    xmltv_datetime,
)

__all__ = [
    "normalize_red_bull_schedule",
    "red_bull_page_schedule",
    "red_bull_request_country",
    "red_bull_chile_snapshot_schedule",
    "red_bull_chile_schedule",
    "red_bull_api_schedule",
    "red_bull_relay_schedule",
    "fetch_red_bull_schedules",
]


def normalize_red_bull_schedule(schedule: list[dict]) -> list[dict]:
    """Return a chronological, non-overlapping linear guide."""
    ordered: list[dict] = []
    sortable: list[tuple[datetime, dict]] = []
    for item in schedule:
        try:
            start = datetime.fromisoformat(item["start_time"].replace("Z", "+00:00"))
            stop = datetime.fromisoformat(item["end_time"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if stop > start:
            sortable.append((start, item))

    # The API can briefly return duplicate or overlapping cards while its guide
    # rolls over. A linear XMLTV channel must expose one programme at a time.
    previous_stop: datetime | None = None
    for start, source_item in sorted(sortable, key=lambda pair: pair[0]):
        stop = datetime.fromisoformat(source_item["end_time"].replace("Z", "+00:00"))
        if previous_stop is not None and start < previous_stop:
            if stop <= previous_stop:
                continue
            item = dict(source_item)
            item["start_time"] = previous_stop.isoformat()
            start = previous_stop
        else:
            item = source_item
        ordered.append(item)
        previous_stop = (
            stop
            if previous_stop is None or stop > previous_stop
            else previous_stop
        )
    return ordered


def red_bull_page_schedule(now: datetime) -> list[dict]:
    """Read the Spanish World of Red Bull rail from the official TV guide page."""
    status, body, _ = fetch_bytes(
        RED_BULL_SPANISH_EPG_PAGE,
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "es-CL,es;q=0.9",
        },
        timeout=90,
        limit=30_000_000,
    )
    if status != 200:
        raise ValueError(f"pagina EPG Red Bull HTTP {status}")
    html = body.decode("utf-8", "replace")
    rails = None
    for script in re.findall(r"<script[^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL):
        if "channelRails" not in script:
            continue
        match = re.fullmatch(
            r"\s*self\.__next_f\.push\(\[1,(.*)\]\)\s*", script, re.DOTALL
        )
        if not match:
            continue
        try:
            decoded = json.loads(match.group(1))
            marker = '"channelRails":'
            marker_start = decoded.index(marker) + len(marker)
            rails, _ = json.JSONDecoder().raw_decode(decoded, marker_start)
            break
        except (IndexError, json.JSONDecodeError, TypeError, ValueError):
            continue
    if not isinstance(rails, list):
        raise ValueError("pagina EPG Red Bull no contiene channelRails")

    world_rail = next(
        (
            rail
            for rail in rails
            if isinstance(rail, dict)
            and str(rail.get("title", "")).strip().lower() == "world of red bull"
        ),
        None,
    )
    if not isinstance(world_rail, dict):
        raise ValueError("pagina EPG Red Bull no contiene la rail World of Red Bull")

    schedule: list[dict] = []
    for card in world_rail.get("cards", []):
        if not isinstance(card, dict):
            continue
        title = card.get("title")
        start = card.get("start_time")
        stop = card.get("end_time")
        if not title or not start or not stop:
            continue
        try:
            if datetime.fromisoformat(stop.replace("Z", "+00:00")) <= now - timedelta(
                hours=1
            ):
                continue
        except (TypeError, ValueError):
            continue
        schedule.append(
            {
                "start_time": start,
                "end_time": stop,
                "title": title,
                "subheading": card.get("subheading"),
                "short_description": card.get("short_description"),
                "long_description": card.get("long_description"),
                "lang": "es",
            }
        )
    schedule = normalize_red_bull_schedule(schedule)
    if len(schedule) < 5:
        raise ValueError("pagina EPG Red Bull entrego una parrilla demasiado corta")
    return schedule


def red_bull_request_country() -> str:
    """País que Red Bull asigna a esta conexión (lo decide por la IP)."""
    status, body, _ = fetch_bytes(
        f"{RED_BULL_SESSION_URL}&locale=es",
        {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"},
        timeout=60,
        limit=1_048_576,
    )
    if status != 200:
        raise ValueError(f"sesion Red Bull HTTP {status}")
    return str(json.loads(body).get("country_code", "")).strip().lower()


def red_bull_chile_snapshot_schedule(
    now: datetime, path: Path = RED_BULL_CHILE_EPG_SNAPSHOT_PATH
) -> list[dict]:
    """Parrilla de Red Bull Chile subida desde una IP chilena."""
    if not path.is_file():
        raise ValueError("no hay copia chilena de la parrilla Red Bull")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("country") != "cl":
        raise ValueError("la copia de Red Bull no es de Chile")
    schedule = normalize_red_bull_schedule(
        [
            {**item, "lang": "es"}
            for item in payload.get("programmes", [])
            if isinstance(item, dict)
        ]
    )
    upcoming = [
        item
        for item in schedule
        if datetime.fromisoformat(item["end_time"].replace("Z", "+00:00")) > now
    ]
    if not upcoming:
        raise ValueError("la copia chilena de Red Bull ya no tiene programas vigentes")
    return schedule


def red_bull_chile_schedule(now: datetime) -> list[dict]:
    """Red Bull Chile: la página en vivo solo si Red Bull nos ve en Chile."""
    country = red_bull_request_country()
    if country == "cl":
        return red_bull_page_schedule(now)
    try:
        return red_bull_chile_snapshot_schedule(now)
    except ValueError as error:
        raise ValueError(
            f"Red Bull ve esta conexion como '{country}' y {error}"
        ) from error


def red_bull_api_schedule(locale: str) -> list[dict]:
    """Read the current Red Bull linear schedule using a short-lived API session."""
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "es-CL,es;q=0.9",
    }
    status, body, _ = fetch_bytes(
        f"{RED_BULL_SESSION_URL}&locale={locale}",
        headers,
        timeout=60,
        limit=1_048_576,
    )
    if status != 200:
        raise ValueError(f"sesion Red Bull HTTP {status}")
    session = json.loads(body)
    token = session.get("token")
    if not token:
        raise ValueError("Red Bull no entrego token de sesion")

    epg_headers = dict(headers)
    epg_headers["Authorization"] = token
    status, body, _ = fetch_bytes(
        RED_BULL_OFFICIAL_EPG_URL,
        epg_headers,
        timeout=60,
        limit=10_485_760,
    )
    if status != 200:
        raise ValueError(f"EPG Red Bull HTTP {status}")
    payload = json.loads(body)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("EPG Red Bull no contiene items")

    language = "es" if locale.startswith("es") else "en"
    schedule: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        title = item.get("title")
        start = item.get("start_time")
        stop = item.get("end_time")
        if not title or not start or not stop:
            continue
        key = (start, stop, title)
        if key in seen:
            continue
        seen.add(key)
        schedule.append(
            {
                "start_time": start,
                "end_time": stop,
                "title": title,
                "subheading": item.get("subheading"),
                "short_description": item.get("short_description"),
                "long_description": item.get("long_description"),
                "lang": language,
            }
        )
    schedule = normalize_red_bull_schedule(schedule)
    if len(schedule) < 5:
        raise ValueError("EPG Red Bull entrego una parrilla demasiado corta")
    return schedule


def red_bull_relay_schedule(now: datetime) -> list[dict]:
    """Use the GitHub-documented relay only when it has a current guide."""
    status, body, _ = fetch_bytes(
        RED_BULL_RELAY_EPG_URL,
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/xml,text/xml,*/*",
        },
        timeout=60,
        limit=10_485_760,
    )
    if status != 200:
        raise ValueError(f"relay Red Bull HTTP {status}")
    root = ET.fromstring(body)
    schedule: list[dict] = []
    for programme in root.findall("programme"):
        if programme.get("channel") != "10001":
            continue
        start_value = programme.get("start")
        stop_value = programme.get("stop")
        title_element = programme.find("title")
        if not start_value or not stop_value or title_element is None:
            continue
        start = xmltv_datetime(start_value)
        stop = xmltv_datetime(stop_value)
        if stop <= now - timedelta(hours=1):
            continue
        schedule.append(
            {
                "start_time": start.isoformat(),
                "end_time": stop.isoformat(),
                "title": (title_element.text or "Red Bull TV").strip(),
                "subheading": None,
                "short_description": None,
                "long_description": None,
                "lang": title_element.get("lang") or "en",
            }
        )
    schedule = normalize_red_bull_schedule(schedule)
    if len(schedule) < 5:
        raise ValueError("relay Red Bull entrego una parrilla demasiado corta")
    last_stop = datetime.fromisoformat(schedule[-1]["end_time"])
    if last_stop < now + timedelta(hours=24):
        raise ValueError("relay Red Bull no cubre las proximas 24 horas")
    return schedule


def fetch_red_bull_schedules(
    expected_ids: set[str], now: datetime
) -> tuple[dict[str, list[dict]], set[str], dict[str, str]]:
    schedules: dict[str, list[dict]] = {}
    source_names: set[str] = set()
    errors: dict[str, str] = {}
    for channel_id, locale in RED_BULL_CHANNEL_LOCALES.items():
        if channel_id not in expected_ids:
            continue
        if channel_id == RED_BULL_CHILE_ID:
            try:
                schedules[channel_id] = red_bull_chile_schedule(now)
                source_names.add("red-bull-es-oficial-page")
                continue
            except Exception as page_error:
                # La API v3 es global y no representa necesariamente la rail
                # regional que ve el usuario en es_CL/epg. No la usamos como
                # fallback para evitar publicar una parrilla de otro país o
                # de Red Bull World bajo la identidad española.
                errors[f"red_bull:{channel_id}"] = (
                    f"pagina oficial regional: {page_error}"
                )
                continue
        try:
            schedules[channel_id] = red_bull_api_schedule(locale)
            source_names.add("red-bull-oficial")
        except Exception as official_error:
            if channel_id != RED_BULL_WORLD_ID:
                errors[f"red_bull:{channel_id}"] = str(official_error)
                continue
            try:
                schedules[channel_id] = red_bull_relay_schedule(now)
                source_names.add("red-bull-relay")
            except Exception as relay_error:
                errors[f"red_bull:{channel_id}"] = (
                    f"oficial: {official_error}; relay: {relay_error}"
                )
    return schedules, source_names, errors
