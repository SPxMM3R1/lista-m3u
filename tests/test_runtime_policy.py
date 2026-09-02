import json
import subprocess
import unittest
import urllib.error
from unittest.mock import patch

import run_m3u_6h
import update_m3u


class _Response:
    def __init__(self, body: bytes, url: str) -> None:
        self.status = 200
        self._body = body
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, limit: int) -> bytes:
        return self._body[:limit]

    def geturl(self) -> str:
        return self._url


class RuntimePolicyTests(unittest.TestCase):
    def test_expired_certificate_scope_is_only_known_tvvoo_hls(self) -> None:
        self.assertTrue(
            update_m3u.is_tvvoo_hls_candidate_url(
                "https://td3wb1bchdvsahp.ngolpdkyoctjcddxshli469r.org/"
                "sunshine/opaque/hls/index.m3u8"
            )
        )
        self.assertFalse(
            update_m3u.is_tvvoo_hls_candidate_url(
                "https://example.invalid/sunshine/opaque/hls/index.m3u8"
            )
        )
        self.assertFalse(
            update_m3u.is_tvvoo_hls_candidate_url(
                "https://tvvoo.hayd.uk/stream/tv/alias.json"
            )
        )
        self.assertFalse(
            update_m3u.is_tvvoo_hls_candidate_url(
                "http://td3wb1bchdvsahp.ngolpdkyoctjcddxshli469r.org/"
                "sunshine/opaque/hls/index.m3u8"
            )
        )

    def test_expired_certificate_fallback_requires_explicit_tvvoo_scope(self) -> None:
        url = (
            "https://td3wb1bchdvsahp.ngolpdkyoctjcddxshli469r.org/"
            "sunshine/opaque/hls/index.m3u8"
        )
        error = urllib.error.URLError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "certificate has expired"
        )
        response = _Response(b"#EXTM3U\n", url)

        with patch.object(
            update_m3u.urllib.request,
            "urlopen",
            side_effect=[error, response],
        ) as urlopen:
            status, body, final_url = update_m3u.fetch_bytes(
                url,
                {},
                allow_scoped_expired_cert=True,
            )

        self.assertEqual((status, body, final_url), (200, b"#EXTM3U\n", url))
        self.assertEqual(urlopen.call_count, 2)
        insecure_context = urlopen.call_args_list[1].kwargs["context"]
        self.assertEqual(insecure_context.verify_mode, update_m3u.ssl.CERT_NONE)

        with patch.object(
            update_m3u.urllib.request,
            "urlopen",
            side_effect=error,
        ) as urlopen:
            with self.assertRaises(urllib.error.URLError):
                update_m3u.fetch_bytes(url, {})
        urlopen.assert_called_once()

    def test_tvvoo_candidates_try_http_before_expired_https(self) -> None:
        payload_url = (
            "https://td3wb1bchdvsahp.ngolpdkyoctjcddxshli469r.org/"
            "sunshine/opaque/hls/index.m3u8"
        )
        resolver_map = {"test": ("alias",)}

        def fake_fetch(url, headers, **kwargs):
            return 200, json.dumps({"streams": [{"url": payload_url}]}).encode(), url

        with patch.object(update_m3u, "TVVOO_STREAM_RESOLVER_IDS", resolver_map), patch.object(
            update_m3u, "fetch_bytes", side_effect=fake_fetch
        ):
            candidates = list(update_m3u.iter_fresh_tvvoo_stream_urls("test"))

        self.assertEqual(
            candidates,
            [
                payload_url.replace("https://", "http://", 1),
                payload_url,
            ],
        )

    def test_forced_coordinator_requests_dynamic_refresh(self) -> None:
        completed = subprocess.CompletedProcess([], 0)
        with patch.object(
            run_m3u_6h.subprocess,
            "run",
            return_value=completed,
        ) as run:
            self.assertEqual(run_m3u_6h.run_updater(True), 0)

        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["M3U_FORCE_DYNAMIC_REFRESH"], "true")
        self.assertEqual(environment["M3U_ALLOW_GEO_RESTRICTED"], "true")


if __name__ == "__main__":
    unittest.main()
