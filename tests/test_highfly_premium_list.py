import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_m3u


class HighflyPremiumListTest(unittest.TestCase):
    def test_only_leaf_slugs_are_rendered_and_events_are_ignored(self) -> None:
        payload = {
            "metas": [
                {
                    "id": "streamed:match-123",
                    "name": "Temporary event",
                    "poster": "https://cdn.highfly.dev/private/event.webp?token=secret",
                },
                {
                    "id": "leaf:now-sky-sports-f1-free",
                    "name": "(FHD) SKY SPORTS F1 ᴿᴬᵂ",
                    "poster": "https://cdn.highfly.dev/leaf_posters/f1.webp",
                },
                {"id": "javascript:unsafe", "name": "Unsafe"},
            ]
        }

        entries = update_m3u.parse_highfly_premium_stable_catalog(
            json.dumps(payload).encode("utf-8")
        )
        content = update_m3u.render_highfly_premium_stable_playlist(entries)

        self.assertEqual(["now-sky-sports-f1-free"], [item["slug"] for item in entries])
        self.assertIn('x-resolver-id="now-sky-sports-f1-free"', content)
        self.assertIn('x-highfly-premium-id="leaf:now-sky-sports-f1-free"', content)
        self.assertIn('tvg-id="SkySportsF1.uk"', content)
        self.assertIn("https://leaf.highfly.dev/m3u/now-sky-sports-f1-free/live.m3u8", content)
        self.assertNotIn("streamed:", content)
        self.assertNotIn("access_token", content)
        self.assertNotIn("token=secret", content)
        self.assertNotIn("cdn.highfly.dev/leaf_posters", content)
        self.assertEqual(1, update_m3u.validate_highfly_premium_stable_playlist(
            content.splitlines()
        ))

    def test_catalog_order_prefers_historical_slots_then_new_channels(self) -> None:
        payload = {
            "metas": [
                {"id": "leaf:us-espn-hd", "name": "ESPN"},
                {"id": "leaf:future-channel", "name": "Future"},
                {"id": "leaf:now-sky-sports-tennis", "name": "Tennis"},
                {"id": "leaf:now-sky-sports-f1-free", "name": "F1"},
            ]
        }

        entries = update_m3u.parse_highfly_premium_stable_catalog(payload)

        self.assertEqual(
            [
                "now-sky-sports-f1-free",
                "now-sky-sports-tennis",
                "us-espn-hd",
                "future-channel",
            ],
            [item["slug"] for item in entries],
        )

    def test_sync_preserves_previous_file_on_catalog_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "3.m3u"
            previous = "#EXTM3U\n# old stable list\n"
            path.write_text(previous, encoding="utf-8")
            with patch.object(
                update_m3u,
                "fetch_highfly_premium_stable_catalog",
                side_effect=RuntimeError("provider unavailable"),
            ):
                self.assertFalse(
                    update_m3u.sync_highfly_premium_stable_playlist(path)
                )
            self.assertEqual(previous, path.read_text(encoding="utf-8"))

    def test_sync_writes_validated_public_list_without_a_token(self) -> None:
        entries = [
            {
                "slug": "now-sky-sports-f1-free",
                "tvg_id": "SkySportsF1.uk",
                "name": "Sky Sports F1",
                "country": "GB",
                "logo": "sky-sports-f1.png",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "3.m3u"
            with patch.object(
                update_m3u,
                "fetch_highfly_premium_stable_catalog",
                return_value=entries,
            ):
                self.assertTrue(
                    update_m3u.sync_highfly_premium_stable_playlist(path)
                )
            content = path.read_text(encoding="utf-8")
            self.assertEqual(
                1,
                update_m3u.validate_highfly_premium_stable_playlist(
                    content.splitlines(), path=path
                ),
            )
            self.assertNotIn("access_token", content)
            self.assertNotIn("signature", content)
            self.assertIn(
                f'x-resolver-manifest="{update_m3u.HIGHFLY_PREMIUM_STABLE_MANIFEST_URL}"',
                content,
            )
            self.assertIn('x-resolver-refresh="on_play"', content)

    def test_list3_rejects_non_final_manifest(self) -> None:
        entries = [
            {
                "slug": "now-sky-sports-f1-free",
                "tvg_id": "SkySportsF1.uk",
                "name": "Sky Sports F1",
                "country": "GB",
                "logo": "sky-sports-f1.png",
            }
        ]
        content = update_m3u.render_highfly_premium_stable_playlist(entries)
        with self.assertRaises(ValueError):
            update_m3u.validate_highfly_premium_stable_playlist(
                content.replace(
                    update_m3u.HIGHFLY_PREMIUM_STABLE_MANIFEST_URL,
                    "https://sports.highfly.dev/configure",
                ).splitlines()
            )

    def test_new_list3_channels_use_real_epg_mappings(self) -> None:
        self.assertEqual(
            ("uk1", "SkySpCricket.HD.uk"),
            update_m3u.EPG_PROGRAMME_SOURCES[
                "HighflyPremium.now-sky-sports-cricket"
            ],
        )
        self.assertEqual(
            ("uk1", "SkySp.Golf.HD.uk"),
            update_m3u.EPG_PROGRAMME_SOURCES[
                "HighflyPremium.now-sky-sports-golf"
            ],
        )
        self.assertEqual(
            ("us2", "Marquee.Sports.Network.HD.us2"),
            update_m3u.EPG_PROGRAMME_SOURCES[
                "HighflyPremium.us-marquee-sports-network-hd"
            ],
        )
        self.assertEqual(
            ("au1", "FoxFooty.au"),
            update_m3u.EPG_PROGRAMME_SOURCES[
                "HighflyPremium.au-fox-sports-504-hd"
            ],
        )
        self.assertEqual(
            ("au1", "FoxLeague.au"),
            update_m3u.EPG_PROGRAMME_SOURCES[
                "HighflyPremium.au-fox-sports-502-hd"
            ],
        )

    def test_uhd_sky_channels_use_dedicated_logo_variants(self) -> None:
        self.assertEqual(
            "sky-sports-main-event-uhd.png",
            update_m3u.HIGHFLY_PREMIUM_STABLE_OVERRIDES[
                "4k-sky-sports-main-events"
            ]["logo"],
        )
        self.assertEqual(
            "sky-sports-f1-uhd.png",
            update_m3u.HIGHFLY_PREMIUM_STABLE_OVERRIDES[
                "now-sky-sports-f1-2"
            ]["logo"],
        )
        content = update_m3u.render_highfly_premium_stable_playlist(
            [
                {
                    "slug": "4k-sky-sports-main-events",
                    "tvg_id": "HighflyPremium.4k-sky-sports-main-events",
                    "name": "Sky Sports Main Event UHD",
                    "country": "GB",
                    "logo": "sky-sports-main-event-uhd.png",
                },
                {
                    "slug": "now-sky-sports-f1-2",
                    "tvg_id": "HighflyPremium.now-sky-sports-f1-2",
                    "name": "Sky Sports F1 UHD",
                    "country": "GB",
                    "logo": "sky-sports-f1-uhd.png",
                },
            ]
        )
        self.assertIn("/logos/sky-sports-main-event-uhd.png", content)
        self.assertIn("/logos/sky-sports-f1-uhd.png", content)

    def test_rally_official_epg_reads_only_linear_cards(self) -> None:
        cards = []
        for index in range(25):
            start_day = 3 + index // 24
            stop_day = 3 + (index + 1) // 24
            start = f"2026-09-{start_day:02d}T{(10 + index) % 24:02d}:00:00.000Z"
            stop = f"2026-09-{stop_day:02d}T{(11 + index) % 24:02d}:00:00.000Z"
            cards.append(
                (
                    '{\\"title\\":\\"Rally programme '
                    + str(index)
                    + f'\\",\\"start_time\\":\\"{start}\\",'
                    + f'\\"end_time\\":\\"{stop}\\"}}'
                )
            )
        sample = (
            '\\"title\\":\\"Rally TV\\",\\"type\\":\\"epg\\",\\"cards\\":['
            + ",".join(cards)
            + '],\\"title\\":\\"Best of Highlights\\",\\"cards\\":[]'
        )
        channels = update_m3u.parse_channels(
            Path(update_m3u.HIGHFLY_PREMIUM_STABLE_PLAYLIST)
            .read_text(encoding="utf-8-sig")
            .splitlines()
        )
        with patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(200, sample.encode("utf-8"), update_m3u.RALLY_TV_OFFICIAL_EPG_URL),
        ):
            data, error = update_m3u.fetch_rally_tv_official_epg(
                channels,
                update_m3u.datetime(2026, 9, 3, 9, tzinfo=update_m3u.timezone.utc),
            )
        self.assertIsNone(error)
        self.assertIsNotNone(data)
        root = update_m3u.ET.fromstring(data)
        programmes = root.findall("programme")
        self.assertGreaterEqual(len(programmes), 20)
        self.assertTrue(all(p.get("channel") == "RallyTV.us" for p in programmes))


if __name__ == "__main__":
    unittest.main()
