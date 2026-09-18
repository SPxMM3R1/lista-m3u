"""Apply safe, channel-scoped repository changes.

This module is intentionally separate from ``run_m3u_6h.py``.  It never
advances the six-hour state files and never performs a full catalogue probe.
The scheduled workflows remain responsible for volatile resolver renewal.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import change_plan
import update_m3u


PROJECT_ROOT = Path(__file__).resolve().parent
PLAYLIST_NAMES = (
    "channel-catalog.m3u",
    "m3u.m3u",
    "m3u-externa.m3u",
    "1.m3u",
    "2.m3u",
)
PLAYLIST_PATHS = tuple(PROJECT_ROOT / name for name in PLAYLIST_NAMES)
EPG_PATH = PROJECT_ROOT / "epg.xml"


def _git_text(base: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{base}:{path}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8-sig")


def repository_plan(base: str) -> tuple[change_plan.ChangePlan, dict[str, str], dict[str, str]]:
    """Classify the committed diff from ``base`` to ``HEAD``."""
    if not base or set(base) == {"0"}:
        raise change_plan.ChangePlanError(
            "el push no tiene un commit base comparable; requiere corrida completa"
        )
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    before: dict[str, str] = {}
    after: dict[str, str] = {}
    for path in paths:
        old = _git_text(base, path)
        if old is not None:
            before[path] = old
        current = PROJECT_ROOT / path
        if current.is_file():
            after[path] = current.read_text(encoding="utf-8-sig")
    return change_plan.classify_changes(paths, before=before, after=after), before, after


def _records(text: str) -> dict[str, tuple[str, str]]:
    channels = update_m3u.parse_channels(text.splitlines())
    return {
        channel.tvg_id: (text.splitlines()[channel.info_line], channel.url)
        for channel in channels
    }


def _manifest_entries(text: str, *, path: str) -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise change_plan.ChangePlanError(f"{path}: JSON invalido: {error}") from error
    raw_channels = payload.get("channels") if isinstance(payload, dict) else None
    if raw_channels is None and isinstance(payload, dict):
        raw_channels = payload
    entries: dict[str, dict[str, str]] = {}
    if isinstance(raw_channels, dict):
        iterator = raw_channels.items()
        for channel_id, raw_entry in iterator:
            entry = raw_entry if isinstance(raw_entry, dict) else {"url": raw_entry}
            entries[str(channel_id).strip()] = {
                str(key): str(value).strip()
                for key, value in entry.items()
                if value is not None
            }
    elif isinstance(raw_channels, list):
        for raw_entry in raw_channels:
            if not isinstance(raw_entry, dict):
                raise change_plan.ChangePlanError(f"{path}: entrada de canal invalida")
            channel_id = raw_entry.get("tvg_id", raw_entry.get("tvg-id"))
            if channel_id is None:
                raise change_plan.ChangePlanError(f"{path}: entrada sin tvg_id")
            entries[str(channel_id).strip()] = {
                str(key): str(value).strip()
                for key, value in raw_entry.items()
                if value is not None
            }
    else:
        raise change_plan.ChangePlanError(f"{path}: channels debe ser objeto o lista")
    entries = {channel_id: entry for channel_id, entry in entries.items() if channel_id}
    if not entries:
        raise change_plan.ChangePlanError(f"{path}: no declara canales")
    return entries


def _collect_stream_urls(
    plan: change_plan.ChangePlan,
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, str]:
    updates: dict[str, str] = {}
    # Manual dispatch can be used as a scoped validation of the URLs already
    # present in the catalog. A push carrying a manifest still must provide a
    # concrete URL and therefore cannot take this shortcut.
    if not plan.changed_files:
        return updates
    for path in plan.changed_files:
        if path not in change_plan._PLAYLIST_PATHS:
            continue
        if path not in before or path not in after:
            continue
        before_records = _records(before[path])
        after_records = _records(after[path])
        for channel_id in set(before_records) & set(after_records):
            old_url = before_records[channel_id][1]
            new_url = after_records[channel_id][1]
            if old_url == new_url:
                continue
            previous = updates.setdefault(channel_id, new_url)
            if previous != new_url:
                raise change_plan.ChangePlanError(
                    f"{channel_id}: el commit propone URLs distintas en varias listas"
                )

    manifest_path = "stream-overrides.json"
    if manifest_path in after:
        for channel_id, entry in _manifest_entries(after[manifest_path], path=manifest_path).items():
            url = entry.get("url") or entry.get("stream_url") or entry.get("candidate_url")
            if not url or not url.startswith(("http://", "https://")):
                raise change_plan.ChangePlanError(
                    f"{manifest_path}: {channel_id} necesita url, stream_url o candidate_url"
                )
            previous = updates.setdefault(channel_id, url)
            if previous != url:
                raise change_plan.ChangePlanError(
                    f"{channel_id}: URL de stream contradictoria"
                )
    missing = sorted(set(plan.channel_ids) - set(updates))
    if missing:
        raise change_plan.ChangePlanError(
            "no se pudo obtener la URL nueva para: " + ", ".join(missing)
        )
    return updates


def _collect_info_updates(
    plan: change_plan.ChangePlan,
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, str]:
    updates: dict[str, str] = {}
    for path in plan.changed_files:
        if path not in change_plan._PLAYLIST_PATHS:
            continue
        if path not in before or path not in after:
            continue
        before_records = _records(before[path])
        after_records = _records(after[path])
        for channel_id in set(before_records) & set(after_records):
            old_info = before_records[channel_id][0]
            new_info = after_records[channel_id][0]
            if old_info == new_info:
                continue
            previous = updates.setdefault(channel_id, new_info)
            if previous != new_info:
                raise change_plan.ChangePlanError(
                    f"{channel_id}: metadatos contradictorios en varias listas"
                )
    return updates


def _playlist_lines() -> dict[Path, list[str]]:
    return {
        path: path.read_text(encoding="utf-8-sig").splitlines()
        for path in PLAYLIST_PATHS
        if path.exists()
    }


def apply_playlist_text_updates(
    texts: dict[str, str],
    url_updates: dict[str, str],
    info_updates: dict[str, str],
) -> dict[str, str]:
    """Apply only the requested records to in-memory playlist text."""
    updated: dict[str, str] = {}
    for path, text in texts.items():
        lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        channels = update_m3u.parse_channels(lines)
        for channel in channels:
            if channel.tvg_id in info_updates:
                lines[channel.info_line] = info_updates[channel.tvg_id]
            if channel.tvg_id in url_updates:
                lines[channel.url_line] = url_updates[channel.tvg_id]
        updated[path] = "\n".join(lines) + "\n"
    return updated


def reorder_playlist_lines(lines: list[str], desired_ids: list[str]) -> list[str]:
    """Rebuild presentation order while retaining current channel records."""
    channels = update_m3u.parse_channels(lines)
    if not channels:
        return list(lines)
    rank = {channel_id: index for index, channel_id in enumerate(desired_ids)}
    ordered = sorted(
        channels,
        key=lambda channel: (rank.get(channel.tvg_id, len(rank)), channel.info_line),
    )
    first_info = min(channel.info_line for channel in channels)
    header = [line for line in lines[:first_info] if line.startswith("#EXTM3U")]
    if not header:
        header = ["#EXTM3U"]
    result = list(header)
    previous_group = None
    for channel in ordered:
        if channel.group != previous_group:
            result.extend(["", f"# {channel.group}" if channel.group else ""])
            previous_group = channel.group
        result.extend((lines[channel.info_line], lines[channel.url_line]))
    return result


def _apply_playlist_updates(
    url_updates: dict[str, str],
    info_updates: dict[str, str],
) -> dict[Path, list[str]]:
    texts = {
        path.name: "\n".join(lines) + "\n"
        for path, lines in _playlist_lines().items()
    }
    updated_texts = apply_playlist_text_updates(texts, url_updates, info_updates)
    return {
        PROJECT_ROOT / name: text.splitlines()
        for name, text in updated_texts.items()
    }


def _validate_partition(updated: dict[Path, list[str]]) -> None:
    catalog_lines = updated[PROJECT_ROOT / "channel-catalog.m3u"]
    main_lines = updated[PROJECT_ROOT / "m3u.m3u"]
    external_lines = updated[PROJECT_ROOT / "m3u-externa.m3u"]
    catalog_channels = update_m3u.parse_channels(catalog_lines)
    manual_ids = update_m3u.load_manual_main_channel_ids(
        catalog_channels,
        PROJECT_ROOT / "m3u.m3u",
    )
    external_ids = {
        channel.tvg_id for channel in update_m3u.parse_channels(external_lines)
    }
    update_m3u.validate_resolver_contract(catalog_lines)
    update_m3u.validate_public_playlist_partition(
        catalog_lines,
        main_lines,
        external_lines,
        manual_ids,
        expected_external_ids=external_ids,
    )


def _write_playlists(updated: dict[Path, list[str]]) -> None:
    for path, lines in updated.items():
        new_text = "\n".join(lines) + "\n"
        if path.read_text(encoding="utf-8-sig") == new_text:
            continue
        path.write_text(new_text, encoding="utf-8", newline="\n")
    update_m3u.sync_short_playlist_aliases()


def apply_presentation(
    plan: change_plan.ChangePlan,
    before: dict[str, str],
    after: dict[str, str],
) -> None:
    info_updates = _collect_info_updates(plan, before, after)
    updated = _apply_playlist_updates({}, info_updates)
    if "channel-catalog.m3u" in plan.changed_files:
        catalog_before = before.get("channel-catalog.m3u", "")
        catalog_after = after.get("channel-catalog.m3u", "")
        if catalog_before and catalog_after:
            before_ids = [channel.tvg_id for channel in update_m3u.parse_channels(catalog_before.splitlines())]
            after_catalog = update_m3u.parse_channels(updated[PROJECT_ROOT / "channel-catalog.m3u"])
            after_ids = [channel.tvg_id for channel in after_catalog]
            if before_ids != after_ids:
                for path in (
                    PROJECT_ROOT / "m3u.m3u",
                    PROJECT_ROOT / "m3u-externa.m3u",
                ):
                    if path in updated:
                        updated[path] = reorder_playlist_lines(updated[path], after_ids)
    _validate_partition(updated)
    for path in PROJECT_ROOT.joinpath("logos").glob("**/*"):
        if path.is_file() and path.stat().st_size == 0:
            raise RuntimeError(f"logo vacio: {path.relative_to(PROJECT_ROOT)}")
    _write_playlists(updated)
    print(f"Cambio editorial validado sin red: {', '.join(plan.changed_files)}")


def apply_stream(
    plan: change_plan.ChangePlan,
    before: dict[str, str],
    after: dict[str, str],
) -> None:
    url_updates = _collect_stream_urls(plan, before, after)
    info_updates = _collect_info_updates(plan, before, after)
    updated = _apply_playlist_updates(url_updates, info_updates)
    catalog_lines = updated[PROJECT_ROOT / "channel-catalog.m3u"]
    catalog_channels = {
        channel.tvg_id: channel
        for channel in update_m3u.parse_channels(catalog_lines)
    }
    allow_geo = bool(os.environ.get("CI", "").lower() == "true")
    for channel_id in plan.channel_ids:
        channel = catalog_channels.get(channel_id)
        if channel is None:
            raise RuntimeError(f"stream dirigido: falta el canal {channel_id}")
        result = update_m3u.check_channel(channel, allow_ci_geo_block=allow_geo)
        print(f"  [{'OK' if result.ok else 'FALLO'}] {channel.name}: {result.detail}")
        if not result.ok:
            raise RuntimeError(f"stream no validado para {channel_id}: {result.detail}")
    _validate_partition(updated)
    _write_playlists(updated)
    print(
        "Streams dirigidos publicados sin renovar otros canales: "
        + ", ".join(plan.channel_ids)
    )


def merge_epg_xml(
    existing: bytes,
    replacement: bytes,
    target_ids: set[str] | frozenset[str],
) -> bytes:
    """Replace only target channels/programmes and preserve the rest."""
    existing_root = ET.fromstring(existing)
    replacement_root = ET.fromstring(replacement)
    if existing_root.tag != "tv" or replacement_root.tag != "tv":
        raise ValueError("ambos documentos EPG deben tener raiz <tv>")
    targets = set(target_ids)
    replacement_channels = {
        element.get("id", ""): element
        for element in replacement_root.findall("channel")
        if element.get("id", "") in targets
    }
    missing = sorted(targets - set(replacement_channels))
    if missing:
        raise ValueError("la EPG dirigida no devolvio canales: " + ", ".join(missing))

    for element in list(existing_root.findall("channel")):
        if element.get("id", "") in targets:
            existing_root.remove(element)
    for element in list(existing_root.findall("programme")):
        if element.get("channel", "") in targets:
            existing_root.remove(element)

    # Keep global generation metadata from the fresh targeted build.
    for key, value in replacement_root.attrib.items():
        if key == "data-next-refresh-at" and existing_root.get(key):
            # A partial build cannot calculate the next global refresh from
            # only the selected channels; preserve the catalog-wide deadline.
            continue
        existing_root.set(key, value)

    insertion_index = next(
        (
            index
            for index, element in enumerate(list(existing_root))
            if element.tag == "programme"
        ),
        len(list(existing_root)),
    )
    for channel_id in sorted(targets):
        existing_root.insert(insertion_index, copy.deepcopy(replacement_channels[channel_id]))
        insertion_index += 1
    for programme in replacement_root.findall("programme"):
        if programme.get("channel", "") in targets:
            existing_root.append(copy.deepcopy(programme))

    ET.indent(existing_root, space="  ")
    return ET.tostring(existing_root, encoding="utf-8", xml_declaration=True) + b"\n"


def _apply_epg_manifest(after: dict[str, str], channel_ids: set[str]) -> None:
    text = after.get("epg-overrides.json")
    if not text:
        return
    entries = _manifest_entries(text, path="epg-overrides.json")
    for channel_id in channel_ids:
        entry = entries.get(channel_id, {})
        source = entry.get("source")
        source_id = entry.get("source_id") or entry.get("sourceId")
        if not source or not source_id:
            continue
        update_m3u.EPG_PROGRAMME_SOURCES[channel_id] = (source, source_id)


def apply_epg(
    plan: change_plan.ChangePlan,
    after: dict[str, str],
) -> None:
    if not EPG_PATH.exists():
        raise RuntimeError("no existe epg.xml para hacer una actualizacion parcial")
    catalog_lines = (PROJECT_ROOT / "channel-catalog.m3u").read_text(
        encoding="utf-8-sig"
    ).splitlines()
    catalog_channels = update_m3u.parse_channels(catalog_lines)
    selected = [channel for channel in catalog_channels if channel.tvg_id in plan.channel_ids]
    if len(selected) != len(plan.channel_ids):
        missing = sorted(set(plan.channel_ids) - {channel.tvg_id for channel in selected})
        raise RuntimeError("EPG dirigida: faltan canales: " + ", ".join(missing))
    _apply_epg_manifest(after, set(plan.channel_ids))

    existing = EPG_PATH.read_bytes()
    temporary = EPG_PATH.with_name(".epg-targeted.xml")
    temporary.write_bytes(existing)
    try:
        update_m3u.refresh_epg(selected, force=True, output_path=temporary)
        replacement = temporary.read_bytes()
    finally:
        temporary.unlink(missing_ok=True)
        temporary.with_suffix(".xml.tmp").unlink(missing_ok=True)
    merged = merge_epg_xml(existing, replacement, set(plan.channel_ids))
    expected_ids = {channel.tvg_id for channel in catalog_channels if channel.tvg_id}
    update_m3u.epg_status_from_xml(
        merged,
        expected_ids,
        now=datetime.now(timezone.utc),
        minimum_future=timedelta(hours=24),
        allow_empty_ids=update_m3u.EPG_ALLOWED_EMPTY_IDS,
    )
    temporary_output = EPG_PATH.with_suffix(".xml.tmp")
    temporary_output.write_bytes(merged)
    temporary_output.replace(EPG_PATH)
    print(
        "EPG dirigida publicada sin reconstruir otros canales: "
        + ", ".join(plan.channel_ids)
    )


def execute(plan: change_plan.ChangePlan, before: dict[str, str], after: dict[str, str]) -> int:
    if plan.kind is change_plan.ChangeKind.NOOP:
        print("Sin artefactos publicos dirigidos; no se ejecuta ningun actualizador.")
        return 0
    if plan.kind is change_plan.ChangeKind.FULL:
        print(
            "Cambio amplio diferido a la proxima ventana completa: " + plan.reason
        )
        return 0
    if plan.kind is change_plan.ChangeKind.PRESENTATION:
        apply_presentation(plan, before, after)
    elif plan.kind is change_plan.ChangeKind.STREAM:
        apply_stream(plan, before, after)
    elif plan.kind is change_plan.ChangeKind.EPG:
        apply_epg(plan, after)
    else:  # pragma: no cover - enum exhaustiveness guard
        raise RuntimeError(f"tipo de cambio desconocido: {plan.kind}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aplica cambios dirigidos sin mantenimiento completo.")
    parser.add_argument("--base", help="SHA base del push de GitHub")
    parser.add_argument(
        "--mode",
        choices=("auto", "presentation", "stream", "epg"),
        default="auto",
    )
    parser.add_argument("--channel-ids", nargs="*", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "auto":
        if not args.base:
            raise SystemExit("--base es obligatorio en modo auto")
        plan, before, after = repository_plan(args.base)
    else:
        paths = [
            "stream-overrides.json" if args.mode == "stream" else "epg-overrides.json"
        ]
        if args.mode == "presentation":
            paths = ["presentation"]
        elif args.mode == "stream":
            paths = []
        ids = tuple(sorted(set(args.channel_ids)))
        kind = change_plan.ChangeKind(args.mode)
        plan = change_plan.ChangePlan(kind, channel_ids=ids, changed_files=tuple(paths))
        before, after = {}, {}
    print(json.dumps(plan.as_dict(), ensure_ascii=False, indent=2))
    return execute(plan, before, after)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (change_plan.ChangePlanError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
