#!/usr/bin/env python3
"""Copy distinct historical repository logos into a public, selectable pool."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_OBJECT_LINE = re.compile(r"^([0-9a-f]{40})\s+(logos/.+)$")
_TREE_LINE = re.compile(r"^\d+\s+blob\s+([0-9a-f]{40})\s+(logos/.+)$")
_SAFE_STEM = re.compile(r"[^A-Za-z0-9._-]+")


def parse_logo_objects(output: str) -> dict[str, str]:
    """Return one repository-relative source path per historical image blob."""
    result: dict[str, str] = {}
    for line in output.splitlines():
        match = _OBJECT_LINE.match(line)
        if not match:
            continue
        blob, path = match.groups()
        if path.startswith("logos/history/"):
            continue
        if Path(path).suffix.casefold() not in ALLOWED_EXTENSIONS:
            continue
        result.setdefault(blob, path)
    return result


def parse_current_logo_blobs(output: str) -> set[str]:
    """Return image blobs in HEAD, excluding the generated history pool."""
    result: set[str] = set()
    for line in output.splitlines():
        match = _TREE_LINE.match(line)
        if not match:
            continue
        blob, path = match.groups()
        if path.startswith("logos/history/"):
            continue
        if Path(path).suffix.casefold() in ALLOWED_EXTENSIONS:
            result.add(blob)
    return result


def archive_name(source_path: str, blob: str) -> Path:
    """Keep the original descriptive name while making every version unique."""
    source = Path(source_path)
    stem = _SAFE_STEM.sub("-", source.stem).strip("-._") or "logo"
    suffix = source.suffix.casefold()
    if suffix not in ALLOWED_EXTENSIONS or not re.fullmatch(r"[0-9a-f]{40}", blob):
        raise ValueError("fuente o blob de logo histórico invalido")
    return Path("logos") / "history" / f"{stem}--{blob[:10]}{suffix}"


def _git(*args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    return result.stdout


def archive_logo_history() -> int:
    """Materialize old logo blobs without changing any current logo asset."""
    objects = parse_logo_objects(str(_git("rev-list", "--objects", "HEAD")))
    current = parse_current_logo_blobs(
        str(_git("ls-tree", "-r", "--full-tree", "HEAD", "--", "logos"))
    )
    historical = {blob: path for blob, path in objects.items() if blob not in current}
    if not historical:
        print("No se encontraron versiones históricas de logos para archivar.")
        return 0

    created = 0
    for blob, source_path in sorted(historical.items()):
        relative_target = archive_name(source_path, blob)
        target = ROOT / relative_target
        content = _git("cat-file", "blob", blob, text=False)
        assert isinstance(content, bytes)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != content:
                raise RuntimeError(f"el logo archivado no coincide: {relative_target}")
            continue
        target.write_bytes(content)
        created += 1

    print(
        f"Logos históricos incorporados al pool: {created} nuevos, "
        f"{len(historical)} versiones únicas."
    )
    return created


if __name__ == "__main__":
    archive_logo_history()
