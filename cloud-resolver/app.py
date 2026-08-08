#!/usr/bin/env python3
"""Chile-based token resolver for the public VibeM3U playlist."""

from __future__ import annotations

import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlencode


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
TVN_LIVE_PAGE = "https://live.tvn.cl/"
TVN_DEFAULT_ID = "57a498c4d7b86d600e5461cb"
MEGANOTICIAS_LIVE_PAGE = "https://www.meganoticias.cl/senal-en-vivo/meganoticias/"
MEGANOTICIAS_DEFAULT_ID = "561430ae330428c223687e1e"
MEGAMEDIA_API_URL = "https://api.mega.cl/api/v1/mdstrm"
STREAM_CACHE_TTL = 45.0

_cache: dict[str, tuple[float, str]] = {}
_cache_lock = threading.RLock()


def fetch_bytes(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = 25,
    context: ssl.SSLContext | None = None,
    limit: int = 2_097_152,
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.status, response.read(limit)


def page_html(url: str, *, referer: str) -> str:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        _, body = fetch_bytes(url, headers)
    except urllib.error.URLError as error:
        reason = str(getattr(error, "reason", error)).lower()
        if "certificate verify failed" not in reason and "certificate has expired" not in reason:
            raise
        insecure_context = ssl.create_default_context()
        insecure_context.check_hostname = False
        insecure_context.verify_mode = ssl.CERT_NONE
        _, body = fetch_bytes(url, headers, context=insecure_context)
    return body.decode("utf-8", "replace")


def fresh_tvn_url() -> str:
    html = page_html(TVN_LIVE_PAGE, referer="https://www.tvn.cl/")
    stream_id_match = re.search(r"\bid\s*:\s*['\"]([a-zA-Z0-9]+)['\"]", html)
    token_match = re.search(r"\baccess_token\s*:\s*['\"]([^'\"]+)['\"]", html)
    if not token_match:
        raise RuntimeError("TVN no publico access_token")
    stream_id = stream_id_match.group(1) if stream_id_match else TVN_DEFAULT_ID
    token = token_match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise RuntimeError("token de TVN con formato inesperado")
    return (
        f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8?access_token="
        f"{quote(token, safe='')}"
    )


def fresh_meganoticias_url() -> str:
    html = page_html(MEGANOTICIAS_LIVE_PAGE, referer=MEGANOTICIAS_LIVE_PAGE)
    config_match = re.search(
        r"var\s+VideoSenalEnVivo\s*=\s*\{\s*id:\s*'([^']+)'"
        r".*?serverKey\s*:\s*'([^']+)'",
        html,
        flags=re.DOTALL,
    )
    if not config_match:
        raise RuntimeError("Meganoticias no publico la configuracion del reproductor")
    stream_id, server_key = config_match.groups()
    stream_id = stream_id or MEGANOTICIAS_DEFAULT_ID
    query = urlencode(
        {
            "id": stream_id,
            "ua": BROWSER_USER_AGENT,
            "type": "live",
            "process": "access_token",
            "key": server_key,
        }
    )
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": MEGANOTICIAS_LIVE_PAGE,
        "Origin": "https://www.meganoticias.cl",
        "Accept": "application/json",
    }
    status, body = fetch_bytes(f"{MEGAMEDIA_API_URL}?{query}", headers, limit=262_144)
    if status != 200:
        raise RuntimeError(f"API de Meganoticias respondio HTTP {status}")
    response = json.loads(body.decode("utf-8", "replace"))
    token = response.get("access_token") if isinstance(response, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError("API de Meganoticias no emitio access_token")
    if not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise RuntimeError("token de Meganoticias con formato inesperado")
    return (
        f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8?access_token="
        f"{quote(token, safe='')}"
    )


def cached_stream_url(label: str, factory) -> str:
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(label)
        if cached and now - cached[0] < STREAM_CACHE_TTL:
            return cached[1]
        stream_url = factory()
        _cache[label] = (time.monotonic(), stream_url)
        return stream_url


class ResolverHandler(BaseHTTPRequestHandler):
    server_version = "VibeM3UChileResolver/1.0"

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_text(200, "ok\n")
            return
        routes = {
            "/tvn.m3u8": ("TVN", fresh_tvn_url),
            "/meganoticias.m3u8": ("Meganoticias", fresh_meganoticias_url),
        }
        route = routes.get(path)
        if route is None:
            self._send_text(404, "not found\n")
            return
        label, factory = route
        try:
            stream_url = cached_stream_url(label, factory)
        except Exception as error:
            print(f"[FALLO] {label}: {type(error).__name__}", flush=True)
            self._send_text(503, f"{label} no disponible temporalmente\n")
            return

        self.send_response(302)
        self.send_header("Location", stream_url)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _send_text(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        # Nunca registrar Location: contiene el token temporal.
        print(f"[HTTP] {self.command} {self.path.split('?', 1)[0]}", flush=True)


def main() -> int:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), ResolverHandler)
    print(f"VibeM3U Chile resolver escuchando en puerto {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
