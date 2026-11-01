"""Prueba si abren los candidatos iptv-org de Lista 2 (m3u-externa.m3u).

Corre en GitHub Actions (.github/workflows/abre-lista2.yml), un fragmento por job, o en el PC
con --ids (solo esos tvg-id). «Abre» = ffprobe decodifica al menos un cuadro de video en los
primeros segundos, con las cabeceras http-referrer / http-user-agent de la fila. Solo mide:
no cambia el catálogo.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PREFIX = "IPTVOrg."
TIMEOUT = 30
ATTR = re.compile(r'(\S+?)="([^"]*)"')


def entries(path: Path, prefix: str = PREFIX):
    """(tvg_id, nombre, url, atributos) de cada fila cuyo tvg-id empieza con prefix."""
    pending = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR.findall(line.split(",", 1)[0]))
            pending = (attrs.get("tvg-id", ""), line.rsplit(",", 1)[-1].strip(), attrs)
        elif line and not line.startswith("#") and pending:
            tvg_id, name, attrs = pending
            if tvg_id.startswith(prefix):
                yield tvg_id, name, line, attrs
            pending = None


def ffprobe_args(url: str, attrs: dict, stream: str) -> list[str]:
    args = ["ffprobe", "-v", "error", "-rw_timeout", "15000000"]
    if attrs.get("http-user-agent"):
        args += ["-user_agent", attrs["http-user-agent"]]
    if attrs.get("http-referrer"):
        args += ["-headers", f"Referer: {attrs['http-referrer']}\r\n"]
    return args + ["-select_streams", stream, "-read_intervals", "%+3",
                   "-show_entries", "frame=pts_time", "-of", "csv=p=0", url]


def frames(url: str, attrs: dict, stream: str) -> int:
    try:
        output = subprocess.run(ffprobe_args(url, attrs, stream), capture_output=True,
                                text=True, timeout=TIMEOUT).stdout
    except (subprocess.TimeoutExpired, OSError):
        return 0
    return sum(1 for line in output.splitlines() if line.strip())


def probe(item) -> dict:
    tvg_id, name, url, attrs = item
    video = frames(url, attrs, "v:0")
    result = {"tvg_id": tvg_id, "name": name, "url": url, "ok": video > 0, "video_frames": video}
    if not video:
        # Sin video puede ser una radio: se anota aparte, no cuenta como «abre».
        result["audio_only"] = frames(url, attrs, "a:0") > 0
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", default="m3u-externa.m3u")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--ids", help="JSON con una lista de tvg-id: solo esas filas")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    items = list(entries(Path(args.playlist)))
    if args.ids:
        wanted = set(json.loads(Path(args.ids).read_text(encoding="utf-8")))
        items = [item for item in items if item[0] in wanted]
    items = [item for index, item in enumerate(items) if index % args.shards == args.shard]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(probe, items))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"fragmento {args.shard}: abren {sum(row['ok'] for row in rows)} de {len(rows)}")


if __name__ == "__main__":
    main()
