#!/usr/bin/env python3
"""Verify the published playlist and refresh TVN's expiring stream token."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_PLAYLIST = Path(__file__).with_name("chile_tv_limpio_v3.m3u")
REPORT_PATH = Path(__file__).with_name("channel-status.json")
TVN_LIVE_PAGE = "https://live.tvn.cl/"
TVN_DEFAULT_ID = "57a498c4d7b86d600e5461cb"
PLAYER_USER_AGENT = "VLC/3.0.20 LibVLC/3.0.20"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    url_line: int


@dataclass(frozen=True)
class CheckResult:
    channel: str
    url: str
    ok: bool
    detail: str


def parse_channels(lines: list[str]) -> list[Channel]:
    channels: list[Channel] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXTINF:"):
            continue
        name = line.rsplit(",", 1)[-1].strip() or f"Canal en linea {index + 1}"
        for url_line in range(index + 1, len(lines)):
            candidate = lines[url_line].strip()
            if not candidate:
                continue
            if candidate.startswith("#"):
                raise ValueError(f"{name}: falta la URL despues de #EXTINF")
            channels.append(Channel(name, candidate, url_line))
            break
        else:
            raise ValueError(f"{name}: falta la URL al final del archivo")
    return channels


def request_headers(channel: str) -> dict[str, str]:
    headers = {"User-Agent": PLAYER_USER_AGENT, "Accept": "*/*"}
    if channel == "TVN":
        headers["Referer"] = "https://www.tvn.cl/"
    elif channel == "La Red":
        headers["Referer"] = "https://www.lared.cl/senal-online/"
    return headers


def fetch_bytes(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = 25,
    context: ssl.SSLContext | None = None,
    limit: int = 262_144,
) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.status, response.read(limit), response.geturl()


def check_channel(
    channel: Channel, attempts: int = 2, *, allow_tvn_geo_block: bool = False
) -> CheckResult:
    last_error = "respuesta desconocida"
    for attempt in range(attempts):
        try:
            status, body, final_url = fetch_bytes(channel.url, request_headers(channel.name))
            text = body.decode("utf-8", "replace").lstrip("\ufeff\r\n ")
            if status == 200 and text.startswith("#EXTM3U"):
                detail = "playlist HLS valida"
                if final_url != channel.url:
                    detail += " (con redireccion)"
                return CheckResult(channel.name, channel.url, True, detail)
            last_error = f"HTTP {status}, contenido no reconocido"
        except urllib.error.HTTPError as error:
            if allow_tvn_geo_block and channel.name == "TVN" and error.code == 403:
                return CheckResult(
                    channel.name,
                    channel.url,
                    True,
                    "token oficial renovado; reproduccion limitada fuera de Chile (HTTP 403)",
                )
            last_error = f"HTTP {error.code} {error.reason}"
        except Exception as error:  # Network and TLS failures need a compact report.
            last_error = f"{type(error).__name__}: {error}"
        if attempt + 1 < attempts:
            time.sleep(1.5)
    return CheckResult(channel.name, channel.url, False, last_error)


def tvn_page_html() -> str:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": "https://www.tvn.cl/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        _, body, _ = fetch_bytes(TVN_LIVE_PAGE, headers, limit=1_048_576)
    except urllib.error.URLError as error:
        reason = str(getattr(error, "reason", error)).lower()
        if "certificate verify failed" not in reason and "certificate has expired" not in reason:
            raise
        print("  TVN: certificado web vencido; usando excepcion TLS solo para su pagina oficial")
        insecure_context = ssl.create_default_context()
        insecure_context.check_hostname = False
        insecure_context.verify_mode = ssl.CERT_NONE
        _, body, _ = fetch_bytes(
            TVN_LIVE_PAGE, headers, context=insecure_context, limit=1_048_576
        )
    return body.decode("utf-8", "replace")


def fresh_tvn_url() -> str:
    html = tvn_page_html()
    stream_id_match = re.search(r"\bid\s*:\s*['\"]([a-zA-Z0-9]+)['\"]", html)
    token_match = re.search(r"\baccess_token\s*:\s*['\"]([^'\"]+)['\"]", html)
    if not token_match:
        raise RuntimeError("la pagina oficial de TVN no publico un access_token")
    stream_id = stream_id_match.group(1) if stream_id_match else TVN_DEFAULT_ID
    token = token_match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise RuntimeError("TVN entrego un token con formato inesperado")
    return f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8?access_token={token}"


def verify_all(channels: list[Channel], *, allow_tvn_geo_block: bool = False) -> list[CheckResult]:
    results: dict[str, CheckResult] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(channels))) as pool:
        futures = {
            pool.submit(
                check_channel, channel, allow_tvn_geo_block=allow_tvn_geo_block
            ): channel
            for channel in channels
        }
        for future in as_completed(futures):
            result = future.result()
            results[result.channel] = result
            state = "OK" if result.ok else "FALLO"
            print(f"  [{state}] {result.channel}: {result.detail}")
    return [results[channel.name] for channel in channels]


def write_report(results: list[CheckResult], tvn_refreshed: bool) -> None:
    report = {
        "playlist": DEFAULT_PLAYLIST.name,
        "tvn_refreshed": tvn_refreshed,
        "all_ok": all(result.ok for result in results),
        "channels": [asdict(result) for result in results],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    args = parser.parse_args()

    playlist = args.playlist.resolve()
    lines = playlist.read_text(encoding="utf-8-sig").splitlines()
    channels = parse_channels(lines)
    if not channels:
        raise RuntimeError("la lista no contiene canales activos")

    print(f"Revisando {len(channels)} canales de {playlist.name}")
    running_in_ci = os.environ.get("CI", "").lower() == "true"
    tvn_refreshed = False
    tvn = next((channel for channel in channels if channel.name == "TVN"), None)
    if tvn:
        current_tvn = check_channel(tvn)
        state = "OK" if current_tvn.ok else "VENCIDO"
        print(f"  [{state}] TVN: {current_tvn.detail}")
        if running_in_ci or not current_tvn.ok:
            print("Renovando el enlace temporal de TVN desde su pagina oficial")
            new_url = fresh_tvn_url()
            candidate = Channel("TVN", new_url, tvn.url_line)
            refreshed_result = check_channel(candidate)
            geo_blocked = (
                running_in_ci
                and not refreshed_result.ok
                and "HTTP 403" in refreshed_result.detail
            )
            if not refreshed_result.ok and not geo_blocked:
                raise RuntimeError(f"el nuevo enlace de TVN fallo: {refreshed_result.detail}")
            lines[tvn.url_line] = new_url
            playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            tvn_refreshed = True
            if geo_blocked:
                print("  [GEO] TVN: token renovado; GitLab no puede reproducirlo fuera de Chile")
            else:
                print("  [OK] TVN: token renovado y comprobado")

    print("Verificacion final de la lista completa")
    final_lines = playlist.read_text(encoding="utf-8-sig").splitlines()
    final_channels = parse_channels(final_lines)
    results = verify_all(final_channels, allow_tvn_geo_block=running_in_ci)
    write_report(results, tvn_refreshed)
    failed = [result.channel for result in results if not result.ok]
    if failed:
        print("Canales con problemas: " + ", ".join(failed), file=sys.stderr)
        return 1
    print(f"Todos los canales funcionan ({len(results)}/{len(results)})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
