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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SECONDS = 8
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


def probe(item):
    tvg_id, name, url = item
    result = {"tvg_id": tvg_id, "name": name, "url": url, "ok": False}
    try:
        info = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                               "-analyzeduration", "4000000", "-probesize", "2000000", url]) or "{}")
        video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
        if video:
            result.update(width=video.get("width"), height=video.get("height"),
                          fps=video.get("avg_frame_rate"), video_codec=video.get("codec_name"))
        if audio:
            result.update(audio_codec=audio.get("codec_name"), audio_channels=audio.get("channels"))
        packets = run(["ffprobe", "-v", "error", "-read_intervals", f"%+{SECONDS}", "-show_entries",
                       "packet=size,pts_time", "-of", "csv=p=0", url])
        sizes, times = [], []
        # ffprobe imprime «pts_time,size,» (algunas filas traen pts N/A y se descartan).
        for row in packets.splitlines():
            fields = [field for field in row.split(",") if field not in ("", "N/A")]
            if len(fields) == 2 and fields[1].isdigit():
                try:
                    times.append(float(fields[0]))
                except ValueError:
                    continue
                sizes.append(int(fields[1]))
        if len(times) > 10 and max(times) - min(times) > 1:
            # Ventana de SECONDS segundos: si el canal da más, solo cuentan los paquetes de esa ventana.
            duration = max(times) - min(times)
            result["kbps"] = round(sum(sizes) * 8 / duration / 1000)
            result["ok"] = True
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
