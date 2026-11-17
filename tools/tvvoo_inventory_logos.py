"""Logos del inventario TvVoo para el bloque TvVoo de Lista 2 (2026-11-17).

Para cada canal del catálogo vivo (`data/tvvoo-catalogo-vivo-20261117.json`) que tiene un logo
en el inventario oficial (`lists.json` de GitHub, el mismo que usa tvvoo_variants.py), descarga
la imagen, la convierte a PNG local bajo `logos/tvvoo-inventario/` (lado máximo 512 px, ≤ 64 KB)
y escribe el mapa `contracts/tvvoo-logos-lista2-20261117.json`:

    "<país minúsculas>|<nombre minúsculas>": {"logoPath": "logos/..." | null, "category": "..." | null}

Las filas sin logo utilizable quedan con `logoPath: null` y el script de Lista 2 les pone el logo
genérico del país. Es idempotente: una imagen ya descargada no se vuelve a bajar.

Uso (desde la raíz del repo):
    python tools/tvvoo_inventory_logos.py --lists <ruta a lists.json>

Sin `--lists` descarga el inventario oficial a una carpeta temporal nueva. Solo lee JSON e
imágenes; no ejecuta nada descargado. Requiere Pillow, pero es una herramienta local (no una
prueba): el CI no la ejecuta.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "data" / "tvvoo-catalogo-vivo-20261117.json"
MAP_PATH = ROOT / "contracts" / "tvvoo-logos-lista2-20261117.json"
LOGO_DIR = ROOT / "logos" / "tvvoo-inventario"
INVENTORY_URL = "https://raw.githubusercontent.com/qwertyuiop8899/tvvoo/main/src/channels/lists.json"
MAX_SIDE = 512
MAX_BYTES = 64 * 1024
MAX_DOWNLOAD = 5 * 1024 * 1024
TIMEOUT_SECONDS = 20


def _key(country: str, name: str) -> str:
    return f"{country.strip().lower()}|{name.strip().lower()}"


def _download(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "lista-m3u-logos/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read(MAX_DOWNLOAD + 1)
    except Exception:
        return None
    return data if 0 < len(data) <= MAX_DOWNLOAD else None


def _to_png(data: bytes) -> bytes | None:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:
        return None
    image = image.convert("RGBA")
    if max(image.size) > MAX_SIDE:
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    if len(out.getvalue()) > MAX_BYTES:
        quantized = image.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
        out = io.BytesIO()
        quantized.save(out, format="PNG", optimize=True)
    return out.getvalue() if len(out.getvalue()) <= MAX_BYTES else None


def _load_inventory(path: str | None) -> list[dict]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    workdir = Path(tempfile.mkdtemp(prefix="tvvoo-inventario-"))
    target = workdir / "lists.json"
    target.write_bytes(_download(INVENTORY_URL) or b"")
    return json.loads(target.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lists", help="ruta local a lists.json del inventario TvVoo")
    args = parser.parse_args()

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))["channels"]
    wanted = {_key(row["country"], row["name"]) for row in snapshot}
    inventory = _load_inventory(args.lists)

    rows: dict[str, dict] = {}
    urls: dict[str, str] = {}
    for item in inventory:
        country = str(item.get("country") or "")
        name = str(item.get("name") or "")
        if not country or not name:
            continue
        key = _key(country, name)
        if key not in wanted or key in rows:
            continue
        category = str(item.get("category") or "").strip() or None
        logo = str(item.get("logo") or "").strip()
        rows[key] = {"logoPath": None, "category": category}
        if logo.startswith("https://"):
            rows[key]["_url"] = logo
            urls.setdefault(logo, key)

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    url_paths: dict[str, str | None] = {}
    todo = []
    for url in urls:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        target = LOGO_DIR / f"{digest}.png"
        rel = f"logos/tvvoo-inventario/{digest}.png"
        if target.is_file() and target.stat().st_size <= MAX_BYTES:
            url_paths[url] = rel
        else:
            todo.append((url, target, rel))

    def fetch(item):
        url, target, rel = item
        data = _download(url)
        if data is None:
            return url, None
        png = _to_png(data)
        if png is None:
            return url, None
        target.write_bytes(png)
        return url, rel

    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, rel in pool.map(fetch, todo):
            url_paths[url] = rel

    for row in rows.values():
        url = row.pop("_url", None)
        if url:
            row["logoPath"] = url_paths.get(url)

    document = {
        "schema": 1,
        "source": "lists.json del inventario oficial TvVoo (GitHub), solo filas del catálogo vivo 2026-11-17",
        "rows": dict(sorted(rows.items())),
    }
    MAP_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with_logo = sum(1 for row in rows.values() if row["logoPath"])
    print(json.dumps({
        "snapshotRows": len(snapshot),
        "rowsMatchedInInventory": len(rows),
        "distinctLogoUrls": len(urls),
        "logosStoredForUrls": sum(1 for path in url_paths.values() if path),
        "rowsWithLocalLogo": with_logo,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
