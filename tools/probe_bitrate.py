"""Mide el bitrate real de los canales directos de Lista 2 (m3u-externa.m3u).

Corre en GitHub Actions (.github/workflows/bitrate-lista2.yml), un fragmento por job.
Por canal: resolución, FPS y bitrate de video+audio medido con los paquetes de los primeros
SECONDS segundos (bytes / duración). Canales con x-resolver se omiten (dependen del resolutor).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

SECONDS = 8
# Cuadros decodificados para medir los fps reales (decodificar es más caro que leer paquetes).
FRAME_SECONDS = 3
TIMEOUT = 25
ATTR = re.compile(r'(\S+?)="([^"]*)"')


def entries(path: Path):
    """(tvg_id, nombre, url) de cada canal directo; sin resolutor."""
    pending = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR.findall(line.split(",", 1)[0]))
            pending = (attrs.get("tvg-id", ""), line.rsplit(",", 1)[-1].strip(), "x-resolver" in attrs)
        elif line and not line.startswith("#") and pending:
            tvg_id, name, resolver = pending
            if not resolver:
                yield tvg_id, name, line
            pending = None


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=TIMEOUT).stdout


STREAM_INF = re.compile(r"#EXT-X-STREAM-INF:([^\n]*)\n\s*([^#\s][^\n]*)")


def best_variant(url: str) -> tuple[str, int]:
    """Variante mayor de una lista maestra HLS (2026-10-31): ffprobe sobre la maestra toma
    la primera variante como video y suma al bitrate los paquetes de todas. Devuelve la URL
    de la variante con más resolución (y luego más BANDWIDTH) y cuántas variantes hay."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            text = response.read(300_000).decode("utf-8", "replace")
            base = response.geturl()
    except (OSError, ValueError):
        return url, 0
    best, count = None, 0
    for attributes, target in STREAM_INF.findall(text.replace("\r", "")):
        count += 1
        resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", attributes)
        bandwidth = re.search(r"(?<![-A-Z])BANDWIDTH=(\d+)", attributes)
        key = (int(resolution.group(2)) if resolution else 0, int(bandwidth.group(1)) if bandwidth else 0)
        if best is None or key > best[0]:
            best = (key, urljoin(base, target.strip()))
    return (best[1], count) if best and count > 1 else (url, count)


def probe(item):
    tvg_id, name, url = item
    result = {"tvg_id": tvg_id, "name": name, "url": url, "ok": False}
    try:
        url, result["variantes"] = best_variant(url)
        info = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                               "-analyzeduration", "4000000", "-probesize", "2000000", url]) or "{}")
        video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
        if video:
            result.update(width=video.get("width"), height=video.get("height"),
                          fps=video.get("avg_frame_rate"), video_codec=video.get("codec_name"))
        if audio:
            result.update(audio_codec=audio.get("codec_name"), audio_channels=audio.get("channels"))
        packets = json.loads(run(["ffprobe", "-v", "error", "-read_intervals", f"%+{SECONDS}",
                                  "-show_entries", "packet=size,pts_time",
                                  "-of", "json", url]) or "{}").get("packets", [])
        sizes, times = [], []
        # Algunas filas traen pts N/A: se descartan.
        for packet in packets:
            try:
                moment = float(packet.get("pts_time"))
                size = int(packet.get("size"))
            except (TypeError, ValueError):
                continue
            times.append(moment)
            sizes.append(size)
        if len(times) > 10 and max(times) - min(times) > 1:
            # Ventana de SECONDS segundos: si el canal da más, solo cuentan los paquetes de esa ventana.
            duration = max(times) - min(times)
            result["kbps"] = round(sum(sizes) * 8 / duration / 1000)
            result["ok"] = True
        frames = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-read_intervals",
                                 f"%+{FRAME_SECONDS}", "-show_entries", "frame=pts_time", "-of", "json",
                                 url]) or "{}").get("frames", [])
        frame_times = []
        for frame in frames:
            try:
                frame_times.append(float(frame.get("pts_time")))
            except (TypeError, ValueError):
                continue
        if len(frame_times) > 10 and max(frame_times) - min(frame_times) > 1:
            # Cuadros reales por segundo (2026-11-01): en 1080i ffprobe declara 59,94 (campos)
            # y cada campo llega como paquete aparte, pero se decodifican 29,97 cuadros, que es
            # lo que muestra el OSD de la app.
            span = max(frame_times) - min(frame_times)
            result["fps_measured"] = round((len(frame_times) - 1) / span, 2)
        result["mide_s"] = round(duration, 1) if result["ok"] else None
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as error:
        result["error"] = type(error).__name__
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", default="m3u-externa.m3u")
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--shards", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    items = [item for index, item in enumerate(entries(Path(args.playlist)))
             if index % args.shards == args.shard]
    with ThreadPoolExecutor(max_workers=12) as pool:
        rows = list(pool.map(probe, items))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for row in rows if row["ok"])
    print(f"fragmento {args.shard}: {ok}/{len(rows)} medidos")


if __name__ == "__main__":
    main()
