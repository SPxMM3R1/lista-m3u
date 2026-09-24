#!/usr/bin/env python3
"""Build the static, URL-free channel-editor data bundle for GitHub Pages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import update_m3u
import vibem3u_selection


SITE = ROOT / "site"
DEFAULT_OUTPUT = ROOT / "_site"
REPOSITORY = "SPxMM3R1/lista-m3u"
EXTINF_ATTRIBUTE = re.compile(r'([\w-]+)="([^"]*)"')
UNSAFE_PROVIDER_TEXT = re.compile(
    r"https?://|\.m3u8?(?:\b|\?)|\.mpd(?:\b|\?)|access_token=|token=|signature=|hdnts=|[\r\n]",
    re.I,
)
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
EDITOR_LAYOUT_PATH = Path("data/channel-editor-layout.json")
SELECTION_PATH = Path("data/vibem3u-selection.json")
PRESENTATION_PATH = Path("presentation-overrides.json")


def _read_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback.copy() if fallback is not None else {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.relative_to(ROOT)} no es JSON valido: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(ROOT)} debe ser un objeto JSON")
    return payload


def _blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _logo_path(logo_value: str) -> str | None:
    if not logo_value:
        return None
    parsed = urlsplit(logo_value)
    path = parsed.path.lstrip("/")
    if "/logos/" in path:
        path = "logos/" + path.split("/logos/", 1)[1]
    if not path.startswith("logos/") or any(part in {"", ".", ".."} for part in path.split("/")):
        return None
    candidate = ROOT / Path(*path.split("/"))
    try:
        candidate.resolve().relative_to((ROOT / "logos").resolve())
    except ValueError:
        return None
    return path if candidate.is_file() else None


def parse_playlist(text: str, source_list: str) -> list[dict[str, object]]:
    """Parse only editorial metadata; never retain the following stream line."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError(f"{source_list} no contiene una cabecera #EXTM3U")
    channels: list[dict[str, object]] = []
    for line in lines:
        if not line.startswith("#EXTINF:"):
            continue
        metadata, comma, display = line.rpartition(",")
        if not comma:
            raise ValueError(f"{source_list} contiene un #EXTINF sin nombre")
        attrs = {key: value for key, value in EXTINF_ATTRIBUTE.findall(metadata)}
        # Legacy short playlists can still contain rows managed exclusively
        # by VibeM3U. Keep those out of the direct-M3U source: their stable
        # catalogKey comes from the selection manifest instead.
        if attrs.get("x-resolver", "").casefold() in {"highfly", "tvvoo"}:
            continue
        if attrs.get("x-vibem3u-selection", "").casefold() == "managed":
            continue
        tvg_id = attrs.get("tvg-id", "").strip()
        name = (attrs.get("tvg-name") or display).strip()
        if not tvg_id or not name:
            raise ValueError(f"{source_list} contiene un canal sin tvg-id o nombre")
        channels.append(
            {
                "kind": "m3u",
                "tvgId": tvg_id,
                "name": name,
                "group": attrs.get("group-title", ""),
                "country": attrs.get("tvg-country", ""),
                "sourceList": source_list,
                "logoPath": _logo_path(attrs.get("tvg-logo", "")),
            }
        )
    return channels


def parse_provider_identities(text: str) -> list[dict[str, str]]:
    """Export only canonical IDs/names for exact provider identity matching."""
    identities: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in text.lstrip("\ufeff").splitlines():
        if not line.startswith("#EXTINF:"):
            continue
        metadata, comma, display = line.rpartition(",")
        if not comma:
            continue
        attrs = {key: value for key, value in EXTINF_ATTRIBUTE.findall(metadata)}
        if attrs.get("x-resolver", "").casefold() == "tvvoo":
            continue
        catalog_key = attrs.get("tvg-id", "").strip()
        name = (attrs.get("tvg-name") or display).strip()
        if (
            not catalog_key
            or catalog_key.casefold().startswith("leaf:")
            or not name
            or any(UNSAFE_PROVIDER_TEXT.search(value) for value in (catalog_key, name))
        ):
            continue
        identity = (catalog_key, name)
        if identity in seen:
            continue
        seen.add(identity)
        identities.append({"catalogKey": catalog_key, "name": name})
    return identities


def _provider_row(provider: str, row: dict) -> dict[str, object]:
    """Keep stable identity and resolver references, but no provider URLs."""
    allowed = (
        "catalogKey",
        "providerResourceId",
        "resolverSlug",
        "alias",
        "country",
        "countryKey",
        "name",
        "group",
        "category",
        "aliases",
        "resolverAliases",
        "identityState",
        "order",
        "enabled",
    )
    result = {key: row[key] for key in allowed if key in row}
    result["kind"] = "provider"
    result["provider"] = provider
    return result


def _unique_provider_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep the first ordered resolver candidate for each stable channel key."""
    unique: dict[tuple[str, str], dict[str, object]] = {}
    for row in sorted(rows, key=lambda item: (int(item.get("order", 0) or 0), str(item.get("catalogKey", "")))):
        key = (str(row.get("provider", "")), str(row.get("catalogKey", "")))
        unique.setdefault(key, row)
    return list(unique.values())


def initial_layout(catalog: list[dict[str, object]]) -> dict[str, object]:
    channels = []
    for order, channel in enumerate(catalog, start=1):
        row = {key: channel[key] for key in (
            "kind", "tvgId", "name", "group", "country", "sourceList", "logoPath",
            "provider", "catalogKey", "providerResourceId", "resolverSlug", "alias",
            "countryKey", "category", "aliases", "resolverAliases", "identityState",
        ) if key in channel and channel[key] not in (None, "")}
        row.update({"order": order, "number": order, "state": "active"})
        channels.append(row)
    return {"schemaVersion": 1, "excludedM3u": [], "channels": channels}


def apply_saved_direct_order(
    catalog: list[dict[str, object]], presentation: dict[str, object]
) -> list[dict[str, object]]:
    surface = presentation.get("presentation", presentation)
    orders = surface.get("orders", {}) if isinstance(surface, dict) else {}
    if not isinstance(orders, dict):
        return catalog
    result: list[dict[str, object]] = []
    for source_list, canonical_name in (("1.m3u", "m3u.m3u"), ("2.m3u", "m3u-externa.m3u")):
        rows = [row for row in catalog if row.get("sourceList") == source_list]
        stored = orders.get(canonical_name, orders.get(source_list, []))
        if not isinstance(stored, list):
            stored = []
        by_id = {str(row["tvgId"]): row for row in rows}
        used: set[str] = set()
        for raw_id in stored:
            channel_id = str(raw_id)
            if channel_id in by_id and channel_id not in used:
                result.append(by_id[channel_id])
                used.add(channel_id)
        result.extend(row for row in rows if str(row["tvgId"]) not in used)
    result.extend(row for row in catalog if row.get("kind") == "provider")
    return result


def validate_layout(layout: dict[str, object]) -> None:
    if layout.get("schemaVersion") != 1 or not isinstance(layout.get("channels"), list):
        raise ValueError("data/channel-editor-layout.json debe usar schemaVersion 1 y channels[]")
    exclusions = layout.get("excludedM3u", [])
    if not isinstance(exclusions, list) or any(not isinstance(item, str) for item in exclusions):
        raise ValueError("data/channel-editor-layout.json: excludedM3u debe ser una lista de tvg-id")
    normalized_exclusions = [item.strip() for item in exclusions]
    if (
        any(
            not item
            or len(item) > 512
            or "://" in item
            or re.search(r"\.m3u8?(?:\b|\?)|\.mpd$|[\r\n]", item, re.I)
            for item in normalized_exclusions
        )
        or len(set(normalized_exclusions)) != len(normalized_exclusions)
    ):
        raise ValueError("data/channel-editor-layout.json: excludedM3u contiene IDs no válidos o repetidos")
    seen: set[tuple[str, str]] = set()
    seen_public_ids: set[str] = set()
    seen_orders: set[int] = set()
    active_numbers: set[int] = set()
    for index, row in enumerate(layout["channels"]):
        if not isinstance(row, dict):
            raise ValueError(f"layout.channels[{index}] debe ser un objeto")
        kind = row.get("kind")
        identity = row.get("tvgId") if kind == "m3u" else row.get("catalogKey")
        if kind not in {"m3u", "provider"} or not isinstance(identity, str) or not identity:
            raise ValueError(f"layout.channels[{index}] no tiene identidad estable")
        key = (str(kind), identity)
        if key in seen:
            raise ValueError(f"layout contiene identidad duplicada: {identity}")
        seen.add(key)
        if identity in seen_public_ids:
            raise ValueError(f"layout repite la identidad publica: {identity}")
        seen_public_ids.add(identity)
        if identity in {"", ".", ".."} or "://" in identity or identity.startswith("leaf:"):
            raise ValueError(f"layout contiene identidad no estable: {identity}")
        if kind == "m3u" and row.get("sourceList") not in {"1.m3u", "2.m3u"}:
            raise ValueError(f"layout.channels[{index}].sourceList debe ser 1.m3u o 2.m3u")
        if row.get("state") not in {"active", "hidden", "deleted"}:
            raise ValueError(f"layout.channels[{index}].state invalido")
        for field in ("order", "number"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"layout.channels[{index}].{field} debe ser entero positivo")
        if row["order"] in seen_orders:
            raise ValueError(f"layout contiene order duplicado: {row['order']}")
        seen_orders.add(row["order"])
        if row["state"] == "active":
            if row["number"] in active_numbers:
                raise ValueError(f"layout contiene number activo duplicado: {row['number']}")
            active_numbers.add(row["number"])
            if kind == "m3u" and identity in normalized_exclusions:
                raise ValueError(f"layout: canal M3U activo pero excluido: {identity}")
        if kind == "provider":
            provider = row.get("provider")
            if provider not in {"highfly", "tvvoo"}:
                raise ValueError(f"layout.channels[{index}].provider no permitido")
            resource_id = row.get("providerResourceId")
            if provider == "highfly":
                slug = row.get("resolverSlug")
                if (
                    not isinstance(resource_id, str)
                    or not resource_id.startswith("leaf:")
                    or not isinstance(slug, str)
                    or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,127}", slug)
                    or resource_id[5:] != slug
                ):
                    raise ValueError(f"identidad/referencia Highfly invalida para {identity}")
            elif resource_id != identity:
                raise ValueError(f"TvVoo debe conservar providerResourceId=catalogKey para {identity}")
            if provider == "tvvoo" and len(identity.split("|")) != 2:
                raise ValueError(f"catalogKey TvVoo invalido para {identity}")
        descriptive = (row.get("name"), row.get("group"), row.get("category"), row.get("country"))
        if any(
            isinstance(value, str)
            and re.search(r"https?://|\.m3u8?(?:\b|\?)|access_token=|token=|signature=|hdnts=", value, re.I)
            for value in descriptive
        ):
            raise ValueError(f"layout contiene una URL o credencial en metadatos: {identity}")


def runner_identity_status(selection: dict[str, object]) -> dict[str, object]:
    catalog_path = ROOT / "channel-catalog.m3u"
    lines = catalog_path.read_text(encoding="utf-8-sig").splitlines()
    document = vibem3u_selection.load_selection(ROOT / SELECTION_PATH)
    report = vibem3u_selection.reconcile_selection(
        document,
        update_m3u.parse_channels(lines),
        lines,
    )
    rows: list[dict[str, str]] = []
    for match in report.matched:
        rows.append({
            "provider": match.row.provider,
            "catalogKey": match.row.catalog_key,
            "status": "matched",
        })
    for pending in report.pending:
        rows.append({
            "provider": str(pending.get("provider", "")),
            "catalogKey": str(pending.get("catalogKey", "")),
            "status": "pending",
            "reason": str(pending.get("reason", "identity_unresolved")),
        })
    return {"scope": "identity-match-only", "rows": rows}


def build_bundle(output: Path = DEFAULT_OUTPUT) -> Path:
    direct_catalog: list[dict[str, object]] = []
    for filename in ("1.m3u", "2.m3u"):
        path = ROOT / filename
        direct_catalog.extend(parse_playlist(path.read_text(encoding="utf-8-sig"), filename))

    presentation = _read_json(
        ROOT / PRESENTATION_PATH,
        {"schema": 1, "orders": {}, "info_lines": {}, "logos": {}, "excluded_m3u": [], "assets": []},
    )
    catalog = apply_saved_direct_order(direct_catalog, presentation)

    selection = _read_json(ROOT / SELECTION_PATH)
    sources = selection.get("sources")
    if not isinstance(sources, list):
        raise ValueError("data/vibem3u-selection.json: sources debe ser una lista")
    provider_catalog: list[dict[str, object]] = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("cada source de VibeM3U debe ser un objeto")
        provider = str(source.get("provider", "")).casefold()
        if provider not in {"highfly", "tvvoo"}:
            raise ValueError(f"provider no permitido en seleccion: {provider}")
        rows = source.get("channels", [])
        if not isinstance(rows, list):
            raise ValueError(f"sources.{provider}.channels debe ser una lista")
        if source.get("enabled") is False:
            continue
        provider_catalog.extend(
            _provider_row(provider, row)
            for row in rows
            if isinstance(row, dict)
        )
    catalog.extend(_unique_provider_rows(provider_catalog))

    layout = _read_json(ROOT / EDITOR_LAYOUT_PATH)
    if not layout:
        layout = initial_layout(catalog)
    validate_layout(layout)

    # Hidden and trashed provider entries leave the active runner manifest,
    # but their stable identity and token-free resolver references remain in
    # the editorial layout so the user can restore them.
    by_identity = {
        (row.get("kind"), row.get("tvgId") if row.get("kind") == "m3u" else row.get("catalogKey")): row
        for row in catalog
    }
    for row in layout["channels"]:
        key = (row.get("kind"), row.get("tvgId") if row.get("kind") == "m3u" else row.get("catalogKey"))
        if key not in by_identity:
            catalog.append(dict(row))

    logos = sorted(
        {
            f"logos/{path.relative_to(ROOT / 'logos').as_posix()}"
            for path in (ROOT / "logos").rglob("*")
            if path.is_file() and path.suffix.casefold() in ALLOWED_LOGO_EXTENSIONS
        }
    )
    out = output.resolve()
    if out != DEFAULT_OUTPUT.resolve():
        temp_root = Path(tempfile.gettempdir()).resolve()
        try:
            out.relative_to(temp_root)
        except ValueError as exc:
            raise ValueError(
                f"la salida alternativa debe estar dentro de la carpeta temporal {temp_root}"
            ) from exc
        if out == temp_root:
            raise ValueError("la salida alternativa no puede ser la carpeta temporal raíz")
    out.mkdir(parents=True, exist_ok=True)
    for source in SITE.rglob("*"):
        relative = source.relative_to(SITE)
        target = out / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "catalog.json").write_text(
        json.dumps({"channels": catalog}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    channel_catalog_path = ROOT / "channel-catalog.m3u"
    identities = parse_provider_identities(channel_catalog_path.read_text(encoding="utf-8-sig"))
    (data_dir / "provider-identities.json").write_text(
        json.dumps({"identities": identities}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (data_dir / "logos.json").write_text(
        json.dumps({"logos": logos}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (data_dir / "selection.json").write_text(
        json.dumps(selection, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (data_dir / "layout.json").write_text(
        json.dumps(layout, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (data_dir / "presentation.json").write_text(
        json.dumps(presentation, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (data_dir / "runner-status.json").write_text(
        json.dumps(runner_identity_status(selection), ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    shas = {}
    for path in (SELECTION_PATH, EDITOR_LAYOUT_PATH, PRESENTATION_PATH):
        absolute = ROOT / path
        shas[path.as_posix()] = _blob_sha(absolute.read_bytes()) if absolute.is_file() else None
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "local"
    (data_dir / "repository.json").write_text(
        json.dumps({"repository": REPOSITORY, "revision": revision, "fileShas": shas}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Static editor bundle: {out} ({len(catalog)} channels, {len(logos)} logos)")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--seed-layout",
        action="store_true",
        help="crea una sola vez el archivo editorial inicial si aún no existe",
    )
    args = parser.parse_args()
    build_bundle(args.output)
    if args.seed_layout:
        target = ROOT / EDITOR_LAYOUT_PATH
        if target.exists():
            raise ValueError(f"no se reemplaza un diseño editorial existente: {target}")
        generated = DEFAULT_OUTPUT / "data" / "layout.json"
        payload = _read_json(generated)
        validate_layout(payload)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Diseño editorial inicial creado: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
