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
    def test_app_handled_channels_are_not_background_refreshed(self) -> None:
        self.assertIn("TVN", update_m3u.APP_HANDLED_CHANNELS)
        self.assertIn("Meganoticias", update_m3u.APP_HANDLED_CHANNELS)
        self.assertNotIn("tvn", update_m3u.DYNAMIC_RESOLVER_ENGINES)
        self.assertNotIn("meganoticias", update_m3u.DYNAMIC_RESOLVER_ENGINES)
        self.assertEqual(
            update_m3u.DYNAMIC_RESOLVER_ENGINES,
            frozenset({"tvvoo", "highfly"}),
        )

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

    def test_ar_group_is_excluded_from_public_list_but_kept_for_retry(self) -> None:
        ar = update_m3u.Channel(
            name="TRT ar",
            tvg_id="Vavoo.ar.TRT@TvVoo",
            url="https://example.invalid",
            url_line=0,
        )
        other = update_m3u.Channel(
            name="TRT de",
            tvg_id="Vavoo.de.TRT@TvVoo",
            url="https://example.invalid",
            url_line=0,
        )
        with patch.object(
            update_m3u,
            "TVVOO_STREAM_RESOLVER_IDS",
            {
                ar.name: ("vavoo_TRT%7Cgroup%3Aar",),
                other.name: ("vavoo_TRT%7Cgroup%3Ade",),
            },
        ):
            self.assertFalse(update_m3u.is_permanently_removed_channel(ar))
            self.assertTrue(update_m3u.is_permanently_removed_channel(other))
            self.assertFalse(update_m3u.external_vavoo_channel_is_allowed(ar))
            self.assertFalse(update_m3u.external_vavoo_channel_is_allowed(other))
            self.assertEqual(
                update_m3u.external_publication_channel_ids(
                    [ar], {ar.tvg_id}, set()
                ),
                frozenset(),
            )
            self.assertEqual(
                update_m3u.external_available_ids_from_health(
                    [ar], {ar.tvg_id}, {}
                ),
                frozenset(),
            )
            self.assertEqual(
                update_m3u.external_available_ids_from_health(
                    [ar],
                    {ar.tvg_id},
                    {"channels": {ar.tvg_id: {"status": "functional"}}},
                ),
                {ar.tvg_id},
            )

    def test_external_sky_filter_keeps_sports_and_excludes_other_brands(self) -> None:
        channels = [
            update_m3u.Channel(
                name="Sky Sport F1 Germany",
                tvg_id="SkySportF1.de@TvVoo",
                url="https://example.invalid",
                url_line=0,
            ),
            update_m3u.Channel(
                name="Sky Super Tennis Italia",
                tvg_id="Vavoo.it.SKYSUPERTENNIS@TvVoo",
                url="https://example.invalid",
                url_line=0,
            ),
            update_m3u.Channel(
                name="FOX Sports 4 Países Bajos",
                tvg_id="Vavoo.nl.FOXSPORT4@TvVoo",
                url="https://example.invalid",
                url_line=0,
            ),
            update_m3u.Channel(
                name="Sky Cinema Action Reino Unido",
                tvg_id="Vavoo.uk.SKYCINEMAACTION@TvVoo",
                url="https://example.invalid",
                url_line=0,
            ),
            update_m3u.Channel(
                name="Sky News Reino Unido",
                tvg_id="Vavoo.uk.SKYNEWS@TvVoo",
                url="https://example.invalid",
                url_line=0,
            ),
        ]
        with patch.object(
            update_m3u,
            "TVVOO_STREAM_RESOLVER_IDS",
            {
                channels[0].name: ("sky_sport_f1%7Cgroup%3Ade",),
                channels[1].name: ("sky_super_tennis%7Cgroup%3Ait",),
                channels[2].name: ("fox_sports_4%7Cgroup%3Anl",),
                channels[3].name: ("sky_cinema%7Cgroup%3Auk",),
                channels[4].name: ("sky_news%7Cgroup%3Auk",),
            },
        ):
            self.assertTrue(update_m3u.external_vavoo_channel_is_allowed(channels[0]))
            self.assertTrue(update_m3u.external_vavoo_channel_is_allowed(channels[1]))
            self.assertTrue(update_m3u.external_vavoo_channel_is_allowed(channels[2]))
            self.assertFalse(update_m3u.external_vavoo_channel_is_allowed(channels[3]))
            self.assertFalse(update_m3u.external_vavoo_channel_is_allowed(channels[4]))


if __name__ == "__main__":
    unittest.main()
