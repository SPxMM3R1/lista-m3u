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
                {"id": "leaf:f-39388833", "name": "4K : SKY SPORTS F1"},
                {
                    "id": "leaf:ten-3930030",
                    "name": "(FHD) : SKY SPORTS TENNIS ᴿᴬᵂ",
                },
                {
                    "id": "leaf:pl-434343434",
                    "name": "(FHD) : SKY SPORTS PREMIER LEAGUE ᴿᴬᵂ",
                },
                {
                    "id": "leaf:ml-383892993",
                    "name": "4K : SKY SPORTS MAIN EVENTS",
                },
            ]
        }

        self.assertEqual(
            {
                "SkySportsF1.uk": "f1-3949409",
                "ESPN.us": "us-espn-hd-0",
                "ESPN2.us": "us-33323323",
                "HighflyPremium.now-sky-sports-f1-2": "f-39388833",
                "SkySportsTennis.uk": "ten-3930030",
                "SkySportsPremierLeague.uk": "pl-434343434",
                "HighflyPremium.4k-sky-sports-main-events": "ml-383892993",
            },
            update_m3u.parse_highfly_live_resolver_map(payload),
        )

    def test_runtime_map_ignores_events_and_unknown_leafs(self) -> None:
        payload = {
            "metas": [
                {"id": "streamed:us-open-2026", "name": "US Open"},
                {"id": "leaf:unknown-channel", "name": "Unknown channel"},
                {"id": "javascript:unsafe", "name": "Unsafe"},
                {"id": "leaf:ten-3930030", "name": "Sky Sports Tennis"},
            ]
        }

        self.assertEqual(
            {"SkySportsTennis.uk": "ten-3930030"},
            update_m3u.parse_highfly_live_resolver_map(payload),
        )

    def test_highfly_stream_response_rejects_upgrade_and_non_leaf_urls(self) -> None:
        payload = {
            "streams": [
                {"url": "https://www.google.com/accounts/upgrade"},
                {
                    "url": (
                        "https://leaf.highfly.dev/m3u/f1-3949409/"
                        "live.m3u8"
                    )
                },
                {"url": "https://leaf.highfly.dev/other/live.m3u8"},
            ]
        }

        self.assertEqual(
            ["https://leaf.highfly.dev/m3u/f1-3949409/live.m3u8"],
            update_m3u.highfly_stream_urls_from_payload(payload),
        )

    def test_highfly_premium_lock_is_detected_without_accepting_upgrade_url(self) -> None:
        payload = {
            "streams": [
                {
                    "name": "\U0001f512 Leaf · (4K) : SKY SPORTS F1",
                    "title": "3840x2160 · Upgrade to Premium",
                    "url": "https://www.google.com/",
                    "behaviorHints": {"notWebReady": True},
                }
            ]
        }

        self.assertTrue(update_m3u.highfly_payload_requires_premium(payload))
        self.assertEqual([], update_m3u.highfly_stream_urls_from_payload(payload))

        with patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(
                200,
                json.dumps(payload).encode("utf-8"),
                "https://sports.highfly.dev/stream/sport/leaf:f1-93930303.json",
            ),
        ):
            with self.assertRaises(update_m3u.HighflyPremiumRequired) as raised:
                update_m3u.fetch_highfly_stream_urls_for_slug("f1-93930303")

        self.assertEqual(
            "https://leaf.highfly.dev/m3u/f1-93930303/live.m3u8",
            raised.exception.fallback_url,
        )

    def test_runtime_catalog_updates_highfly_leaf_fallback(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="HighflyPremium.now-sky-sports-f1-2" x-resolver="highfly" x-resolver-id="f-39388833",Sky Sports F1 UHD',
            "https://leaf.highfly.dev/m3u/f-39388833/live.m3u8",
        ]

        with patch.dict(
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS,
            {"HighflyPremium.now-sky-sports-f1-2": "f1-93930303"},
            clear=True,
        ):
            changed = update_m3u.sync_highfly_runtime_fallbacks(lines)

        self.assertTrue(changed)
        self.assertEqual(
            "https://leaf.highfly.dev/m3u/f1-93930303/live.m3u8",
            lines[2],
        )
        self.assertIn('x-resolver-id="f1-93930303"', lines[1])

    def test_premium_empty_leaf_is_accepted_for_both_uhd_channels(self) -> None:
        cases = (
            (
                "HighflyPremium.now-sky-sports-f1-2",
                "Sky Sports F1 UHD",
                "new-f1-93930303",
            ),
            (
                "HighflyPremium.4k-sky-sports-main-events",
                "Sky Sports Main Event UHD",
                "new-main-event-93930303",
            ),
        )
        payload = {"streams": []}
        for tvg_id, name, slug in cases:
            api_url = update_m3u.HIGHFLY_STREAM_API_TEMPLATE.format(slug=slug)
            with patch.object(
                update_m3u,
                "fetch_bytes",
                return_value=(200, json.dumps(payload).encode("utf-8"), api_url),
            ):
                with self.assertRaises(update_m3u.HighflyPremiumRequired):
                    update_m3u.fetch_highfly_stream_urls_for_slug(
                        slug,
                        premium_allowed=True,
                    )

            channel = update_m3u.Channel(
                name=name,
                url="https://leaf.highfly.dev/m3u/old/live.m3u8",
                url_line=1,
                info_line=0,
                tvg_id=tvg_id,
                display_name=name,
            )
            current = update_m3u.CheckResult(name, channel.url, False, "expired")
            with patch.dict(
                update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS,
                {tvg_id: slug},
                clear=True,
            ), patch.object(
                update_m3u,
                "fetch_bytes",
                return_value=(200, json.dumps(payload).encode("utf-8"), api_url),
            ):
                outcome = update_m3u.refresh_dynamic_channel(
                    channel,
                    lambda channel=channel: update_m3u.fresh_highfly_stream_urls(
                        channel,
                        manifest_verified=True,
                    ),
                    running_in_ci=True,
                    current_result=current,
                )

            self.assertTrue(outcome.accepted)
            self.assertTrue(outcome.changed)
            self.assertEqual(
                f"https://leaf.highfly.dev/m3u/{slug}/live.m3u8",
                outcome.resolved_url,
            )

    def test_seeded_premium_slug_survives_catalog_without_main_event(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="HighflyPremium.4k-sky-sports-main-events" x-resolver="highfly" x-resolver-id="new-main-event-93930303",Sky Sports Main Event UHD',
            "https://leaf.highfly.dev/m3u/new-main-event-93930303/live.m3u8",
        ]
        with patch.dict(
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS,
            {},
            clear=True,
        ):
            seeded = update_m3u.seed_highfly_runtime_resolver_map(lines)
            discovered = update_m3u.update_highfly_runtime_resolver_map(
                {
                    "metas": [
                        {
                            "id": "leaf:f1-3949409",
                            "name": "(FHD) : SKY SPORTS F1",
                        }
                    ]
                }
            )

            self.assertEqual(
                {
                    "HighflyPremium.4k-sky-sports-main-events": "new-main-event-93930303"
                },
                seeded,
            )
            self.assertEqual({"SkySportsF1.uk": "f1-3949409"}, discovered)
            self.assertEqual(
                "new-main-event-93930303",
                update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS[
                    "HighflyPremium.4k-sky-sports-main-events"
                ],
            )

    def test_premium_leaf_is_app_managed_after_catalog_lock(self) -> None:
        payload = {
            "streams": [
                {
                    "name": "\U0001f512 Leaf · (4K) : SKY SPORTS F1",
                    "title": "3840x2160 · Upgrade to Premium",
                    "url": "https://www.google.com/",
                }
            ]
        }
        channel = update_m3u.Channel(
            name="Sky Sports F1 UHD",
            url="https://leaf.highfly.dev/m3u/f-39388833/live.m3u8",
            url_line=0,
            info_line=0,
            tvg_id="HighflyPremium.now-sky-sports-f1-2",
            display_name="Sky Sports F1 UHD",
        )
        current = update_m3u.CheckResult(
            channel.name, channel.url, False, "HTTP 404 Not Found"
        )
        with patch.dict(
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS,
            {"HighflyPremium.now-sky-sports-f1-2": "f1-93930303"},
            clear=True,
        ), patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(
                200,
                json.dumps(payload).encode("utf-8"),
                "https://sports.highfly.dev/stream/sport/leaf:f1-93930303.json",
            ),
        ):
            outcome = update_m3u.refresh_dynamic_channel(
                channel,
                lambda: update_m3u.fresh_highfly_stream_urls(
                    channel, manifest_verified=True
                ),
                running_in_ci=True,
                current_result=current,
            )

        self.assertTrue(outcome.accepted)
        self.assertTrue(outcome.changed)
        self.assertIsNotNone(outcome.check_result)
        self.assertTrue(outcome.check_result.ok)
        self.assertEqual(
            "https://leaf.highfly.dev/m3u/f1-93930303/live.m3u8",
            outcome.resolved_url,
        )

    def test_fresh_highfly_uses_runtime_slug_and_stream_api(self) -> None:
        channel = update_m3u.Channel(
            name="Sky Sports F1",
            url="https://leaf.highfly.dev/m3u/old/live.m3u8",
            url_line=1,
            info_line=0,
            tvg_id="SkySportsF1.uk",
            display_name="Sky Sports F1",
        )
        api_url = "https://sports.highfly.dev/stream/sport/leaf:f1-3949409.json"
        response = {
            "streams": [
                {"url": "https://leaf.highfly.dev/m3u/f1-3949409/live.m3u8"}
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
            ["https://leaf.highfly.dev/m3u/f1-3949409/live.m3u8"], urls
        )
        fetch.assert_called_once()
        self.assertIn(api_url, fetch.call_args.args)

    def test_highfly_espn_channels_have_stable_contract_and_epg(self) -> None:
        expected = {
            "ESPN.us": ("ESPN", "us-espn-hd-0", "ESPN.HD.us2"),
            "ESPN2.us": ("ESPN 2", "us-33323323", "ESPN2.HD.us2"),
        }

        for tvg_id, (name, slug, epg_id) in expected.items():
            channel = update_m3u.Channel(
                name=name,
                url=f"https://leaf.highfly.dev/m3u/{slug}/live.m3u8",
                url_line=0,
                info_line=0,
                tvg_id=tvg_id,
                display_name=name,
            )
            self.assertEqual(update_m3u.resolver_engine_for(channel), "highfly")
            self.assertEqual(
                update_m3u.resolver_attributes_for(channel),
                {
                    "x-resolver": "highfly",
                    "x-resolver-id": slug,
                    "x-resolver-manifest": update_m3u.HIGHFLY_MANIFEST_URL,
                    "x-resolver-refresh": "on_play",
                },
            )
            self.assertEqual(update_m3u.HIGHFLY_RESOLVER_CHANNELS[tvg_id], slug)
            self.assertEqual(
                update_m3u.EPG_PROGRAMME_SOURCES[tvg_id], ("us2", epg_id)
            )

    def test_runtime_catalog_refresh_is_in_memory_only(self) -> None:
        payload = {
            "metas": [
                {"id": "leaf:ten-3930030", "name": "Sky Sports Tennis"}
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

        self.assertEqual({"SkySportsTennis.uk": "ten-3930030"}, mapping)
        self.assertEqual(
            "ten-3930030",
            update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS["SkySportsTennis.uk"],
        )

if __name__ == "__main__":
    unittest.main()
