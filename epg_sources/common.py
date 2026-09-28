"""Utilidades compartidas por las fuentes EPG.

Movido desde update_m3u.py sin cambios de lógica."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

__all__ = [
    "decode_web_text",
    "external_epg_datetime",
    "epg_root",
    "clone_xmltv_channel",
]


def decode_web_text(data: bytes) -> str:
    decoded = data.decode("utf-8", "replace")
    if "\ufffd" in decoded:
        return data.decode("cp1252", "replace")
    return decoded


def external_epg_datetime(value: object) -> datetime:
    """Parse the ISO timestamps used by the public non-XMLTV sources."""
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def epg_root(source_name: str) -> ET.Element:
    return ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u updater",
            "source-info-name": source_name,
        },
    )


def clone_xmltv_channel(
    source_xml: bytes,
    source_channel_id: str,
    cloned_channel_id: str,
) -> bytes:
    """Create an in-memory XMLTV source for a simulcast channel.

    Some public guides expose Main Event HD but not its UHD simulcast as a
    separate XMLTV ID. Cloning only that channel keeps the association exact
    without making one source ID compete between two output channels.
    """
    source_root = ET.fromstring(source_xml)
    output = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u updater",
            "source-info-name": "Sky Main Event UHD simulcast",
        },
    )
    source_channel = next(
        (
            channel
            for channel in source_root.findall("channel")
            if channel.get("id") == source_channel_id
        ),
        None,
    )
    if source_channel is None:
        raise ValueError(f"no se encontro el canal fuente {source_channel_id}")
    channel_copy = copy.deepcopy(source_channel)
    channel_copy.set("id", cloned_channel_id)
    output.append(channel_copy)
    programme_count = 0
    for programme in source_root.findall("programme"):
        if programme.get("channel") != source_channel_id:
            continue
        programme_copy = copy.deepcopy(programme)
        programme_copy.set("channel", cloned_channel_id)
        output.append(programme_copy)
        programme_count += 1
    if programme_count < 1:
        raise ValueError(f"el canal fuente {source_channel_id} no tiene programas")
    ET.indent(output, space="  ")
    return ET.tostring(output, encoding="utf-8", xml_declaration=True)
