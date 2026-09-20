"""Validate and reconcile the token-free VibeM3U selection manifest.

The Android application publishes provider identities, not a playlist.  This
module deliberately knows nothing about HLS resolution: ``catalogKey`` is the
only durable identity and provider resource fields are validated as
replaceable references.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, unquote, urlparse


SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = 262_144
ALLOWED_PROVIDERS = frozenset({"highfly", "tvvoo"})
SELECTION_MARKER_ATTRIBUTE = "x-vibem3u-selection"
SELECTION_MARKER_VALUE = "managed"
HIGHFLY_RESOURCE_PATTERN = re.compile(r"^leaf:[a-z0-9][a-z0-9_-]{1,127}$", re.IGNORECASE)
HIGHFLY_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,127}$", re.IGNORECASE)
TVVOO_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\|vavoo_[^|\s]+(?:\|group:[^|\s]+)?$")
SAFE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@|:%-]{0,255}$")
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:token|password|passwd|secret|serverkey|signature|authorization|cookie|credential)",
    re.IGNORECASE,
)
SIGNED_QUERY_KEYS = frozenset(
    {"token", "access_token", "signature", "sig", "auth", "expires", "exp", "key"}
)


class SelectionError(ValueError):
    """Raised when a published selection cannot be safely consumed."""


@dataclass(frozen=True)
class SelectionRow:
    provider: str
    catalog_key: str
    provider_resource_id: str
    resolver_slug: str
    name: str
    group: str
    category: str
    country_key: str
    identity_state: str
    order: int
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class SelectionDocument:
    present: bool
    published_at: str
    rows: tuple[SelectionRow, ...]
    disabled_providers: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedSelection:
    row: SelectionRow
    catalog_index: int
    catalog_id: str
    match: str


@dataclass(frozen=True)
class SelectionReconciliation:
    document: SelectionDocument
    matched: tuple[ResolvedSelection, ...]
    pending: tuple[dict[str, str], ...]

    @property
    def selected_catalog_ids(self) -> frozenset[str]:
        return frozenset(item.catalog_id for item in self.matched)

    @property
    def managed_catalog_ids(self) -> frozenset[str]:
        return self.selected_catalog_ids

    def report(self) -> dict[str, object]:
        return {
            "present": self.document.present,
            "selected_rows": len(self.document.rows),
            "matched_rows": len(self.matched),
            "pending_rows": len(self.pending),
            "disabled_providers": list(self.document.disabled_providers),
            "matched": [
                {
                    "provider": item.row.provider,
                    "catalogKey": item.row.catalog_key,
                    "tvg_id": item.catalog_id,
                    "match": item.match,
                }
                for item in self.matched
            ],
            "pending": [dict(item) for item in self.pending],
        }


def load_selection(path: Path) -> SelectionDocument:
    """Load and validate one selection document.

    A missing file is an intentional no-op so a Lista M3U checkout can run
    before the first Android publication.  A present but malformed file fails
    closed rather than changing public membership.
    """

    if not path.is_file():
        return SelectionDocument(False, "", tuple(), tuple())
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise SelectionError(f"{path.name} no se pudo leer: {error}") from error
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise SelectionError(f"{path.name} supera el limite de 256 KiB")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SelectionError(f"{path.name} no es JSON UTF-8 valido: {error}") from error
    if not isinstance(payload, dict):
        raise SelectionError(f"{path.name} debe contener un objeto JSON")
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise SelectionError(f"{path.name} debe usar schemaVersion {SCHEMA_VERSION}")
    _reject_sensitive_values(payload)
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise SelectionError(f"{path.name}: sources debe ser una lista")

    rows: list[SelectionRow] = []
    disabled: list[str] = []
    seen_keys: set[tuple[str, str]] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise SelectionError(f"{path.name}: cada source debe ser un objeto")
        provider = _required_text(source, "provider", path.name).casefold()
        if provider not in ALLOWED_PROVIDERS:
            raise SelectionError(f"{path.name}: provider no permitido: {provider}")
        enabled = source.get("enabled")
        if not isinstance(enabled, bool):
            raise SelectionError(f"{path.name}: enabled invalido para {provider}")
        if not enabled:
            disabled.append(provider)
        raw_channels = source.get("channels", [])
        if not isinstance(raw_channels, list):
            raise SelectionError(f"{path.name}: channels invalido para {provider}")
        for raw_row in raw_channels:
            row = _parse_row(raw_row, provider, path.name)
            if not enabled:
                continue
            key = (row.provider, row.catalog_key)
            if key in seen_keys:
                raise SelectionError(
                    f"{path.name}: catalogKey duplicado: {row.provider}/{row.catalog_key}"
                )
            seen_keys.add(key)
            rows.append(row)
    rows.sort(key=lambda item: (item.order, item.provider, item.catalog_key))
    return SelectionDocument(
        True,
        _optional_text(payload, "publishedAt"),
        tuple(rows),
        tuple(sorted(set(disabled))),
    )


def reconcile_selection(
    document: SelectionDocument,
    catalog_channels: Iterable[Any],
    catalog_lines: list[str],
) -> SelectionReconciliation:
    """Match selection rows to exactly one existing canonical catalogue row."""

    channels = list(catalog_channels)
    matched: list[ResolvedSelection] = []
    pending: list[dict[str, str]] = []
    used_catalog_indexes: set[int] = set()
    for row in document.rows:
        if row.identity_state != "canonical":
            pending.append(_pending(row, "identity_provisional"))
            continue
        candidates: list[tuple[int, str]] = []
        for index, channel in enumerate(channels):
            match = _match_row(row, channel, catalog_lines)
            if match:
                candidates.append((index, match))
        if not candidates:
            pending.append(_pending(row, "catalog_not_found"))
            continue
        if len(candidates) > 1:
            pending.append(_pending(row, "catalog_match_ambiguous"))
            continue
        index, match = candidates[0]
        if index in used_catalog_indexes:
            pending.append(_pending(row, "catalog_identity_already_selected"))
            continue
        used_catalog_indexes.add(index)
        catalog_id = str(getattr(channels[index], "tvg_id", "")).strip()
        if not catalog_id:
            pending.append(_pending(row, "catalog_missing_tvg_id"))
            continue
        matched.append(ResolvedSelection(row, index, catalog_id, match))
    return SelectionReconciliation(document, tuple(matched), tuple(pending))


def selection_marker_is_managed(info_line: str) -> bool:
    return bool(
        re.search(
            rf'\b{re.escape(SELECTION_MARKER_ATTRIBUTE)}="{re.escape(SELECTION_MARKER_VALUE)}"',
            info_line,
        )
    )


def with_selection_marker(info_line: str, managed: bool) -> str:
    """Add/remove the runner-owned marker without changing presentation data."""

    metadata, separator, display_name = info_line.rpartition(",")
    if not separator or not metadata.startswith("#EXTINF:"):
        raise SelectionError("linea #EXTINF invalida al marcar la seleccion")
    metadata = re.sub(
        rf'\s+{re.escape(SELECTION_MARKER_ATTRIBUTE)}="[^"]*"',
        "",
        metadata,
    )
    if managed:
        metadata += f' {SELECTION_MARKER_ATTRIBUTE}="{SELECTION_MARKER_VALUE}"'
    return f"{metadata},{display_name}"


def _parse_row(raw_row: object, provider: str, filename: str) -> SelectionRow:
    if not isinstance(raw_row, dict):
        raise SelectionError(f"{filename}: cada channel debe ser un objeto")
    row_provider = _required_text(raw_row, "provider", filename).casefold()
    if row_provider != provider:
        raise SelectionError(f"{filename}: provider de channel no coincide con source")
    catalog_key = _required_text(raw_row, "catalogKey", filename)
    _validate_catalog_key(provider, catalog_key, filename)
    name = _required_text(raw_row, "name", filename)
    group = _required_text(raw_row, "group", filename)
    category = _required_text(raw_row, "category", filename)
    identity_state = _required_text(raw_row, "identityState", filename).casefold()
    if identity_state not in {"canonical", "provisional"}:
        raise SelectionError(f"{filename}: identityState invalido para {catalog_key}")
    order = raw_row.get("order")
    if isinstance(order, bool) or not isinstance(order, int) or order < 1:
        raise SelectionError(f"{filename}: order invalido para {catalog_key}")
    country_key = _optional_text(raw_row, "countryKey")
    aliases = _text_list(raw_row.get("aliases", raw_row.get("resolverAliases", [])), filename)
    if provider == "highfly":
        resource = _required_text(raw_row, "providerResourceId", filename)
        slug = _required_text(raw_row, "resolverSlug", filename)
        if not HIGHFLY_RESOURCE_PATTERN.fullmatch(resource):
            raise SelectionError(f"{filename}: providerResourceId Highfly invalido")
        if not HIGHFLY_SLUG_PATTERN.fullmatch(slug) or resource[5:] != slug:
            raise SelectionError(f"{filename}: resolverSlug Highfly no coincide con leaf")
    else:
        resource = _required_text(raw_row, "providerResourceId", filename)
        if resource != catalog_key:
            raise SelectionError(f"{filename}: TvVoo debe conservar providerResourceId=stableId")
        slug = ""
        stable_alias = catalog_key.split("|", 1)[1]
        if stable_alias not in aliases:
            aliases = (stable_alias,) + aliases
    for value in (name, group, category, country_key, *aliases):
        if "\n" in value or "\r" in value or len(value) > 512:
            raise SelectionError(f"{filename}: texto invalido para {catalog_key}")
    return SelectionRow(
        provider,
        catalog_key,
        resource,
        slug,
        name,
        group,
        category,
        country_key,
        identity_state,
        order,
        tuple(dict.fromkeys(aliases)),
    )


def _validate_catalog_key(provider: str, value: str, filename: str) -> None:
    if not value or len(value) > 256 or not SAFE_KEY_PATTERN.fullmatch(value):
        raise SelectionError(f"{filename}: catalogKey invalido")
    if value.isdigit() or value.lower().startswith("leaf:") or "/" in value:
        raise SelectionError(f"{filename}: catalogKey no puede ser un localizador")
    if provider == "tvvoo" and not TVVOO_KEY_PATTERN.fullmatch(value):
        raise SelectionError(f"{filename}: catalogKey TvVoo debe ser country|vavoo_alias")


def _match_row(row: SelectionRow, channel: Any, lines: list[str]) -> str:
    tvg_id = str(getattr(channel, "tvg_id", "") or "")
    if row.provider == "highfly":
        return "catalogKey=tvg-id" if tvg_id == row.catalog_key else ""
    stable_alias = row.catalog_key.split("|", 1)[1]
    stable_aliases = {stable_alias, unquote(stable_alias)}
    if tvg_id in {row.catalog_key, row.catalog_key + "@TvVoo"}:
        return "catalogKey=tvg-id"
    info_line = ""
    info_index = getattr(channel, "info_line", -1)
    if isinstance(info_index, int) and 0 <= info_index < len(lines):
        info_line = lines[info_index]
    resolver_aliases = {
        unquote(alias)
        for alias in re.findall(r'\bx-resolver-ids="([^"]*)"', info_line)
        for alias in alias.split(";")
        if alias
    }
    row_aliases = {alias for value in row.aliases for alias in (value, unquote(value))}
    if stable_aliases.intersection(resolver_aliases) or resolver_aliases.intersection(row_aliases):
        return "catalogKey=resolver-alias"
    return ""


def _pending(row: SelectionRow, reason: str) -> dict[str, str]:
    return {
        "provider": row.provider,
        "catalogKey": row.catalog_key,
        "identityState": row.identity_state,
        "status": "pending",
        "reason": reason,
    }


def _required_text(payload: dict[str, Any], key: str, filename: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SelectionError(f"{filename}: falta {key}")
    return value.strip()


def _optional_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _text_list(value: object, filename: str) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SelectionError(f"{filename}: aliases debe ser una lista de textos")
    return tuple(item.strip() for item in value if item.strip())


def _reject_sensitive_values(value: object, path: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            if key_text != "selectionSignature" and SENSITIVE_KEY_PATTERN.search(key_text):
                raise SelectionError(f"selection contiene un campo sensible: {key_text}")
            _reject_sensitive_values(nested, f"{path}.{key_text}")
        return
    if not isinstance(value, str):
        if isinstance(value, list):
            for nested in value:
                _reject_sensitive_values(nested, path)
        return
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        return
    suffix = parsed.path.lower()
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
    if suffix.endswith((".m3u8", ".mpd")) or query_keys.intersection(SIGNED_QUERY_KEYS):
        raise SelectionError(f"selection contiene una URL de reproduccion temporal: {path}")
