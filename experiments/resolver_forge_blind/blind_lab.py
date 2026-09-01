"""Hidden randomized fixture lab for Resolver Forge blind trials.

The system under test must not import this module. The orchestrator exposes only
PublicCase values to forge_core and keeps expectations inside HiddenCase.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import random
import string
import threading
import urllib.parse
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


SUPPORTED_FAMILIES = (
    "fixed_json",
    "json_nested",
    "json_urlencoded",
    "json_base64",
    "nested_json_string",
    "html_attribute",
    "html_script_json",
    "plain_text",
    "two_hop",
    "same_origin_redirect",
    "relative_hls",
    "decoy_then_valid",
)

OUT_OF_ENVELOPE_FAMILIES = (
    "xor_cipher",
    "javascript_reverse",
    "missing_identity",
    "new_control_host",
    "too_deep",
)

ADVERSARIAL_FAMILIES = (
    "wrong_metadata",
    "wrong_hls_identity",
    "broken_segment",
    "private_redirect",
    "redirect_loop",
    "oversized_body",
    "dangerous_scheme",
    "crossed_content_unobservable",
)


@dataclass(frozen=True)
class PublicCase:
    case_id: str
    entry_url: str
    expected_id: str
    expected_name: str


@dataclass
class HiddenCase:
    case_id: str
    family: str
    expectation: str
    expected_id: str
    expected_name: str
    actual_content_id: str
    nonce: str
    issued_tokens: list[str] = field(default_factory=list)
    entry_requests: int = 0
    random_keys: tuple[str, ...] = ()


def _random_word(rng: random.Random, minimum: int = 5, maximum: int = 12) -> str:
    size = rng.randint(minimum, maximum)
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(size))


class BlindFixtureLab:
    def __init__(self, seed: int, repetitions: int = 2):
        self.seed = seed
        self.rng = random.Random(seed)
        self.cases: dict[str, HiddenCase] = {}
        families: list[tuple[str, str]] = []
        for _ in range(repetitions):
            families.extend((family, "resolve") for family in SUPPORTED_FAMILIES)
            families.extend((family, "reject") for family in OUT_OF_ENVELOPE_FAMILIES)
            families.extend((family, "reject") for family in ADVERSARIAL_FAMILIES)
        self.rng.shuffle(families)
        for index, (family, expectation) in enumerate(families):
            nonce = _random_word(self.rng, 8, 14)
            case_id = f"c{index:03d}-{nonce[:6]}"
            expected_id = f"station-{_random_word(self.rng, 7, 10)}"
            expected_name = f"Channel {_random_word(self.rng, 6, 11).title()}"
            actual = expected_id
            if family in {
                "decoy_then_valid",
                "wrong_hls_identity",
                "wrong_metadata",
                "crossed_content_unobservable",
            }:
                actual = f"station-{_random_word(self.rng, 7, 10)}"
            self.cases[case_id] = HiddenCase(
                case_id=case_id,
                family=family,
                expectation=expectation,
                expected_id=expected_id,
                expected_name=expected_name,
                actual_content_id=actual,
                nonce=nonce,
                random_keys=tuple(_random_word(self.rng) for _ in range(6)),
            )
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.origin = ""

    def start(self) -> None:
        lab = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "BlindResolverLab/1.0"

            def log_message(self, format: str, *args) -> None:  # noqa: A002, ANN002
                return

            def do_GET(self) -> None:  # noqa: N802
                lab._handle(self)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = int(self.httpd.server_address[1])
        self.origin = f"http://127.0.0.1:{port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)

    def public_cases(self) -> list[PublicCase]:
        if not self.origin:
            raise RuntimeError("lab not started")
        return [
            PublicCase(
                case_id=case.case_id,
                entry_url=f"{self.origin}/case/{case.case_id}/entry",
                expected_id=case.expected_id,
                expected_name=case.expected_name,
            )
            for case in self.cases.values()
        ]

    def hidden(self, case_id: str) -> HiddenCase:
        return self.cases[case_id]

    def _token(self, case: HiddenCase) -> str:
        case.entry_requests += 1
        raw = f"{self.seed}:{case.case_id}:{case.entry_requests}:{case.nonce}"
        token = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:28]
        case.issued_tokens.append(token)
        return token

    def _hls_url(self, case: HiddenCase, token: str, *, wrong: bool = False) -> str:
        suffix = "wrong-master.m3u8" if wrong else "master.m3u8"
        return f"{self.origin}/case/{case.case_id}/{suffix}?access_token={token}"

    @staticmethod
    def _send(
        handler: BaseHTTPRequestHandler,
        status: int,
        body: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        handler.send_response(status)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            handler.send_header(key, value)
        handler.end_headers()
        if body:
            try:
                handler.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, handler: BaseHTTPRequestHandler, payload: object) -> None:
        self._send(
            handler,
            HTTPStatus.OK,
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            "application/json",
        )

    def _handle(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urllib.parse.urlsplit(handler.path)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 3 or parts[0] != "case":
            self._send(handler, HTTPStatus.NOT_FOUND, b"", "text/plain")
            return
        case = self.cases.get(parts[1])
        if case is None:
            self._send(handler, HTTPStatus.NOT_FOUND, b"", "text/plain")
            return
        resource = "/".join(parts[2:])
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))

        if resource == "entry":
            self._serve_entry(handler, case)
            return
        if resource.startswith("hop"):
            self._serve_hop(handler, case, resource)
            return
        if resource in {"redirected", "loop"}:
            self._serve_redirect_target(handler, case, resource)
            return
        if resource in {"master.m3u8", "wrong-master.m3u8"}:
            self._serve_master(handler, case, query, wrong=resource.startswith("wrong"))
            return
        if resource in {"media.m3u8", "wrong-media.m3u8"}:
            self._serve_media(handler, case, query, wrong=resource.startswith("wrong"))
            return
        if resource.startswith("segment") or resource.startswith("wrong-segment"):
            self._serve_segment(handler, case, query, wrong=resource.startswith("wrong"))
            return
        self._send(handler, HTTPStatus.NOT_FOUND, b"", "text/plain")

    def _serve_entry(self, handler: BaseHTTPRequestHandler, case: HiddenCase) -> None:
        token = self._token(case)
        url = self._hls_url(case, token)
        wrong_url = self._hls_url(case, token, wrong=True)
        keys = case.random_keys
        family = case.family

        if family == "fixed_json":
            self._json(
                handler,
                {"id": case.expected_id, "streams": [{"url": url}], keys[0]: case.nonce},
            )
        elif family == "json_nested":
            self._json(
                handler,
                {
                    keys[0]: {keys[1]: [{keys[2]: url, keys[3]: case.expected_name}]},
                    keys[4]: [1, True, case.nonce],
                },
            )
        elif family == "json_urlencoded":
            self._json(
                handler,
                {keys[0]: urllib.parse.quote_plus(url), keys[1]: case.expected_id},
            )
        elif family == "json_base64":
            encoded = base64.b64encode(url.encode("utf-8")).decode("ascii")
            self._json(handler, {keys[0]: encoded, keys[1]: case.expected_name})
        elif family == "nested_json_string":
            nested = json.dumps({keys[1]: url, keys[2]: case.expected_id})
            self._json(handler, {keys[0]: nested, keys[3]: case.nonce})
        elif family == "html_attribute":
            body = (
                "<html><body>"
                f'<section data-{keys[0]}="{html.escape(case.expected_name)}">'
                f'<button data-{keys[1]}="{html.escape(url)}">play</button>'
                "</section></body></html>"
            ).encode("utf-8")
            self._send(handler, HTTPStatus.OK, body, "text/html")
        elif family == "html_script_json":
            payload = json.dumps({keys[0]: case.expected_id, keys[1]: {keys[2]: url}})
            body = (
                "<html><body><script type=\"application/json\">"
                + html.escape(payload, quote=False)
                + "</script></body></html>"
            ).encode("utf-8")
            self._send(handler, HTTPStatus.OK, body, "text/html")
        elif family == "plain_text":
            body = f"provider={case.nonce}\nchannel={case.expected_name}\nplay={url}\n".encode()
            self._send(handler, HTTPStatus.OK, body, "text/plain")
        elif family == "two_hop":
            self._json(
                handler,
                {
                    keys[0]: case.expected_id,
                    keys[1]: f"/case/{case.case_id}/hop1?ticket={token}",
                },
            )
        elif family == "same_origin_redirect":
            location = f"/case/{case.case_id}/redirected?ticket={token}"
            self._send(handler, HTTPStatus.FOUND, b"", "text/plain", {"Location": location})
        elif family == "relative_hls":
            self._json(
                handler,
                {keys[0]: case.expected_name, keys[1]: f"master.m3u8?access_token={token}"},
            )
        elif family == "decoy_then_valid":
            self._json(
                handler,
                {
                    keys[0]: case.expected_id,
                    keys[1]: [wrong_url, url],
                },
            )
        elif family == "xor_cipher":
            encrypted = bytes(byte ^ 0x23 for byte in url.encode("utf-8"))
            self._json(
                handler,
                {keys[0]: base64.b64encode(encrypted).decode("ascii"), keys[1]: case.expected_id},
            )
        elif family == "javascript_reverse":
            body = (
                "<html><body>"
                f"<p>{html.escape(case.expected_name)}</p>"
                f"<script>const x='{url[::-1]}';play(x.split('').reverse().join(''));</script>"
                "</body></html>"
            ).encode("utf-8")
            self._send(handler, HTTPStatus.OK, body, "text/html")
        elif family == "missing_identity":
            self._json(handler, {keys[0]: url, keys[1]: case.nonce})
        elif family == "new_control_host":
            self._json(
                handler,
                {keys[0]: case.expected_id, keys[1]: "https://untrusted.invalid/new-api"},
            )
        elif family == "too_deep":
            self._json(
                handler,
                {keys[0]: case.expected_name, keys[1]: f"/case/{case.case_id}/hop1?ticket={token}"},
            )
        elif family == "wrong_metadata":
            self._json(handler, {keys[0]: case.actual_content_id, keys[1]: url})
        elif family == "wrong_hls_identity":
            self._json(handler, {keys[0]: case.expected_id, keys[1]: wrong_url})
        elif family == "broken_segment":
            self._json(handler, {keys[0]: case.expected_id, keys[1]: url})
        elif family == "private_redirect":
            self._send(
                handler,
                HTTPStatus.FOUND,
                b"",
                "text/plain",
                {"Location": "http://169.254.169.254/latest/meta-data/"},
            )
        elif family == "redirect_loop":
            self._send(
                handler,
                HTTPStatus.FOUND,
                b"",
                "text/plain",
                {"Location": f"/case/{case.case_id}/loop"},
            )
        elif family == "oversized_body":
            body = (case.expected_id + "\n" + url + "\n").encode() + b"X" * (300 * 1024)
            self._send(handler, HTTPStatus.OK, body, "text/plain")
        elif family == "dangerous_scheme":
            body = (
                f"<html><p>{html.escape(case.expected_name)}</p>"
                "<a href='file:///etc/passwd'>play</a>"
                "<a href='gopher://127.0.0.1/'>backup</a></html>"
            ).encode()
            self._send(handler, HTTPStatus.OK, body, "text/html")
        elif family == "crossed_content_unobservable":
            self._json(handler, {keys[0]: case.expected_id, keys[1]: wrong_url})
        else:
            self._send(handler, HTTPStatus.INTERNAL_SERVER_ERROR, b"", "text/plain")

    def _serve_hop(
        self,
        handler: BaseHTTPRequestHandler,
        case: HiddenCase,
        resource: str,
    ) -> None:
        number_text = resource.removeprefix("hop")
        try:
            number = int(number_text)
        except ValueError:
            self._send(handler, HTTPStatus.NOT_FOUND, b"", "text/plain")
            return
        token = case.issued_tokens[-1] if case.issued_tokens else self._token(case)
        if case.family == "two_hop":
            self._json(
                handler,
                {case.random_keys[2]: self._hls_url(case, token), case.random_keys[3]: case.expected_name},
            )
            return
        if case.family == "too_deep":
            if number <= 5:
                self._json(
                    handler,
                    {case.random_keys[number % len(case.random_keys)]: f"/case/{case.case_id}/hop{number + 1}"},
                )
            else:
                self._json(handler, {case.random_keys[0]: self._hls_url(case, token)})
            return
        self._send(handler, HTTPStatus.NOT_FOUND, b"", "text/plain")

    def _serve_redirect_target(
        self,
        handler: BaseHTTPRequestHandler,
        case: HiddenCase,
        resource: str,
    ) -> None:
        if resource == "loop":
            self._send(
                handler,
                HTTPStatus.FOUND,
                b"",
                "text/plain",
                {"Location": f"/case/{case.case_id}/entry"},
            )
            return
        token = case.issued_tokens[-1] if case.issued_tokens else self._token(case)
        self._json(
            handler,
            {case.random_keys[0]: case.expected_name, case.random_keys[1]: self._hls_url(case, token)},
        )

    def _valid_token(self, case: HiddenCase, query: dict[str, str]) -> bool:
        return query.get("access_token", "") in case.issued_tokens

    def _serve_master(
        self,
        handler: BaseHTTPRequestHandler,
        case: HiddenCase,
        query: dict[str, str],
        *,
        wrong: bool,
    ) -> None:
        if not self._valid_token(case, query):
            self._send(handler, HTTPStatus.FORBIDDEN, b"expired", "text/plain")
            return
        token = query["access_token"]
        identity = case.actual_content_id if wrong else case.expected_id
        session_line = f'#EXT-X-SESSION-DATA:DATA-ID="channel",VALUE="{identity}"\n'
        if case.family == "crossed_content_unobservable":
            session_line = ""
        media = "wrong-media.m3u8" if wrong else "media.m3u8"
        body = (
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            + session_line
            + "#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360\n"
            + f"{media}?access_token={token}\n"
        ).encode()
        self._send(handler, HTTPStatus.OK, body, "application/vnd.apple.mpegurl")

    def _serve_media(
        self,
        handler: BaseHTTPRequestHandler,
        case: HiddenCase,
        query: dict[str, str],
        *,
        wrong: bool,
    ) -> None:
        if not self._valid_token(case, query):
            self._send(handler, HTTPStatus.FORBIDDEN, b"expired", "text/plain")
            return
        token = query["access_token"]
        prefix = "wrong-segment" if wrong else "segment"
        body = (
            "#EXTM3U\n"
            "#EXT-X-TARGETDURATION:4\n"
            "#EXT-X-MEDIA-SEQUENCE:1\n"
            "#EXTINF:4.0,\n"
            f"{prefix}1.ts?access_token={token}\n"
            "#EXTINF:4.0,\n"
            f"{prefix}2.ts?access_token={token}\n"
        ).encode()
        self._send(handler, HTTPStatus.OK, body, "application/vnd.apple.mpegurl")

    def _serve_segment(
        self,
        handler: BaseHTTPRequestHandler,
        case: HiddenCase,
        query: dict[str, str],
        *,
        wrong: bool,
    ) -> None:
        if not self._valid_token(case, query):
            self._send(handler, HTTPStatus.FORBIDDEN, b"expired", "text/plain")
            return
        if case.family == "broken_segment":
            self._send(handler, HTTPStatus.NOT_FOUND, b"", "text/plain")
            return
        content_id = case.actual_content_id if wrong else case.expected_id
        body = ("SYNTHETIC-VIDEO:" + content_id + ":" + case.nonce).encode()
        self._send(handler, HTTPStatus.OK, body, "video/mp2t")


def family_counts(cases: list[HiddenCase]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.family] = counts.get(case.family, 0) + 1
    return counts
