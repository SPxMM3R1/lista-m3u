#!/usr/bin/env python3
"""Serve short-lived Chilean stream redirects without GitHub Raw caching."""

from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from update_m3u import fresh_meganoticias_url  # noqa: E402


class M3URequestHandler(BaseHTTPRequestHandler):
    server_version = "VibeM3ULocal/1.0"

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_text(200, "ok\n")
            return
        if path == "/meganoticias.m3u8":
            self._redirect_to_fresh_meganoticias()
            return
        self._send_text(404, "not found\n")

    def _redirect_to_fresh_meganoticias(self) -> None:
        try:
            stream_url = fresh_meganoticias_url()
        except Exception as error:
            print(
                f"[FALLO] Meganoticias: no se pudo emitir una sesion fresca: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            self._send_text(503, "Meganoticias no disponible desde esta red\n")
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
        # Nunca registrar la URL de redireccion, porque contiene el token.
        print(f"[HTTP] {self.command} {urlsplit(self.path).path}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), M3URequestHandler)
    print(f"VibeM3U local escuchando en http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
