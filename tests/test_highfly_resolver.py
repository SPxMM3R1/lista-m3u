import json
import unittest
from unittest.mock import patch

import update_m3u


class HighflyResolverTest(unittest.TestCase):
    def test_runtime_map_uses_current_sky_leaf_slugs(self) -> None:
        payload = {
            "metas": [
                {
                    "id": "leaf:f1-3949409",
                    "name": "(FHD) : SKY SPORTS F1 ᴿᴬᵂ",
                },
                {"id": "leaf:us-espn-hd-0", "name": "(HD) : ESPN"},
                {"id": "leaf:us-33323323", "name": "(HD) : ESPN 2"},
                {
                    "id": "leaf:uk-330030303",
                    "name": "(FHD) : SKY SPORTS TENNIS ᴿᴬᵂ",
                },
                {
                    "id": "leaf:now-4994949494",
                    "name": "(FHD) : SKY SPORTS PREMIER LEAGUE ᴿᴬᵂ",
                },
            ]
        }

        self.assertEqual(
            {
                "SkySportsF1.uk": "f1-3949409",
                "SkySportsTennis.uk": "uk-330030303",
                "SkySportsPremierLeague.uk": "now-4994949494",
            },
            update_m3u.parse_highfly_live_resolver_map(payload),
        )

    def test_runtime_map_ignores_events_and_unknown_leafs(self) -> None:
        payload = {
            "metas": [
                {"id": "streamed:us-open-2026", "name": "US Open"},
                {"id": "leaf:unknown-channel", "name": "Unknown channel"},
                {"id": "javascript:unsafe", "name": "Unsafe"},
                {"id": "leaf:uk-330030303", "name": "Sky Sports Tennis"},
            ]
        }

        self.assertEqual(
            {"SkySportsTennis.uk": "uk-330030303"},
            update_m3u.parse_highfly_live_resolver_map(payload),
        )

    def test_highfly_stream_response_rejects_upgrade_and_non_leaf_urls(self) -> None:
        payload = {
            "streams": [
                {"url": "https://www.google.com/accounts/upgrade"},
                {
                    "url": (
                        "https://papacito.cfd/m3u/f1-3949409/"
                        "live.m3u8"
                    )
                },
                {"url": "https://papacito.cfd/other/live.m3u8"},
            ]
        }

        self.assertEqual(
            ["https://papacito.cfd/m3u/f1-3949409/live.m3u8"],
            update_m3u.highfly_stream_urls_from_payload(payload),
        )

    def test_highfly_stream_response_prefers_highest_reported_bitrate(self) -> None:
        low = "https://papacito.cfd/m3u/low/live.m3u8"
        high = "https://papacito.cfd/m3u/high/live.m3u8"
        numeric = "https://papacito.cfd/m3u/numeric/live.m3u8"
        payload = {
            "streams": [
                {"url": low, "title": "1920x1080 · Stereo · ~7.8 Mbps"},
                {"url": high, "title": "1920x1080 · Stereo · ~9.6 Mbps"},
                {"url": numeric, "bandwidth": 8_500_000},
            ]
        }

        self.assertEqual(
            [high, numeric, low],
            update_m3u.highfly_stream_urls_from_payload(payload),
        )

    def test_highfly_stream_response_keeps_provider_order_without_bitrate(self) -> None:
        first = "https://papacito.cfd/m3u/first/live.m3u8"
        second = "https://papacito.cfd/m3u/second/live.m3u8"
        payload = {"streams": [{"url": first}, {"url": second}]}

        self.assertEqual(
            [first, second],
            update_m3u.highfly_stream_urls_from_payload(payload),
        )

    def test_dynamic_refresh_keeps_healthy_current_highfly_candidate(self) -> None:
        current = "https://papacito.cfd/m3u/high/live.m3u8"
        lower = "https://papacito.cfd/m3u/lower/live.m3u8"
        channel = update_m3u.Channel(
            name="Sky Sports Tennis",
            url=current,
            url_line=1,
            info_line=0,
            tvg_id="SkySportsTennis.uk",
            display_name="Sky Sports Tennis",
        )
        current_result = update_m3u.CheckResult(
            channel.name,
            current,
            True,
            "enlace actual validado",
        )

        with patch.object(update_m3u, "check_channel") as check_channel:
            outcome = update_m3u.refresh_dynamic_channel(
                channel,
                lambda: iter([current, lower]),
                running_in_ci=False,
                current_result=current_result,
            )

        self.assertTrue(outcome.accepted)
        self.assertFalse(outcome.changed)
        self.assertEqual(current, outcome.resolved_url)
        self.assertIs(outcome.check_result, current_result)
        check_channel.assert_not_called()

    def test_papacito_numeric_playlist_is_decoded_only_for_highfly_host(self) -> None:
        encoded = b"35\n69\n88\n84\n77\n51\n85\n10"
        self.assertEqual(
            b"#EXTM3U\n",
            update_m3u.decode_highfly_playlist_body(
                encoded, "https://papacito.cfd/m3u/f1-3949409/live.m3u8"
            ),
        )
        self.assertEqual(
            encoded,
            update_m3u.decode_highfly_playlist_body(
                encoded, "https://example.invalid/m3u/f1-3949409/live.m3u8"
            ),
        )

    def test_runtime_catalog_updates_highfly_leaf_fallback(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="SkySportsF1.uk" x-resolver="highfly" x-resolver-id="old-f1-39388833",Sky Sports F1',
            "https://papacito.cfd/m3u/old-f1-39388833/live.m3u8",
        ]

        with patch.dict(
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS,
            {"SkySportsF1.uk": "f1-93930303"},
            clear=True,
        ):
            changed = update_m3u.sync_highfly_runtime_fallbacks(lines)

        self.assertTrue(changed)
        self.assertEqual(
            "https://papacito.cfd/m3u/f1-93930303/live.m3u8",
            lines[2],
        )
        self.assertIn('x-resolver-id="f1-93930303"', lines[1])

    def test_fresh_highfly_uses_runtime_slug_and_stream_api(self) -> None:
        channel = update_m3u.Channel(
            name="Sky Sports F1",
            url="https://papacito.cfd/m3u/old/live.m3u8",
            url_line=1,
            info_line=0,
            tvg_id="SkySportsF1.uk",
            display_name="Sky Sports F1",
        )
        api_url = "https://sports.highfly.to/stream/sport/leaf:f1-3949409.json"
        response = {
            "streams": [
                {"url": "https://papacito.cfd/m3u/f1-3949409/live.m3u8"}
            ]
        }

        with patch.object(
            update_m3u,
            "HIGHFLY_RUNTIME_RESOLVER_CHANNELS",
            {"SkySportsF1.uk": "f1-3949409"},
        ), patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(200, json.dumps(response).encode("utf-8"), api_url),
        ) as fetch:
            urls = list(
                update_m3u.fresh_highfly_stream_urls(
                    channel, manifest_verified=True
                )
            )

        self.assertEqual(
            ["https://papacito.cfd/m3u/f1-3949409/live.m3u8"], urls
        )
        fetch.assert_called_once()
        self.assertIn(api_url, fetch.call_args.args)

    def test_runtime_catalog_refresh_is_in_memory_only(self) -> None:
        payload = {
            "metas": [
                {"id": "leaf:uk-330030303", "name": "Sky Sports Tennis"}
            ]
        }
        with patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(
                200,
                json.dumps(payload).encode("utf-8"),
                update_m3u.HIGHFLY_PUBLIC_CATALOG_URL,
            ),
        ):
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS.clear()
            mapping = update_m3u.refresh_highfly_runtime_catalog()

        self.assertEqual({"SkySportsTennis.uk": "uk-330030303"}, mapping)
        self.assertEqual(
            "uk-330030303",
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS["SkySportsTennis.uk"],
        )

if __name__ == "__main__":
    unittest.main()
