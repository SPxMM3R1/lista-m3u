"""Bounded, data-only resolver recipe discovery used by the blind experiment.

The module intentionally knows nothing about the fixture generator. It treats
all responses as untrusted data and emits a replayable generic recipe rather
than executable code.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import html.parser
import ipaddress
import json
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable


URL_PATTERN = re.compile(r"https?://[^\s\"'<>\\]+|/(?:[^\s\"'<>\\])+")
SESSION_DATA_PATTERN = re.compile(
    r'#EXT-X-SESSION-DATA:[^\n]*?DATA-ID="channel"[^\n]*?VALUE="([^"]+)"',
    re.IGNORECASE,
)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(?:token|auth|signature|sig|key|secret|session|jwt|expires?)"
)
HLS_CONTENT_TYPES = {
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
}


class ForgeError(RuntimeError):
    """A bounded resolver operation failed closed."""


class SecurityViolation(ForgeError):
    """A network or data safety invariant was violated."""


class BudgetExceeded(ForgeError):
    """A request, response, traversal or candidate budget was exceeded."""


@dataclass(frozen=True)
class ForgePolicy:
    allowed_control_origins: frozenset[str]
    max_requests: int = 16
    max_response_bytes: int = 256 * 1024
    max_redirects: int = 3
    max_depth: int = 3
    max_candidates: int = 128
    max_strings: int = 512
    timeout_seconds: float = 2.0
    segments_to_probe: int = 2
    test_mode: bool = False
    allow_http_stream_fallback: bool = False


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes


@dataclass(frozen=True)
class ExtractedString:
    value: str
    locator: str


@dataclass(frozen=True)
class Recipe:
    entry_url: str
    expected_id: str
    expected_name: str
    strategy: str = "bounded-recursive-discovery-v1"
    max_depth: int = 3
    max_candidates: int = 128

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "entryUrl": self.entry_url,
                "expectedId": self.expected_id,
                "expectedName": self.expected_name,
                "maxCandidates": self.max_candidates,
                "maxDepth": self.max_depth,
                "strategy": self.strategy,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass
class Resolution:
    accepted: bool
    recipe: Recipe
    resolved_url: str | None = None
    redacted_url: str | None = None
    reason: str = ""
    identity_evidence: tuple[str, ...] = ()
    stream_identity: str | None = None
    requests: int = 0
    bytes_read: int = 0
    security_events: tuple[str, ...] = ()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class SafeHttpClient:
    """Small HTTP client with explicit redirects, DNS checks and hard budgets."""

    def __init__(self, policy: ForgePolicy):
        self.policy = policy
        self.requests = 0
        self.bytes_read = 0
        self.security_events: list[str] = []
        self._opener = urllib.request.build_opener(_NoRedirect())

    @staticmethod
    def origin(url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
        default = 443 if parsed.scheme.lower() == "https" else 80
        suffix = f":{port}" if port and port != default else ""
        return f"{parsed.scheme.lower()}://{(parsed.hostname or '').lower()}{suffix}"

    def _validate_url(self, url: str, *, control: bool) -> None:
        try:
            parsed = urllib.parse.urlsplit(url)
            port = parsed.port
        except ValueError as error:
            raise SecurityViolation("URL invalida") from error
        if parsed.username or parsed.password:
            raise SecurityViolation("userinfo no permitido")
        allowed_schemes = {"https"}
        if self.policy.test_mode or (
            not control and self.policy.allow_http_stream_fallback
        ):
            allowed_schemes.add("http")
        if parsed.scheme.lower() not in allowed_schemes:
            raise SecurityViolation("esquema no permitido")
        if not parsed.hostname:
            raise SecurityViolation("host ausente")
        if port is not None and not (1 <= port <= 65535):
            raise SecurityViolation("puerto invalido")
        origin = self.origin(url)
        if control and origin not in self.policy.allowed_control_origins:
            raise SecurityViolation("host de control no permitido")

        host = parsed.hostname
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            if self.policy.test_mode and origin in self.policy.allowed_control_origins:
                return
            if not literal.is_global:
                raise SecurityViolation("IP no publica")
            return

        if self.policy.test_mode:
            if origin not in self.policy.allowed_control_origins:
                raise SecurityViolation("DNS externo bloqueado en prueba")
            return
        try:
            addresses = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
        except OSError as error:
            raise ForgeError("DNS no resolvio") from error
        if not addresses:
            raise ForgeError("DNS sin direcciones")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise SecurityViolation("DNS resolvio a red no publica")

    def fetch(
        self,
        url: str,
        *,
        control: bool = True,
        read_limit: int | None = None,
    ) -> FetchResult:
        current = url
        redirects = 0
        downgraded_stream = False
        while True:
            self._validate_url(current, control=control)
            if self.requests >= self.policy.max_requests:
                raise BudgetExceeded("presupuesto de peticiones agotado")
            self.requests += 1
            request = urllib.request.Request(
                current,
                headers={
                    "Accept": "application/json,text/html,application/vnd.apple.mpegurl,*/*;q=0.5",
                    "User-Agent": "ResolverForgeBlind/1.0",
                },
            )
            try:
                response = self._opener.open(request, timeout=self.policy.timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                reason = getattr(error, "reason", error)
                tls_verification_error = isinstance(
                    reason,
                    (ssl.SSLCertVerificationError, ssl.CertificateError),
                ) or "certificate verify failed" in str(reason).lower()
                parsed_current = urllib.parse.urlsplit(current)
                can_downgrade = bool(
                    not control
                    and self.policy.allow_http_stream_fallback
                    and not downgraded_stream
                    and parsed_current.scheme.lower() == "https"
                    and tls_verification_error
                )
                if can_downgrade:
                    current = urllib.parse.urlunsplit(
                        (
                            "http",
                            parsed_current.netloc,
                            parsed_current.path,
                            parsed_current.query,
                            parsed_current.fragment,
                        )
                    )
                    downgraded_stream = True
                    self.security_events.append(
                        "fallback HTTP de stream autorizado por politica"
                    )
                    continue
                raise ForgeError("peticion fallida") from error

            status = int(getattr(response, "status", response.getcode()))
            if status in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location", "").strip()
                response.close()
                if not location:
                    raise ForgeError("redireccion sin destino")
                redirects += 1
                if redirects > self.policy.max_redirects:
                    raise BudgetExceeded("demasiadas redirecciones")
                next_url = urllib.parse.urljoin(current, location)
                # Redirects never broaden the control origin.
                self._validate_url(next_url, control=control)
                current = next_url
                continue
            if status < 200 or status >= 300:
                response.close()
                raise ForgeError(f"HTTP {status}")

            remaining = self.policy.max_response_bytes - self.bytes_read
            if remaining <= 0:
                response.close()
                raise BudgetExceeded("presupuesto total de bytes agotado")
            if read_limit is not None:
                requested_bytes = max(1, min(read_limit, remaining))
                body = response.read(requested_bytes)
            else:
                requested_bytes = min(remaining, self.policy.max_response_bytes)
                body = response.read(requested_bytes + 1)
            content_type = response.headers.get_content_type().lower()
            final_url = response.geturl()
            response.close()
            if read_limit is None and (
                len(body) > remaining or len(body) > self.policy.max_response_bytes
            ):
                raise BudgetExceeded("respuesta demasiado grande")
            self.bytes_read += len(body)
            return FetchResult(url, final_url, status, content_type, body)


class _StringHTMLParser(html.parser.HTMLParser):
    def __init__(self, limit: int):
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.values: list[ExtractedString] = []
        self._script_json = False
        self._script_chunks: list[str] = []

    def _add(self, value: str, locator: str) -> None:
        value = value.strip()
        if value and len(self.values) < self.limit:
            self.values.append(ExtractedString(value[:8192], locator))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        for key, value in attr_map.items():
            self._add(value, f"html:{tag}@{key}")
        if tag.lower() == "script" and "json" in attr_map.get("type", "").lower():
            self._script_json = True
            self._script_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script_json:
            self._add("".join(self._script_chunks), "html:script-json")
            self._script_json = False
            self._script_chunks = []

    def handle_data(self, data: str) -> None:
        if self._script_json:
            self._script_chunks.append(data)
        else:
            self._add(data, "html:text")


def _walk_json(value: object, *, limit: int) -> list[ExtractedString]:
    values: list[ExtractedString] = []
    stack: list[tuple[object, str]] = [(value, "$")]
    while stack and len(values) < limit:
        current, path = stack.pop()
        if isinstance(current, dict):
            for key, nested in reversed(list(current.items())):
                stack.append((nested, f"{path}.{str(key)[:80]}"))
        elif isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                stack.append((current[index], f"{path}[{index}]"))
        elif isinstance(current, (str, int, float, bool)):
            text = str(current).strip()
            if text:
                values.append(ExtractedString(text[:8192], f"json:{path}"))
    return values


def extract_strings(result: FetchResult, limit: int) -> list[ExtractedString]:
    text = result.body.decode("utf-8", "replace")
    stripped = text.lstrip()
    if result.content_type == "application/json" or stripped.startswith(("{", "[")):
        try:
            return _walk_json(json.loads(text), limit=limit)
        except (json.JSONDecodeError, RecursionError):
            pass
    if result.content_type == "text/html" or "<html" in stripped[:256].lower():
        parser = _StringHTMLParser(limit)
        try:
            parser.feed(text)
            parser.close()
        except (html.parser.HTMLParseError, RecursionError):
            pass
        return parser.values
    return [
        ExtractedString(line.strip()[:8192], f"text:{index}")
        for index, line in enumerate(text.splitlines())
        if line.strip()
    ][:limit]


def _normalise_identity(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def identity_matches(value: str, expected_id: str, expected_name: str) -> bool:
    normalised = _normalise_identity(value)
    expected = {
        _normalise_identity(expected_id),
        _normalise_identity(expected_name),
    }
    return any(token and (normalised == token or token in normalised) for token in expected)


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.query:
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    keys = []
    for key, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        keys.append(f"{key}=REDACTED" if SENSITIVE_KEY_PATTERN.search(key) else f"{key}=VALUE")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "&".join(keys), ""))


def _decode_variants(raw: str) -> Iterable[tuple[str, str]]:
    """Yield bounded reversible data transforms; never execute source text."""
    seen: set[str] = set()
    queue: deque[tuple[str, str, int]] = deque([(raw.strip(), "literal", 0)])
    while queue:
        value, method, depth = queue.popleft()
        if not value or value in seen or len(value) > 8192:
            continue
        seen.add(value)
        yield value, method
        if depth >= 2:
            continue

        decoded_url = urllib.parse.unquote_plus(value)
        if decoded_url != value:
            queue.append((decoded_url, method + ">url-decode", depth + 1))

        compact = value.strip()
        if len(compact) >= 12 and len(compact) % 4 in {0, 2, 3}:
            padded = compact + "=" * ((4 - len(compact) % 4) % 4)
            try:
                decoded = base64.b64decode(padded, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, ValueError):
                decoded = ""
            if decoded and decoded != value:
                queue.append((decoded, method + ">base64", depth + 1))

        if compact.startswith(("{", "[", '"')):
            try:
                nested = json.loads(compact)
            except (json.JSONDecodeError, RecursionError):
                nested = None
            if isinstance(nested, str):
                queue.append((nested, method + ">json-string", depth + 1))
            elif isinstance(nested, (dict, list)):
                for item in _walk_json(nested, limit=32):
                    queue.append((item.value, method + ">nested-json", depth + 1))


def _candidate_urls(raw: str, base_url: str) -> Iterable[tuple[str, str]]:
    for decoded, method in _decode_variants(raw):
        matches = list(URL_PATTERN.finditer(decoded))
        compact = decoded.strip()
        if not matches:
            try:
                relative_path = urllib.parse.urlsplit(compact).path.lower()
            except ValueError:
                relative_path = ""
            is_relative_resource = (
                compact
                and not any(character.isspace() for character in compact)
                and (
                    compact.startswith(("http://", "https://", "/", "./", "../"))
                    or relative_path.endswith((".m3u8", ".json", ".txt", ".html"))
                )
            )
            if is_relative_resource:
                matches = [type("Whole", (), {"group": lambda self, _=0: compact})()]
        for match in matches:
            value = match.group(0).rstrip(".,;)]}")
            yield urllib.parse.urljoin(base_url, value), method


def _looks_hls_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return parsed.path.lower().endswith(".m3u8")


def _looks_discovery_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.lower()
    blocked_suffixes = (
        ".ts",
        ".m4s",
        ".mp4",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".css",
        ".woff",
        ".woff2",
    )
    return not path.endswith(blocked_suffixes)


@dataclass
class _HlsProbe:
    ok: bool
    stream_identity: str | None = None
    reason: str = ""
    resolved_url: str | None = None


def probe_hls(
    client: SafeHttpClient,
    url: str,
    *,
    expected_id: str,
    expected_name: str,
) -> _HlsProbe:
    try:
        master = client.fetch(url, control=False)
    except ForgeError as error:
        return _HlsProbe(False, reason=str(error))
    text = master.body.decode("utf-8", "replace")
    if not text.lstrip().startswith("#EXTM3U"):
        return _HlsProbe(False, reason="no es HLS")
    stream_identity = None
    identity_match = SESSION_DATA_PATTERN.search(text)
    if identity_match:
        stream_identity = identity_match.group(1).strip()
        if not identity_matches(stream_identity, expected_id, expected_name):
            return _HlsProbe(False, stream_identity, "identidad HLS distinta")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    media_url = master.final_url
    for index, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            for nested in lines[index + 1 :]:
                if not nested.startswith("#"):
                    media_url = urllib.parse.urljoin(master.final_url, nested)
                    break
            break
    if media_url != master.final_url:
        try:
            media = client.fetch(media_url, control=False)
        except ForgeError as error:
            return _HlsProbe(False, stream_identity, str(error))
        media_text = media.body.decode("utf-8", "replace")
        if not media_text.lstrip().startswith("#EXTM3U"):
            return _HlsProbe(False, stream_identity, "variante no HLS")
        media_lines = [line.strip() for line in media_text.splitlines() if line.strip()]
        media_base = media.final_url
    else:
        media_lines = lines
        media_base = master.final_url

    segments = [
        urllib.parse.urljoin(media_base, line)
        for line in media_lines
        if not line.startswith("#")
    ]
    if not segments:
        return _HlsProbe(False, stream_identity, "playlist sin segmentos")
    segment_candidates = list(dict.fromkeys([segments[0], *segments[-3:]]))
    successful_segments = 0
    last_segment_error = "segmento no disponible"
    for segment in segment_candidates:
        try:
            result = client.fetch(segment, control=False, read_limit=64)
        except ForgeError as error:
            last_segment_error = str(error)
            continue
        if not result.body:
            last_segment_error = "segmento vacio"
            continue
        successful_segments += 1
        if successful_segments >= client.policy.segments_to_probe:
            break
    if successful_segments < client.policy.segments_to_probe:
        return _HlsProbe(False, stream_identity, last_segment_error)
    return _HlsProbe(True, stream_identity, "HLS completo", master.final_url)


def execute_recipe(recipe: Recipe, policy: ForgePolicy) -> Resolution:
    client = SafeHttpClient(policy)
    evidence: set[str] = set()
    queue: deque[tuple[str, int, bool]] = deque([(recipe.entry_url, 0, False)])
    visited: set[str] = set()
    candidates_seen = 0
    failures: list[str] = []

    while queue:
        url, depth, inherited_identity = queue.popleft()
        canonical = redact_url(url)
        if canonical in visited:
            continue
        visited.add(canonical)
        if depth > min(policy.max_depth, recipe.max_depth):
            continue
        try:
            result = client.fetch(url, control=not _looks_hls_url(url))
        except SecurityViolation as error:
            client.security_events.append(str(error))
            failures.append(str(error))
            continue
        except ForgeError as error:
            failures.append(str(error))
            continue

        if result.body.lstrip().startswith(b"#EXTM3U") or _looks_hls_url(result.final_url):
            if not inherited_identity:
                failures.append("identidad no demostrada antes de HLS")
                continue
            probe = probe_hls(
                client,
                result.final_url,
                expected_id=recipe.expected_id,
                expected_name=recipe.expected_name,
            )
            if probe.ok:
                return Resolution(
                    accepted=True,
                    recipe=recipe,
                    resolved_url=result.final_url,
                    redacted_url=redact_url(result.final_url),
                    reason="receta valida",
                    identity_evidence=tuple(sorted(evidence)),
                    stream_identity=probe.stream_identity,
                    requests=client.requests,
                    bytes_read=client.bytes_read,
                    security_events=tuple(client.security_events),
                )
            failures.append(probe.reason)
            continue

        strings = extract_strings(result, policy.max_strings)
        local_identity = inherited_identity
        for item in strings:
            if identity_matches(item.value, recipe.expected_id, recipe.expected_name):
                local_identity = True
                evidence.add(item.locator)

        for item in strings:
            for candidate, method in _candidate_urls(item.value, result.final_url):
                candidates_seen += 1
                if candidates_seen > min(policy.max_candidates, recipe.max_candidates):
                    failures.append("presupuesto de candidatos agotado")
                    queue.clear()
                    break
                candidate_redacted = redact_url(candidate)
                if candidate_redacted in visited:
                    continue
                try:
                    parsed = urllib.parse.urlsplit(candidate)
                except ValueError:
                    continue
                if parsed.scheme not in {"http", "https"}:
                    continue
                if _looks_hls_url(candidate):
                    if not local_identity:
                        continue
                    try:
                        client._validate_url(candidate, control=False)
                    except SecurityViolation as error:
                        client.security_events.append(str(error))
                        continue
                    probe = probe_hls(
                        client,
                        candidate,
                        expected_id=recipe.expected_id,
                        expected_name=recipe.expected_name,
                    )
                    if probe.ok:
                        evidence.add(f"{item.locator}:{method}")
                        resolved_url = probe.resolved_url or candidate
                        return Resolution(
                            accepted=True,
                            recipe=recipe,
                            resolved_url=resolved_url,
                            redacted_url=redact_url(resolved_url),
                            reason="receta valida",
                            identity_evidence=tuple(sorted(evidence)),
                            stream_identity=probe.stream_identity,
                            requests=client.requests,
                            bytes_read=client.bytes_read,
                            security_events=tuple(client.security_events),
                        )
                    failures.append(probe.reason)
                elif depth < min(policy.max_depth, recipe.max_depth) and _looks_discovery_url(candidate):
                    try:
                        if SafeHttpClient.origin(candidate) not in policy.allowed_control_origins:
                            client.security_events.append("host de control no permitido")
                            continue
                    except ValueError:
                        continue
                    queue.append((candidate, depth + 1, local_identity))

    reason = failures[-1] if failures else "sin candidato util"
    return Resolution(
        accepted=False,
        recipe=recipe,
        reason=reason,
        identity_evidence=tuple(sorted(evidence)),
        requests=client.requests,
        bytes_read=client.bytes_read,
        security_events=tuple(client.security_events),
    )


def discover_recipe(
    entry_url: str,
    expected_id: str,
    expected_name: str,
    policy: ForgePolicy,
) -> Resolution:
    recipe = Recipe(
        entry_url=entry_url,
        expected_id=expected_id,
        expected_name=expected_name,
        max_depth=policy.max_depth,
        max_candidates=policy.max_candidates,
    )
    return execute_recipe(recipe, policy)


def fixed_schema_baseline(
    entry_url: str,
    expected_id: str,
    expected_name: str,
    policy: ForgePolicy,
) -> bool:
    """Approximate the current fixed `streams[].url` style resolver."""
    client = SafeHttpClient(policy)
    try:
        result = client.fetch(entry_url, control=True)
        payload = json.loads(result.body.decode("utf-8"))
        streams = payload.get("streams", [])
        if not isinstance(streams, list):
            return False
        identity = payload.get("id") or payload.get("name") or ""
        if not identity_matches(str(identity), expected_id, expected_name):
            return False
        for stream in streams[:16]:
            if not isinstance(stream, dict) or not isinstance(stream.get("url"), str):
                continue
            if probe_hls(
                client,
                stream["url"],
                expected_id=expected_id,
                expected_name=expected_name,
            ).ok:
                return True
    except (ForgeError, json.JSONDecodeError, AttributeError, TypeError):
        return False
    return False
