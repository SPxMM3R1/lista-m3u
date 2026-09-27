"""Asigna logos a las filas de proveedor (Highfly/TvVoo) del catálogo editorial.

Orden, igual que ``suggestLogo`` en ``site/editor-core.mjs``:

1. logo local del catálogo para la misma identidad (catalogKey Highfly o alias TvVoo);
2. logo vigente de ``logos/`` con el mismo nombre de canal;
3. logo histórico de ``logos/history/`` con el mismo nombre;
4. solo TvVoo: el logo que publica TvVoo para ese canal, si viene del repositorio público
   ``tv-logo/tv-logos``. Se copia a ``logos/tvvoo/``; los placeholders generados se descartan.

Sin ``--apply`` solo informa. Nunca reemplaza un logo ya elegido (``logoOverride``/``logoPath``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_site_data  # noqa: E402

LAYOUT_PATH = ROOT / "data" / "channel-editor-layout.json"
CATALOG_PATH = ROOT / "channel-catalog.m3u"
LOGO_ROOT = ROOT / "logos"
TVVOO_LOGO_DIR = LOGO_ROOT / "tvvoo"
TVVOO_BASE = "https://tvvoo.hayd.uk"
TVVOO_LOGO_PREFIX = "/tv-logo/tv-logos/"
MAX_LOGO_BYTES = 1024 * 1024
LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
NOISE_WORDS = {
    "hd", "fhd", "uhd", "sd", "4k", "8k", "hevc", "backup", "logopedia", "transparent",
    "mosca", "color", "dark", "light", "white", "black", "tvvoo",
}
USER_AGENT = "lista-m3u-logo-assigner/1.0"


def logo_name_key(value: str) -> str:
    """Misma clave que ``logoNameKey`` del editor."""
    text = str(value or "").strip()
    file = text.split("/")[-1]
    if file != text or re.search(r"\.(png|svg|jpe?g|webp)$", text, re.I):
        text = re.sub(r"\.(png|svg|jpe?g|webp)$", "", file, flags=re.I)
        text = re.sub(r"--[0-9a-f]{6,}$", "", text, flags=re.I)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    words = [word for word in re.split(r"[^a-z0-9]+", text) if word and word not in NOISE_WORDS]
    return "".join(words)


def suggest_logo(row: dict, catalog_logos: dict, logos: list[str]) -> str:
    """Misma prioridad que ``suggestLogo`` del editor."""
    by_id = catalog_logos.get("byId", {})
    by_alias = catalog_logos.get("byAlias", {})
    if row.get("kind") == "m3u":
        return by_id.get(row.get("tvgId", ""), "")
    if row.get("provider") == "highfly" and by_id.get(row.get("catalogKey", "")):
        return by_id[row["catalogKey"]]
    if row.get("provider") == "tvvoo":
        alias = str(row.get("catalogKey", "")).split("|", 1)[-1]
        for candidate in [alias, *(row.get("aliases") or []), *(row.get("resolverAliases") or [])]:
            if candidate and (by_alias.get(candidate) or by_alias.get(unquote(candidate))):
                return by_alias.get(candidate) or by_alias[unquote(candidate)]
    key = logo_name_key(row.get("name", ""))
    if not key:
        return ""
    matches = [path for path in logos if logo_name_key(path) == key]
    matches.sort(key=lambda path: (path.startswith("logos/history/"), len(path), path))
    return matches[0] if matches else ""


def local_logos() -> list[str]:
    return sorted(
        f"logos/{path.relative_to(LOGO_ROOT).as_posix()}"
        for path in LOGO_ROOT.rglob("*")
        if path.is_file() and path.suffix.casefold() in LOGO_EXTENSIONS
    )


def fetch(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - HTTPS fijo
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"respuesta demasiado grande: {url}")
    return data


def image_extension(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def tvvoo_logo_url(row: dict, catalogs: dict[str, list[dict]]) -> str:
    """URL del logo real que publica TvVoo para la fila, o vacío si solo hay placeholder."""
    alias = unquote(str(row.get("catalogKey", "")).split("|", 1)[-1])
    match = re.search(r"\|group:([a-z]{2})$", alias)
    if not match:
        return ""
    country = match.group(1)
    if country not in catalogs:
        try:
            payload = json.loads(fetch(f"{TVVOO_BASE}/catalog/tv/vavoo_tv_{country}.json", 8 * 1024 * 1024))
            catalogs[country] = payload.get("metas", []) if isinstance(payload, dict) else []
        except Exception as error:  # noqa: BLE001 - un país caído no detiene el resto
            print(f"AVISO: catálogo TvVoo {country} no disponible: {error}", file=sys.stderr)
            catalogs[country] = []
    for meta in catalogs[country]:
        meta_id = unquote(str(meta.get("id", "")))
        if not meta_id.startswith("vavoo_"):
            continue
        canonical = meta_id if "|group:" in meta_id.lower() else f"{meta_id}|group:{country}"
        if canonical != alias:
            continue
        logo = str(meta.get("logo") or "")
        parsed = urlsplit(logo)
        if (
            parsed.scheme == "https"
            and parsed.hostname == "raw.githubusercontent.com"
            and parsed.path.startswith(TVVOO_LOGO_PREFIX)
        ):
            return logo
        return ""
    return ""


def catalog_remote_logo(row: dict, catalog_logos: dict) -> str:
    """Logo externo que Lista M3U ya asociaba al mismo alias TvVoo (solo repo tv-logo)."""
    alias = unquote(str(row.get("catalogKey", "")).split("|", 1)[-1])
    url = catalog_logos.get("remoteByAlias", {}).get(alias, "")
    parsed = urlsplit(url)
    if parsed.hostname == "raw.githubusercontent.com" and parsed.path.startswith(TVVOO_LOGO_PREFIX):
        return url
    return ""


def mirror_tvvoo_logo(url: str, apply: bool) -> str:
    name = Path(urlsplit(url).path).name
    stem = re.sub(r"[^a-z0-9-]+", "-", Path(name).stem.lower()).strip("-") or "logo"
    if not apply:
        return f"logos/tvvoo/{stem}.png"
    data = fetch(url, MAX_LOGO_BYTES)
    extension = image_extension(data)
    if extension is None:
        raise ValueError(f"no es una imagen PNG/JPEG/WebP: {url}")
    TVVOO_LOGO_DIR.mkdir(parents=True, exist_ok=True)
    target = TVVOO_LOGO_DIR / f"{stem}{extension}"
    target.write_bytes(data)
    return f"logos/tvvoo/{target.name}"


def assign(apply: bool) -> int:
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    catalog_logos = build_site_data.parse_catalog_logos(CATALOG_PATH.read_text(encoding="utf-8-sig"))
    logos = local_logos()
    tvvoo_catalogs: dict[str, list[dict]] = {}
    changed = 0
    pending: list[str] = []
    for row in layout.get("channels", []):
        if row.get("kind") != "provider" or row.get("logoOverride") or row.get("logoPath"):
            continue
        path = suggest_logo(row, catalog_logos, logos)
        origin = "catálogo/historial"
        if not path and row.get("provider") == "tvvoo":
            url = tvvoo_logo_url(row, tvvoo_catalogs) or catalog_remote_logo(row, catalog_logos)
            if url:
                try:
                    path = mirror_tvvoo_logo(url, apply)
                    origin = "TvVoo"
                except Exception as error:  # noqa: BLE001
                    print(f"AVISO: {row.get('name')}: {error}", file=sys.stderr)
        label = f"{row.get('number', '?'):>4} {row.get('provider')} {row.get('name')}"
        if not path:
            pending.append(label)
            continue
        print(f"{label} → {path} ({origin})")
        row["logoPath"] = path
        changed += 1
    if pending:
        print("Sin logo disponible:")
        for label in pending:
            print("  " + label)
    if apply and changed:
        LAYOUT_PATH.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{changed} logos {'asignados' if apply else 'por asignar (usa --apply)'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="descarga logos y escribe el layout")
    return assign(parser.parse_args().apply)


if __name__ == "__main__":
    raise SystemExit(main())
