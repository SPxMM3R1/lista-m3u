#!/usr/bin/env python3
import json
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone

# Auditoría 2026-10-15: un tercio de las publicaciones de epg.xml (6,6 MB cada una) solo
# quitaba programas ya terminados y cambiaba la hora de generación. Cada una agrandaba el
# repositorio y hacía que cada TV volviera a descargar y analizar la guía sin ver nada nuevo.
# Esos cambios se dejan para la próxima publicación con contenido real (la app ignora los
# programas terminados). Los archivos de estado se publican igual.
VOLATILE_ROOT_ATTRIBUTES = frozenset({"data-generated-at"})


def _git_bytes(*args: str) -> bytes | None:
    result = subprocess.run(["git", *args], capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def _stop(programme: ET.Element) -> datetime | None:
    value = programme.get("stop", "")
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S %z")
    except ValueError:
        return None


def is_prune_only(old: bytes, new: bytes, now: datetime) -> bool:
    """True si ``new`` es ``old`` sin algunos programas ya terminados (y otra hora de generación)."""
    try:
        old_root, new_root = ET.fromstring(old), ET.fromstring(new)
    except ET.ParseError:
        return False

    def root_attributes(root: ET.Element) -> dict:
        return {k: v for k, v in root.attrib.items() if k not in VOLATILE_ROOT_ATTRIBUTES}

    if root_attributes(old_root) != root_attributes(new_root):
        return False
    old_channels = [ET.tostring(item) for item in old_root.findall("channel")]
    new_channels = [ET.tostring(item) for item in new_root.findall("channel")]
    if old_channels != new_channels:
        return False
    old_programmes = Counter()
    ended: dict[bytes, bool] = {}
    for programme in old_root.findall("programme"):
        key = ET.tostring(programme)
        old_programmes[key] += 1
        stop = _stop(programme)
        ended[key] = stop is not None and stop <= now
    new_programmes = Counter(ET.tostring(item) for item in new_root.findall("programme"))
    if new_programmes - old_programmes:
        return False  # hay programas nuevos o distintos
    removed = old_programmes - new_programmes
    return all(ended.get(key, False) for key in removed)


def index_only_timestamp_changed(old: bytes, new: bytes) -> bool:
    try:
        before, after = json.loads(old), json.loads(new)
    except ValueError:
        return False
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    before.pop("generatedAt", None)
    after.pop("generatedAt", None)
    return before == after


def _keep_file_if_prune_only(name: str, now: datetime) -> bool:
    published = _git_bytes("show", f"HEAD:{name}")
    try:
        with open(name, "rb") as handle:
            current = handle.read()
    except OSError:
        return False
    if published is None or published == current or not is_prune_only(published, current, now):
        return False
    with open(name, "wb") as handle:
        handle.write(published)
    return True


def keep_published_guide_if_prune_only(now: datetime | None = None) -> bool:
    """Si una guía solo perdió programas terminados, deja la versión publicada. Devuelve si lo hizo.

    Desde 2026-10-21 hay dos guías: epg.xml (Lista 1) y epg-2.xml (Lista 2); cada una se
    evalúa por separado. Devuelve si epg.xml se conservó (y entonces también el índice).
    """
    now = now or datetime.now(timezone.utc)
    if _keep_file_if_prune_only("epg-2.xml", now):
        print("EPG 2: solo se quitaban programas terminados; se mantiene la guía publicada.")
    if not _keep_file_if_prune_only("epg.xml", now):
        return False
    published_index = _git_bytes("show", "HEAD:epg/indice.json")
    try:
        with open("epg/indice.json", "rb") as handle:
            current_index = handle.read()
    except OSError:
        current_index = None
    if published_index is not None and current_index is not None \
            and index_only_timestamp_changed(published_index, current_index):
        with open("epg/indice.json", "wb") as handle:
            handle.write(published_index)
    print("EPG: solo se quitaban programas terminados; se mantiene la guía publicada.")
    return True


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=False)


def push_with_rebase() -> int:
    first_push = run("git", "push", "origin", "HEAD:main")
    if first_push.returncode == 0:
        return 0

    # El proceso de canales puede publicar un commit mientras la EPG se
    # construye. La EPG solo toca sus propios archivos, por lo que se puede
    # rebasar de forma segura sobre el main nuevo y reintentar sin mezclar
    # historiales ni perder el commit del otro proceso.
    # Con grupo de concurrencia propio, canales puede publicar en paralelo:
    # se integra y reintenta hasta tres veces.
    result = first_push.returncode
    for _ in range(3):
        fetched = run("git", "fetch", "origin", "main")
        if fetched.returncode != 0:
            return result
        rebased = run("git", "rebase", "origin/main")
        if rebased.returncode != 0:
            run("git", "rebase", "--abort")
            return rebased.returncode
        result = run("git", "push", "origin", "HEAD:main").returncode
        if result == 0:
            return 0
    return result


def main() -> int:
    keep_published_guide_if_prune_only()
    subprocess.run(
        ["git", "add", "-A", "--", "epg.xml", "epg-2.xml", "epg", "epg-run-state.json", "epg-pending.json"],
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Actualizador"], check=True)
    subprocess.run(["git", "config", "user.email", "m3u-bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "commit", "-m", "Actualiza EPG independiente [skip ci]"], check=False)
    return push_with_rebase()


if __name__ == "__main__":
    raise SystemExit(main())
