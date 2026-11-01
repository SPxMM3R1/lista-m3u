"""Mide la calidad de cada canal con respaldos y de sus copias en backups.json (2026-10-31).

Pedido del usuario: el selector de respaldos de la app (VibeM3U 0.6.48, mockup «V2 · Pulso»)
dibuja una barra por señal cuyo alto es su bitrate. Este script mide el principal (su URL en
``m3u.m3u``, si no depende de un resolutor) y cada copia con ``tools/probe_bitrate.probe``
(variante HLS mayor) y guarda en backups.json:

- ``principal_quality`` en cada canal y ``quality`` en cada copia:
  ``{"height", "width", "fps", "kbps", "ok"}`` (``ok`` = abrió y se pudo medir);
- ``quality_measured``: fecha y hora UTC de la medición.

Uso: ``python scripts/measure_backup_quality.py`` (mide y escribe) o
``--save resultados.json`` / ``--apply resultados.json`` para volver a escribir una medición
ya hecha (el workflow lo usa si otro commit cambió backups.json mientras medía).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import probe_bitrate  # noqa: E402

BACKUPS_PATH = ROOT / "backups.json"
PLAYLIST_PATH = ROOT / "m3u.m3u"
ATTR = re.compile(r'(\S+?)="([^"]*)"')


def principal_urls(path: Path) -> dict[str, str]:
    """tvg-id → URL directa de Lista 1 (sin los canales que dependen de un resolutor)."""
    urls: dict[str, str] = {}
    pending = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR.findall(line.split(",", 1)[0]))
            pending = None if "x-resolver" in attrs else attrs.get("tvg-id", "")
        elif line and not line.startswith("#") and pending:
            if line.startswith(("http://", "https://")):
                urls.setdefault(pending, line)
            pending = None
    return urls


def summary(result: dict) -> dict:
    """Lo que lee la app: alto, ancho, fps, kbps y si abrió."""
    fps = 0.0
    text = str(result.get("fps") or "0")
    if text and not text.endswith("/0"):
        try:
            fps = round(float(Fraction(text)), 2)
        except (ValueError, ZeroDivisionError):
            fps = 0.0
    ok = bool(result.get("ok") and result.get("height"))
    return {
        "height": int(result.get("height") or 0),
        "width": int(result.get("width") or 0),
        "fps": fps,
        "kbps": int(result.get("kbps") or 0),
        "ok": ok,
    }


def targets(backups: dict, urls: dict[str, str]) -> list[tuple[str, str, str]]:
    items = []
    for key, entry in backups.get("channels", {}).items():
        if key in urls:
            items.append((key, entry.get("display_name", key), urls[key]))
        for copy in entry.get("backups", []):
            items.append((copy["tvg_id"], copy.get("display_name", ""), copy["url"]))
    return items


def measure(items: list[tuple[str, str, str]]) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=12) as pool:
        rows = list(pool.map(probe_bitrate.probe, items))
    return {row["tvg_id"]: summary(row) for row in rows}


def apply(backups: dict, results: dict[str, dict], measured_at: str) -> int:
    """Escribe las mediciones en backups.json; devuelve cuántas señales quedaron medidas."""
    written = 0
    for key, entry in backups.get("channels", {}).items():
        if key in results:
            entry["principal_quality"] = results[key]
            written += 1
        else:
            entry.pop("principal_quality", None)
        for copy in entry.get("backups", []):
            if copy["tvg_id"] in results:
                copy["quality"] = results[copy["tvg_id"]]
                written += 1
    backups["quality_measured"] = measured_at
    fields = backups.setdefault("fields", {})
    fields["principal_quality / backups[].quality"] = (
        "Medición de la señal (variante HLS mayor): height, width, fps, kbps y ok (abrió y se "
        "midió). La app VibeM3U dibuja con esto las barras del selector de respaldos."
    )
    fields["quality_measured"] = "Fecha y hora UTC de la última medición (scripts/measure_backup_quality.py)."
    return written


def write(backups: dict) -> None:
    text = json.dumps(backups, ensure_ascii=False, indent=2) + "\n"
    BACKUPS_PATH.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", help="guarda también los resultados en este archivo")
    parser.add_argument("--apply", help="no mide: escribe los resultados de este archivo")
    args = parser.parse_args()
    backups = json.loads(BACKUPS_PATH.read_text(encoding="utf-8"))
    if args.apply:
        saved = json.loads(Path(args.apply).read_text(encoding="utf-8"))
        results, measured_at = saved["results"], saved["measured_at"]
    else:
        results = measure(targets(backups, principal_urls(PLAYLIST_PATH)))
        measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if args.save:
            Path(args.save).write_text(
                json.dumps({"measured_at": measured_at, "results": results}, ensure_ascii=False),
                encoding="utf-8",
            )
    written = apply(backups, results, measured_at)
    write(backups)
    ok = sum(1 for value in results.values() if value["ok"])
    print(f"backups.json: {written} señales con medición ({ok} abrieron), {measured_at}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
