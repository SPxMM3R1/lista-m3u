"""Guía por canal (2026-10-12): un fragmento XMLTV por canal y un ensamblador sin red.

- ``epg/canales/<id>.xml``: la guía automática de un canal (su ``<channel>`` y sus
  ``<programme>``). Solo la escribe la construcción de ese canal; si su fuente falla, el
  fragmento anterior queda intacto con su última guía buena.
- ``epg/manual/<id>.xml``: correcciones por tramo del usuario. Cada ``<programme>`` manual
  reemplaza lo automático que se cruce con su horario; el resto del día sigue automático.
- ``epg.xml``: lo arma ``assemble`` concatenando fragmentos y correcciones. No consulta
  fuentes, así que no puede caerse por una fuente o un canal roto.

Este módulo no conoce update_m3u: recibe bytes y devuelve bytes, para probarlo aislado.
"""
from __future__ import annotations

import copy
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

FRAGMENTS_DIRNAME = "canales"
MANUAL_DIRNAME = "manual"
# Fuentes de relleno que no cuentan como guía real del canal.
FILLER_GUIDE_SOURCES = frozenset({"continuidad-tecnica", "pendiente"})
MANUAL_GUIDE_SOURCE = "manual"


def fragment_filename(channel_id: str) -> str:
    """Nombre de archivo estable y seguro en Linux y Windows para un tvg-id."""
    if not channel_id:
        raise ValueError("canal sin tvg-id")
    return urllib.parse.quote(channel_id, safe="-_.@") + ".xml"


def channel_id_from_filename(name: str) -> str:
    return urllib.parse.unquote(name[:-4] if name.endswith(".xml") else name)


def xmltv_time(value: str) -> datetime:
    text = value.strip()
    stamp, _, offset = text.partition(" ")
    moment = datetime.strptime(stamp[:14], "%Y%m%d%H%M%S")
    offset = offset.strip() or "+0000"
    sign = 1 if offset[0] == "+" else -1
    delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5]))
    return (moment - sign * delta).replace(tzinfo=timezone.utc)


def _format_like(original: str, moment: datetime) -> str:
    """Escribe ``moment`` con la misma zona que traía ``original``."""
    offset = (original.strip().partition(" ")[2] or "+0000").strip()
    sign = 1 if offset[0] == "+" else -1
    delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5]))
    local = moment.astimezone(timezone.utc) + sign * delta
    return local.strftime("%Y%m%d%H%M%S") + " " + offset


def _serialize(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def split_epg(data: bytes) -> dict[str, bytes]:
    """Un fragmento por canal del XMLTV (sin los alias de la app, que se rehacen al unir)."""
    root = ET.fromstring(data)
    if root.tag != "tv":
        raise ValueError("la guía debe tener raíz <tv>")
    channels: dict[str, ET.Element] = {}
    for element in root.findall("channel"):
        channel_id = element.get("id", "")
        if channel_id and not element.get("data-app-alias-of"):
            channels[channel_id] = element
    programmes: dict[str, list[ET.Element]] = {channel_id: [] for channel_id in channels}
    for programme in root.findall("programme"):
        channel_id = programme.get("channel", "")
        if channel_id in programmes:
            programmes[channel_id].append(programme)
    fragments: dict[str, bytes] = {}
    for channel_id, element in channels.items():
        fragment = ET.Element("tv", {"data-fragment-of": channel_id})
        fragment.append(copy.deepcopy(element))
        for programme in programmes[channel_id]:
            fragment.append(copy.deepcopy(programme))
        fragments[channel_id] = _serialize(fragment)
    return fragments


def _real_future_stop(fragment: bytes | None, now: datetime,
                      filler_titles: frozenset[str] = frozenset()) -> datetime | None:
    """Fin del último programa real (no relleno) que aún no termina, o None."""
    if not fragment:
        return None
    try:
        root = ET.fromstring(fragment)
    except ET.ParseError:
        return None
    channel = root.find("channel")
    if channel is not None and channel.get("data-guide-source", "") in FILLER_GUIDE_SOURCES:
        return None
    latest: datetime | None = None
    for programme in root.findall("programme"):
        if (programme.findtext("title", "") or "").strip().casefold() in filler_titles:
            continue
        try:
            stop = xmltv_time(programme.get("stop", ""))
        except (ValueError, IndexError):
            continue
        if stop > now and (latest is None or stop > latest):
            latest = stop
    return latest


def should_replace(old: bytes | None, new: bytes, now: datetime,
                   filler_titles: frozenset[str] = frozenset()) -> bool:
    """Un canal solo pierde guía real si la nueva también la trae y llega igual o más lejos.

    Si la construcción nueva de un canal quedó en relleno (su fuente falló) mientras el
    fragmento anterior aún cubre el futuro con guía real, se conserva el anterior.
    """
    if _real_future_stop(old, now, filler_titles) is None:
        return True
    return _real_future_stop(new, now, filler_titles) is not None


def _manual_intervals(manual: bytes | None) -> tuple[list[ET.Element], list[tuple[datetime, datetime]]]:
    if not manual:
        return [], []
    root = ET.fromstring(manual)
    if root.tag != "tv":
        raise ValueError("la corrección manual debe tener raíz <tv>")
    programmes: list[ET.Element] = []
    intervals: list[tuple[datetime, datetime]] = []
    for programme in root.findall("programme"):
        start = xmltv_time(programme.get("start", ""))
        stop = xmltv_time(programme.get("stop", ""))
        if stop <= start:
            raise ValueError("programa manual con fin antes del inicio")
        programmes.append(programme)
        intervals.append((start, stop))
    return programmes, intervals


def _subtract(start: datetime, stop: datetime,
              intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    segments = [(start, stop)]
    for cut_start, cut_stop in intervals:
        next_segments = []
        for seg_start, seg_stop in segments:
            if cut_stop <= seg_start or cut_start >= seg_stop:
                next_segments.append((seg_start, seg_stop))
                continue
            if seg_start < cut_start:
                next_segments.append((seg_start, cut_start))
            if cut_stop < seg_stop:
                next_segments.append((cut_stop, seg_stop))
        segments = next_segments
    return [(a, b) for a, b in segments if b - a >= timedelta(minutes=1)]


def assemble(
    fragments: dict[str, bytes],
    manual: dict[str, bytes],
    scope_ids: list[str],
    *,
    root_attributes: dict[str, str],
    now: datetime,
    past_retention: timedelta,
) -> tuple[bytes, list[str]]:
    """Une los fragmentos de ``scope_ids`` (en ese orden) con sus correcciones manuales.

    Devuelve el XMLTV y los ids que no tenían fragmento. Un fragmento o una corrección
    ilegible se omite solo para ese canal (queda informado), nunca detiene la unión.
    """
    root = ET.Element("tv", dict(root_attributes))
    root.set("data-generated-at", now.astimezone(timezone.utc).isoformat())
    programmes_out: list[ET.Element] = []
    missing: list[str] = []
    cutoff = now - past_retention
    for channel_id in scope_ids:
        fragment = fragments.get(channel_id)
        if fragment is None:
            missing.append(channel_id)
            continue
        try:
            fragment_root = ET.fromstring(fragment)
        except ET.ParseError:
            missing.append(channel_id)
            continue
        channel = fragment_root.find("channel")
        if channel is None or channel.get("id") != channel_id:
            missing.append(channel_id)
            continue
        try:
            manual_programmes, intervals = _manual_intervals(manual.get(channel_id))
        except (ValueError, IndexError, ET.ParseError) as error:
            print(f"AVISO EPG: corrección manual ignorada para {channel_id}: {error}")
            manual_programmes, intervals = [], []
        channel_copy = copy.deepcopy(channel)
        if manual_programmes:
            channel_copy.set("data-manual", "true")
        root.append(channel_copy)
        for programme in fragment_root.findall("programme"):
            try:
                start = xmltv_time(programme.get("start", ""))
                stop = xmltv_time(programme.get("stop", ""))
            except (ValueError, IndexError):
                continue
            if stop <= cutoff:
                continue
            for seg_start, seg_stop in _subtract(start, stop, intervals):
                copied = copy.deepcopy(programme)
                if seg_start != start:
                    copied.set("start", _format_like(programme.get("start", ""), seg_start))
                if seg_stop != stop:
                    copied.set("stop", _format_like(programme.get("stop", ""), seg_stop))
                copied.set("channel", channel_id)
                programmes_out.append(copied)
        for programme in manual_programmes:
            if xmltv_time(programme.get("stop", "")) <= cutoff:
                continue
            copied = copy.deepcopy(programme)
            copied.set("channel", channel_id)
            copied.set("data-guide-source", MANUAL_GUIDE_SOURCE)
            programmes_out.append(copied)
    programmes_out.sort(key=lambda item: (item.get("channel", ""), xmltv_time(item.get("start", ""))))
    for programme in programmes_out:
        root.append(programme)
    return _serialize(root), missing


def read_dir(directory: Path) -> dict[str, bytes]:
    if not directory.is_dir():
        return {}
    return {
        channel_id_from_filename(path.name): path.read_bytes()
        for path in sorted(directory.glob("*.xml"))
    }


def write_fragment(directory: Path, channel_id: str, data: bytes) -> bool:
    """Escribe solo si cambió; devuelve si hubo cambio."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / fragment_filename(channel_id)
    if path.exists() and path.read_bytes() == data:
        return False
    temporary = path.with_suffix(".xml.tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    return True
