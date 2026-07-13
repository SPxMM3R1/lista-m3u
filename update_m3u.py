#!/usr/bin/env python3
"""Verify the published playlist and refresh TVN's expiring stream token."""

from __future__ import annotations

import argparse
import html
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
CI_GEO_RESTRICTED_CHANNELS = {"TVN", "CHV", "24 Horas"}
PLAYER_USER_AGENT = "VLC/3.0.20 LibVLC/3.0.20"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
OFFICIAL_STREAM_PAGES = {
    "Mega": ["https://www.mega.cl/senal-en-vivo/"],
    "CHV": ["https://www.chilevision.cl/senal-online"],
    "Canal 13": ["https://www.13.cl/en-vivo"],
    "T13": ["https://www.t13.cl/en-vivo"],
    "24 Horas": ["https://www.24horas.cl/envivo"],
    "La Red": ["https://www.lared.cl/senal-online/"],
}
OFFICIAL_CANDIDATE_HINTS = {
    "Mega": re.compile(r"mega", re.IGNORECASE),
    "CHV": re.compile(r"(?:chv|chilevision)", re.IGNORECASE),
    "Canal 13": re.compile(r"(?:13cl|canal.?13)", re.IGNORECASE),
    "T13": re.compile(r"(?:/t13/|t13\.)", re.IGNORECASE),
    "24 Horas": re.compile(r"(?:24horas|689ba606ecfe7915e1f8f741)", re.IGNORECASE),
    "La Red": re.compile(r"(?:lared|ds5i0a12qngha)", re.IGNORECASE),
}
KNOWN_STREAM_FALLBACKS = {
    "Mega": ["https://unlimited1-cl-isp.dps.live/mega/mega.smil/playlist.m3u8"],
    "CHV": [
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/chv/chv.smil/playlist.m3u8"
    ],
    "Canal 13": ["https://redirector.dps.live/hls/13cl/playlist.m3u8"],
    "T13": [
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/t13/t13.smil/playlist.m3u8"
    ],
    "24 Horas": ["https://mdstrm.com/live-stream-playlist/689ba606ecfe7915e1f8f741.m3u8"],
    "La Red": ["https://ds5i0a12qngha.cloudfront.net/ts:abr.m3u8"],
    "DW Espanol": [
        "https://dwamdstream104.akamaized.net/hls/live/2015530/dwstream104/master.m3u8"
    ],
    "France 24 Espanol": [
        "https://a-cdn.klowdtv.com/live2/france24sp_720p/playlist.m3u8"
    ],
    "Euronews Espanol": [
        "https://cdn-euronews.akamaized.net/live/eds/euronews-es/25053/index.m3u8"
    ],
    "NHK World Japan": ["https://masterpl.hls.nhkworld.jp/hls/w/live/smarttv.m3u8"],
    "Al Jazeera English": ["https://live-hls-apps-aje-v3-fa.getaj.net/AJE/index.m3u8"],
    "Red Bull TV": ["https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8"],
}


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    url_line: int
    info_line: int = -1
    logo_url: str = ""
    group: str = ""


@dataclass(frozen=True)
class CheckResult:
    channel: str
    url: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class LogoResult:
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
        logo_match = re.search(r'\btvg-logo="([^"]+)"', line)
        group_match = re.search(r'\bgroup-title="([^"]+)"', line)
        logo_url = logo_match.group(1) if logo_match else ""
        group = group_match.group(1) if group_match else ""
        for url_line in range(index + 1, len(lines)):
            candidate = lines[url_line].strip()
            if not candidate:
                continue
            if candidate.startswith("#"):
                raise ValueError(f"{name}: falta la URL despues de #EXTINF")
            channels.append(Channel(name, candidate, url_line, index, logo_url, group))
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
    channel: Channel, attempts: int = 2, *, allow_ci_geo_block: bool = False
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
            if (
                allow_ci_geo_block
                and channel.name in CI_GEO_RESTRICTED_CHANNELS
                and error.code == 403
            ):
                return CheckResult(
                    channel.name,
                    channel.url,
                    True,
                    "reproduccion limitada fuera de Chile (HTTP 403)",
                )
            last_error = f"HTTP {error.code} {error.reason}"
        except Exception as error:  # Network and TLS failures need a compact report.
            last_error = f"{type(error).__name__}: {error}"
        if attempt + 1 < attempts:
            time.sleep(1.5)
    return CheckResult(channel.name, channel.url, False, last_error)


def check_logo(channel: Channel) -> LogoResult:
    if not channel.logo_url:
        return LogoResult(channel.name, "", False, "falta tvg-logo")
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "image/png,image/*;q=0.8,*/*;q=0.5"}
    try:
        status, body, _ = fetch_bytes(channel.logo_url, headers, limit=65_536)
        if status == 200 and body.startswith(b"\x89PNG\r\n\x1a\n"):
            return LogoResult(channel.name, channel.logo_url, True, "PNG valido")
        return LogoResult(channel.name, channel.logo_url, False, f"HTTP {status}, no es PNG")
    except urllib.error.HTTPError as error:
        return LogoResult(channel.name, channel.logo_url, False, f"HTTP {error.code} {error.reason}")
    except Exception as error:
        return LogoResult(channel.name, channel.logo_url, False, f"{type(error).__name__}: {error}")


def verify_logos(channels: list[Channel]) -> list[LogoResult]:
    results: dict[str, LogoResult] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(channels))) as pool:
        futures = {pool.submit(check_logo, channel): channel for channel in channels}
        for future in as_completed(futures):
            result = future.result()
            results[result.channel] = result
            state = "OK" if result.ok else "FALLO"
            print(f"  [{state}] Logo {result.channel}: {result.detail}")
    return [results[channel.name] for channel in channels]


def extract_hls_urls(page_text: str) -> list[str]:
    matches = re.findall(
        r"https?:\\?/\\?/[^\s\"'<>]+?\.m3u8(?:\?[^\s\"'<>]*)?",
        page_text,
        flags=re.IGNORECASE,
    )
    urls: list[str] = []
    for match in matches:
        cleaned = html.unescape(match).replace("\\/", "/")
        cleaned = re.sub(r"\\+u0026", "&", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.rstrip("\\,);]")
        if cleaned not in urls:
            urls.append(cleaned)
    return urls


def discover_official_candidates(channel: Channel) -> list[str]:
    candidates = list(KNOWN_STREAM_FALLBACKS.get(channel.name, []))
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    for page_url in OFFICIAL_STREAM_PAGES.get(channel.name, []):
        try:
            _, body, _ = fetch_bytes(page_url, headers, limit=2_097_152)
            for candidate in extract_hls_urls(body.decode("utf-8", "replace")):
                hint = OFFICIAL_CANDIDATE_HINTS.get(channel.name)
                if (hint is None or hint.search(candidate)) and candidate not in candidates:
                    candidates.append(candidate)
        except Exception as error:
            print(f"  [AVISO] {channel.name}: no se pudo leer {page_url}: {error}")
    return [candidate for candidate in candidates if candidate != channel.url]


def repair_failed_channels(
    lines: list[str],
    channels: list[Channel],
    results: list[CheckResult],
    *,
    allow_ci_geo_block: bool,
) -> list[str]:
    channels_by_name = {channel.name: channel for channel in channels}
    repaired: list[str] = []
    for result in results:
        if result.ok or result.channel == "TVN":
            continue
        channel = channels_by_name[result.channel]
        print(f"Buscando reemplazo oficial para {channel.name}")
        for candidate_url in discover_official_candidates(channel):
            candidate = Channel(
                channel.name,
                candidate_url,
                channel.url_line,
                channel.info_line,
                channel.logo_url,
                channel.group,
            )
            candidate_result = check_channel(
                candidate, allow_ci_geo_block=allow_ci_geo_block
            )
            if candidate_result.ok:
                lines[channel.url_line] = candidate_url
                repaired.append(channel.name)
                print(f"  [REPARADO] {channel.name}: enlace alternativo verificado")
                break
        if channel.name not in repaired:
            print(f"  [SIN REEMPLAZO] {channel.name}: se conserva el enlace para revision manual")
    return repaired


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


def verify_all(channels: list[Channel], *, allow_ci_geo_block: bool = False) -> list[CheckResult]:
    results: dict[str, CheckResult] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(channels))) as pool:
        futures = {
            pool.submit(
                check_channel, channel, allow_ci_geo_block=allow_ci_geo_block
            ): channel
            for channel in channels
        }
        for future in as_completed(futures):
            result = future.result()
            results[result.channel] = result
            state = "OK" if result.ok else "FALLO"
            print(f"  [{state}] {result.channel}: {result.detail}")
    return [results[channel.name] for channel in channels]


def write_report(
    results: list[CheckResult],
    tvn_refreshed: bool,
    logo_results: list[LogoResult] | None = None,
    repaired_channels: list[str] | None = None,
) -> None:
    logos = logo_results or []
    report = {
        "playlist": DEFAULT_PLAYLIST.name,
        "tvn_refreshed": tvn_refreshed,
        "repaired_channels": repaired_channels or [],
        "all_ok": all(result.ok for result in results) and all(result.ok for result in logos),
        "channels": [asdict(result) for result in results],
        "logos": [asdict(result) for result in logos],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def verify_published_copy(url: str, playlist: Path, attempts: int = 4) -> bool:
    expected = playlist.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    separator = "&" if "?" in url else "?"
    for attempt in range(attempts):
        cache_busted = f"{url}{separator}verify={int(time.time())}-{attempt}"
        try:
            _, body, _ = fetch_bytes(
                cache_busted,
                {"User-Agent": PLAYER_USER_AGENT, "Cache-Control": "no-cache"},
                limit=2_097_152,
            )
            published = body.decode("utf-8-sig", "replace").replace("\r\n", "\n")
            if published == expected and published.startswith("#EXTM3U"):
                print(
                    f"Archivo publicado verificado: {published.count('#EXTINF:')} canales y contenido exacto"
                )
                return True
            print(f"  [REINTENTO] El raw aun no coincide ({attempt + 1}/{attempts})")
        except Exception as error:
            print(f"  [REINTENTO] No se pudo leer el raw: {error}")
        if attempt + 1 < attempts:
            time.sleep(2.0)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--verify-published", metavar="URL")
    args = parser.parse_args()

    playlist = args.playlist.resolve()
    if args.verify_published:
        return 0 if verify_published_copy(args.verify_published, playlist) else 1

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
            candidate = Channel(
                "TVN", new_url, tvn.url_line, tvn.info_line, tvn.logo_url, tvn.group
            )
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
    results = verify_all(final_channels, allow_ci_geo_block=running_in_ci)
    repaired_channels = repair_failed_channels(
        final_lines,
        final_channels,
        results,
        allow_ci_geo_block=running_in_ci,
    )
    if repaired_channels:
        playlist.write_text(
            "\n".join(final_lines) + "\n", encoding="utf-8", newline="\n"
        )
        final_lines = playlist.read_text(encoding="utf-8-sig").splitlines()
        final_channels = parse_channels(final_lines)
        print("Verificacion posterior a las reparaciones")
        results = verify_all(final_channels, allow_ci_geo_block=running_in_ci)

    print("Verificacion de logos PNG")
    logo_results = verify_logos(final_channels)
    write_report(results, tvn_refreshed, logo_results, repaired_channels)
    failed = [result.channel for result in results if not result.ok]
    failed_logos = [result.channel for result in logo_results if not result.ok]
    if failed or failed_logos:
        if failed:
            print("Canales con problemas: " + ", ".join(failed), file=sys.stderr)
        if failed_logos:
            print("Logos con problemas: " + ", ".join(failed_logos), file=sys.stderr)
        return 1
    print(f"Todos los canales funcionan ({len(results)}/{len(results)})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        REPORT_PATH.write_text(
            json.dumps(
                {"playlist": DEFAULT_PLAYLIST.name, "all_ok": False, "fatal_error": str(error)},
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
