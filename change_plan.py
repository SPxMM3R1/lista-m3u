"""Classify repository changes without touching network sources.

The scheduled jobs are deliberately broad because they renew volatile streams.
Pushes, however, should be routed conservatively: presentation changes can be
validated offline, a stream edit should validate only its channel, and an EPG
edit should be merged only for the declared channels.  This module contains
the pure change-classification rules used by the lightweight workflow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
import re
from typing import Mapping, Sequence
import xml.etree.ElementTree as ET


class ChangePlanError(ValueError):
    """Raised when a change cannot be routed safely."""


class ChangeKind(str, Enum):
    NOOP = "noop"
    PRESENTATION = "presentation"
    STREAM = "stream"
    EPG = "epg"
    FULL = "full"


@dataclass(frozen=True)
class ChangePlan:
    kind: ChangeKind
    channel_ids: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    full_run_required: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["kind"] = self.kind.value
        result["channel_ids"] = list(self.channel_ids)
        result["changed_files"] = list(self.changed_files)
        return result


_PLAYLIST_PATHS = {
    "m3u.m3u",
    "m3u-externa.m3u",
    "1.m3u",
    "2.m3u",
    "channel-catalog.m3u",
}
_STREAM_MANIFEST = "stream-overrides.json"
_EPG_MANIFEST = "epg-overrides.json"
_PRESENTATION_MANIFEST = "presentation-overrides.json"
_EPG_MANUAL_OVERRIDES = "epg-manual-overrides.xml"
_INFO_ID_PATTERN = re.compile(r'\btvg-id="([^"]+)"')
_IGNORED_PREFIXES = (
    "README",
    "docs/",
    "tests/",
    ".codex-remote-attachments/",
)
_FULL_FILES = {
    "update_m3u.py",
    "run_m3u_6h.py",
    "run_epg_6h.py",
    "publish_epg.py",
    "generate_health_report.py",
    "resolver-catalog.json",
    "channel-health-state.json",
    "run-state.json",
    "epg-run-state.json",
}


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _sorted_ids(ids: set[str]) -> tuple[str, ...]:
    return tuple(sorted(ids, key=lambda value: (value.casefold(), value)))


def _playlist_records(text: str, *, path: str) -> tuple[dict[str, tuple[str, str]], tuple[str, ...]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    records: dict[str, tuple[str, str]] = {}
    order: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXTINF:"):
            continue
        match = _INFO_ID_PATTERN.search(line)
        if not match:
            raise ChangePlanError(f"{path}: EXTINF sin tvg-id en la linea {index + 1}")
        channel_id = match.group(1).strip()
        if not channel_id:
            raise ChangePlanError(f"{path}: tvg-id vacio en la linea {index + 1}")
        if channel_id in records:
            raise ChangePlanError(f"{path}: tvg-id duplicado: {channel_id}")
        url = None
        for candidate in lines[index + 1 :]:
            candidate = candidate.strip()
            if not candidate:
                continue
            if candidate.startswith("#"):
                raise ChangePlanError(
                    f"{path}: falta URL despues de EXTINF de {channel_id}"
                )
            url = candidate
            break
        if url is None:
            raise ChangePlanError(f"{path}: falta URL de {channel_id}")
        records[channel_id] = (line, url)
        order.append(channel_id)
    return records, tuple(order)


def _manifest_ids(text: str, *, path: str) -> set[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ChangePlanError(f"{path}: JSON invalido: {error}") from error

    raw_channels = payload.get("channels") if isinstance(payload, dict) else None
    if isinstance(raw_channels, dict):
        ids = {str(channel_id).strip() for channel_id in raw_channels}
    elif isinstance(raw_channels, list):
        ids = set()
        for entry in raw_channels:
            if isinstance(entry, str):
                ids.add(entry.strip())
            elif isinstance(entry, dict):
                value = entry.get("tvg_id", entry.get("tvg-id"))
                if value is not None:
                    ids.add(str(value).strip())
            else:
                raise ChangePlanError(f"{path}: entrada de canal invalida")
    elif isinstance(payload, dict):
        # A mapping keyed by tvg-id is convenient for small manual changes.
        ids = {str(channel_id).strip() for channel_id in payload}
    else:
        raise ChangePlanError(f"{path}: se esperaba un objeto JSON")

    ids.discard("")
    if not ids:
        raise ChangePlanError(f"{path}: no declara ningun tvg-id")
    return ids


def _presentation_manifest_ids(text: str, *, path: str) -> set[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ChangePlanError(f"{path}: JSON invalido: {error}") from error
    if not isinstance(payload, dict):
        raise ChangePlanError(f"{path}: se esperaba un objeto JSON")
    presentation = payload.get("presentation", payload)
    if not isinstance(presentation, dict):
        raise ChangePlanError(f"{path}: presentation debe ser un objeto")
    ids: set[str] = set()
    info_lines = presentation.get("info_lines", {})
    if isinstance(info_lines, dict):
        ids.update(str(channel_id).strip() for channel_id in info_lines)
    orders = presentation.get("orders", {})
    if isinstance(orders, dict):
        for order in orders.values():
            if isinstance(order, list):
                ids.update(str(channel_id).strip() for channel_id in order)
    ids.discard("")
    return ids


def _epg_override_ids(text: str, *, path: str) -> set[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ChangePlanError(f"{path}: XML invalido: {error}") from error
    ids = {
        element.get("id", "").strip()
        for element in root.findall("channel")
        if element.get("id", "").strip()
    }
    ids.update(
        element.get("channel", "").strip()
        for element in root.findall("programme")
        if element.get("channel", "").strip()
    )
    if not ids:
        raise ChangePlanError(f"{path}: no contiene canales EPG")
    return ids


def _changed_epg_ids(before: str, after: str, *, path: str) -> set[str]:
    try:
        before_root = ET.fromstring(before)
        after_root = ET.fromstring(after)
    except ET.ParseError as error:
        raise ChangePlanError(f"{path}: XML invalido: {error}") from error

    def channel_payloads(root: ET.Element) -> dict[str, bytes]:
        result: dict[str, bytes] = {}
        for element in root.findall("channel"):
            channel_id = element.get("id", "").strip()
            if channel_id:
                result[channel_id] = ET.tostring(element, encoding="utf-8")
        for element in root.findall("programme"):
            channel_id = element.get("channel", "").strip()
            if channel_id:
                result[channel_id] = result.get(channel_id, b"") + ET.tostring(
                    element, encoding="utf-8"
                )
        return result

    before_payloads = channel_payloads(before_root)
    after_payloads = channel_payloads(after_root)
    if set(before_payloads) != set(after_payloads):
        raise ChangePlanError(f"{path}: cambio de membresia EPG; requiere corrida completa")
    return {
        channel_id
        for channel_id in before_payloads
        if before_payloads[channel_id] != after_payloads[channel_id]
    }


def classify_changes(
    changed_paths: Sequence[str],
    *,
    before: Mapping[str, str] | None = None,
    after: Mapping[str, str] | None = None,
) -> ChangePlan:
    """Return a fail-closed plan for a set of changed repository paths.

    ``before`` and ``after`` contain text snapshots for changed playlists or
    XML.  If a playlist changed but its snapshots are absent, the safe result
    is ``FULL`` because membership and URL intent cannot be proven.
    """

    normalized = tuple(sorted({_normalize_path(path) for path in changed_paths}))
    before = {_normalize_path(path): value for path, value in (before or {}).items()}
    after = {_normalize_path(path): value for path, value in (after or {}).items()}
    if not normalized:
        return ChangePlan(ChangeKind.NOOP, reason="sin archivos modificados")

    full_reasons: list[str] = []
    presentation_ids: set[str] = set()
    stream_ids: set[str] = set()
    epg_ids: set[str] = set()
    presentation_changed = False

    for path in normalized:
        if path in _FULL_FILES or path.startswith(".github/") or path.startswith("scripts/"):
            full_reasons.append(f"{path} altera la logica o el contrato global")
            continue
        if path == _STREAM_MANIFEST:
            if path not in after:
                full_reasons.append("se elimino el manifiesto de streams")
            else:
                stream_ids.update(_manifest_ids(after[path], path=path))
            continue
        if path == _EPG_MANIFEST:
            if path not in after:
                full_reasons.append("se elimino el manifiesto de EPG")
            else:
                epg_ids.update(_manifest_ids(after[path], path=path))
            continue
        if path == _PRESENTATION_MANIFEST:
            if path not in after:
                full_reasons.append("se elimino el manifiesto de presentacion")
            else:
                presentation_ids.update(
                    _presentation_manifest_ids(after[path], path=path)
                )
                presentation_changed = True
            continue
        if path == _EPG_MANUAL_OVERRIDES:
            if path not in after:
                full_reasons.append("se elimino el bloqueo manual de EPG")
            else:
                epg_ids.update(_epg_override_ids(after[path], path=path))
            continue
        if path.startswith("logos/"):
            presentation_ids.update(())
            continue
        if path == "epg.xml":
            if path not in before or path not in after:
                full_reasons.append("no se pudo comparar epg.xml")
            else:
                epg_ids.update(_changed_epg_ids(before[path], after[path], path=path))
            continue
        if path in _PLAYLIST_PATHS:
            if path not in before or path not in after:
                full_reasons.append(f"no se pudo comparar {path}")
                continue
            before_records, before_order = _playlist_records(before[path], path=path)
            after_records, after_order = _playlist_records(after[path], path=path)
            if (
                before[path].replace("\r\n", "\n").replace("\r", "\n")
                != after[path].replace("\r\n", "\n").replace("\r", "\n")
            ):
                presentation_changed = True
            if set(before_records) != set(after_records):
                full_reasons.append(f"{path} cambio la membresia")
                continue
            if before_order != after_order:
                presentation_ids.update(after_records)
            for channel_id in after_records:
                before_info, before_url = before_records[channel_id]
                after_info, after_url = after_records[channel_id]
                if before_url != after_url:
                    stream_ids.add(channel_id)
                if before_info != after_info:
                    presentation_ids.add(channel_id)
            continue
        if any(path.startswith(prefix) for prefix in _IGNORED_PREFIXES):
            continue
        full_reasons.append(f"{path} no tiene una ruta dirigida segura")

    if full_reasons:
        return ChangePlan(
            ChangeKind.FULL,
            channel_ids=_sorted_ids(stream_ids | epg_ids | presentation_ids),
            changed_files=normalized,
            full_run_required=True,
            reason="; ".join(full_reasons),
        )
    if stream_ids and epg_ids:
        raise ChangePlanError(
            "un commit no puede mezclar cambios de stream y EPG; separa las operaciones"
        )
    if stream_ids:
        return ChangePlan(
            ChangeKind.STREAM,
            channel_ids=_sorted_ids(stream_ids),
            changed_files=normalized,
            reason="solo cambiaron streams de los tvg-id indicados",
        )
    if epg_ids:
        return ChangePlan(
            ChangeKind.EPG,
            channel_ids=_sorted_ids(epg_ids),
            changed_files=normalized,
            reason="solo cambiaron fuentes o bloques EPG dirigidos",
        )
    if presentation_ids or presentation_changed or any(
        path.startswith("logos/") for path in normalized
    ):
        return ChangePlan(
            ChangeKind.PRESENTATION,
            channel_ids=_sorted_ids(presentation_ids),
            changed_files=normalized,
            reason="solo cambiaron logos, orden o metadatos de presentacion",
        )
    return ChangePlan(
        ChangeKind.NOOP,
        changed_files=normalized,
        reason="cambios documentales o de pruebas sin artefactos publicos",
    )
