import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import update_m3u


def extinf(tvg_id: str, name: str, group: str = "legacy") -> str:
    return (
        f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" '
        f'group-title="{group}",{name}'
    )


class PlaylistOrderTests(unittest.TestCase):
    def test_dynamic_validation_cache_is_short_lived_and_url_bound(self) -> None:
        channel = update_m3u.Channel(
            name="ESPN",
            url="https://leaf.highfly.dev/m3u/us-espn-hd/live.m3u8",
            url_line=0,
            tvg_id="ESPN.us",
            display_name="ESPN",
        )
        now = datetime(2026, 8, 29, 12, tzinfo=timezone.utc)
        state = {
            "channels": {
                "ESPN.us": {
                    "last_resolver_validated_at": "2026-08-29T11:50:00Z",
                    "resolver_url_hash": update_m3u.resolver_url_fingerprint(
                        channel.url
                    ),
                }
            }
        }
        current = update_m3u.CheckResult(channel.name, channel.url, True, "ok")

        self.assertTrue(
            update_m3u.dynamic_validation_is_fresh(
                channel, current, state, now=now
            )
        )
        changed_url = channel.url + "?changed=1"
        changed_channel = update_m3u.Channel(
            channel.name,
            changed_url,
            channel.url_line,
            tvg_id=channel.tvg_id,
            display_name=channel.display_name,
        )
        changed_result = update_m3u.CheckResult(
            changed_channel.name, changed_channel.url, True, "ok"
        )
        self.assertFalse(
            update_m3u.dynamic_validation_is_fresh(
                changed_channel, changed_result, state, now=now
            )
        )
        expired_state = {
            "channels": {
                "ESPN.us": {
                    "last_resolver_validated_at": "2026-08-29T11:00:00Z",
                    "resolver_url_hash": update_m3u.resolver_url_fingerprint(
                        channel.url
                    ),
                }
            }
        }
        self.assertFalse(
            update_m3u.dynamic_validation_is_fresh(
                channel, current, expired_state, now=now
            )
        )

    def test_provider_policies_keep_parallel_validation_bounded(self) -> None:
        tvvoo = update_m3u.Channel(
            name="Sky Sports Arena",
            url="https://example.invalid/tvvoo.m3u8",
            url_line=0,
            tvg_id="SkySportsArena.uk@TvVoo",
        )
        highfly = update_m3u.Channel(
            name="ESPN",
            url="https://leaf.highfly.dev/m3u/us-espn-hd/live.m3u8",
            url_line=0,
            tvg_id="ESPN.us",
        )

        self.assertEqual(
            update_m3u.channel_check_policy(tvvoo).playlist_timeout, 18
        )
        self.assertEqual(
            update_m3u.channel_check_policy(highfly).segment_timeout, 14
        )
        self.assertEqual(update_m3u.channel_check_policy(tvvoo).workers, 6)
        self.assertEqual(update_m3u.channel_check_policy(highfly).workers, 4)

    def test_dynamic_refresh_outcome_does_not_mutate_playlist_from_worker(self) -> None:
        channel = update_m3u.Channel(
            name="ESPN",
            url="https://leaf.highfly.dev/m3u/us-espn-hd/live.m3u8",
            url_line=1,
            tvg_id="ESPN.us",
        )
        current = update_m3u.CheckResult(channel.name, channel.url, False, "expired")
        replacement = "https://leaf.highfly.dev/m3u/us-espn-hd/live-v2.m3u8"
        lines = ["#EXTM3U", channel.url]
        with patch.object(
            update_m3u,
            "check_channel",
            return_value=update_m3u.CheckResult(
                channel.name, replacement, True, "playlist HLS valida"
            ),
        ):
            outcome = update_m3u.refresh_dynamic_channel(
                channel,
                lambda: replacement,
                running_in_ci=False,
                current_result=current,
            )

        self.assertTrue(outcome.accepted)
        self.assertTrue(outcome.changed)
        self.assertEqual(outcome.resolved_url, replacement)
        self.assertEqual(lines[1], channel.url)

    def test_tv_chile_belongs_to_international_news_group(self) -> None:
        tv_chile = update_m3u.Channel(
            name="TV Chile",
            url="https://example.invalid/tv-chile.m3u8",
            url_line=0,
            tvg_id="TVChile.cl",
            display_name="TV Chile",
        )

        self.assertEqual(
            update_m3u.content_category_for(tv_chile), "Noticias internacionales"
        )

    def test_catalogue_is_ordered_and_public_filter_keeps_the_same_sequence(self) -> None:
        lines = [
            '#EXTM3U x-tvg-url="https://example.invalid/epg.xml"',
            "# layout anterior",
            extinf("music.channel", "XITE Nuevo Latino"),
            "https://example.invalid/music.m3u8",
            extinf("misc.channel", "BBC Earth FAST"),
            "https://example.invalid/misc.m3u8",
            extinf("sport.channel", "Sky Sports F1"),
            "https://example.invalid/sport.m3u8",
            extinf("nba.channel", "NBA TV Turquía"),
            "https://example.invalid/nba.m3u8",
            extinf("news-int.channel", "BBC News"),
            "https://example.invalid/news-int.m3u8",
            extinf("0201", "24 Horas"),
            "https://example.invalid/national-news.m3u8",
            extinf("0104", "TVN"),
            "https://example.invalid/national.m3u8",
        ]

        self.assertTrue(update_m3u.order_channels_by_content(lines))
        channels = update_m3u.parse_channels(lines)
        self.assertEqual(
            [channel.name for channel in channels],
            [
                "TVN",
                "24 Horas",
                "BBC News",
                "Sky Sports F1",
                "NBA TV Turquía",
                "XITE Nuevo Latino",
                "BBC Earth FAST",
            ],
        )
        self.assertEqual(
            [channel.group for channel in channels],
            [
                "Nacionales",
                "Noticias nacionales",
                "Noticias internacionales",
                "Deportes",
                "Deportes",
                "Música",
                "Misceláneos",
            ],
        )

        public_lines = update_m3u.filter_playlist_to_working_channels(
            lines,
            channels,
            {
                "TVN",
                "BBC News",
                "XITE Nuevo Latino",
                "BBC Earth FAST",
            },
        )
        public_channels = update_m3u.parse_channels(public_lines)
        self.assertEqual(
            [channel.name for channel in public_channels],
            ["TVN", "BBC News", "XITE Nuevo Latino", "BBC Earth FAST"],
        )

    def test_resolver_attributes_survive_group_normalization(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="ESPN.us" group-title="PRUEBA" '
            'x-resolver="highfly" x-resolver-id="us-espn-hd",ESPN',
            "https://example.invalid/espn.m3u8",
        ]

        update_m3u.order_channels_by_content(lines)

        info_line = next(line for line in lines if line.startswith("#EXTINF:"))
        self.assertIn('group-title="Deportes"', info_line)
        self.assertIn('x-resolver="highfly"', info_line)
        self.assertIn('x-resolver-id="us-espn-hd"', info_line)

    def test_selected_misc_channels_follow_national_news(self) -> None:
        lines = [
            "#EXTM3U",
            extinf("RewindTV.cl@SD", "RWND", "Misceláneos"),
            "https://example.invalid/rewind.m3u8",
            extinf("news-int.channel", "BBC News", "Noticias internacionales"),
            "https://example.invalid/news.m3u8",
            extinf("13C.cl@SD", "13C", "Misceláneos"),
            "https://example.invalid/13c.m3u8",
            extinf("45", "NTV", "Misceláneos"),
            "https://example.invalid/ntv.m3u8",
            extinf("0201", "24 Horas", "Noticias nacionales"),
            "https://example.invalid/24horas.m3u8",
        ]

        update_m3u.order_channels_by_content(lines)

        channels = update_m3u.parse_channels(lines)
        self.assertEqual(
            [channel.name for channel in channels],
            ["24 Horas", "NTV", "13C", "RWND", "BBC News"],
        )
        self.assertEqual(
            [channel.group for channel in channels],
            [
                "Noticias nacionales",
                "Misceláneos",
                "Misceláneos",
                "Misceláneos",
                "Noticias internacionales",
            ],
        )
        self.assertIn("# Despues de noticias nacionales", lines)

    def test_dw_channels_stay_adjacent_in_international_news(self) -> None:
        lines = [
            "#EXTM3U",
            extinf("DWEnglish.de", "DW English", "Noticias internacionales"),
            "https://example.invalid/dw-en.m3u8",
            extinf("news-int.channel", "BBC News", "Noticias internacionales"),
            "https://example.invalid/bbc.m3u8",
            extinf("DW.de", "DW Español", "Noticias internacionales"),
            "https://example.invalid/dw-es.m3u8",
        ]

        update_m3u.order_channels_by_content(lines)

        self.assertEqual(
            [channel.name for channel in update_m3u.parse_channels(lines)],
            ["DW Español", "DW English", "BBC News"],
        )

    def test_public_lists_split_by_resolver_without_empty_groups(self) -> None:
        lines = [
            "#EXTM3U",
            "# Nacionales",
            extinf("0104", "TVN", "Nacionales"),
            "https://example.invalid/tvn.m3u8",
            "# Deportes",
            extinf("ESPN.us", "ESPN", "Deportes"),
            "https://example.invalid/espn.m3u8",
        ]
        channels = update_m3u.parse_channels(lines)

        self.assertEqual(
            [update_m3u.playlist_key_for(item) for item in channels],
            ["main", "external"],
        )
        principal = update_m3u.filter_playlist_to_working_channels(
            lines, channels, {"TVN"}
        )
        externa = update_m3u.filter_playlist_to_working_channels(
            lines, channels, {"ESPN"}
        )
        self.assertEqual(
            [item.name for item in update_m3u.parse_channels(principal)], ["TVN"]
        )
        self.assertEqual(
            [item.name for item in update_m3u.parse_channels(externa)], ["ESPN"]
        )
        self.assertNotIn("# Deportes", principal)
        self.assertNotIn("# Nacionales", externa)

    def test_external_list_can_publish_when_principal_epg_is_held(self) -> None:
        principal = update_m3u.Channel(
            name="TVN",
            url="https://example.invalid/tvn.m3u8",
            url_line=0,
            tvg_id="0104",
            display_name="TVN",
        )
        external = update_m3u.Channel(
            name="ESPN",
            url="https://example.invalid/espn.m3u8",
            url_line=1,
            tvg_id="ESPN.us",
            display_name="ESPN",
        )
        results = [
            update_m3u.CheckResult(item.name, item.url, True, "ok")
            for item in (principal, external)
        ]
        logos = [
            update_m3u.LogoResult(item.name, "", True, "ok")
            for item in (principal, external)
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            with patch.object(
                update_m3u, "HEALTH_STATE_PATH", temporary / "health.json"
            ), patch.object(
                update_m3u, "REPORT_PATH", temporary / "report.json"
            ):
                report = update_m3u.write_report(
                    [principal, external],
                    results,
                    False,
                    logos,
                    epg_status={"ok": False},
                    main_epg_status={"ok": False, "required_channels": 1},
                )
                health_state = json.loads(
                    (temporary / "health.json").read_text(encoding="utf-8")
                )

        self.assertFalse(report["playlists"]["main"]["publication_ready"])
        self.assertTrue(report["playlists"]["external"]["publication_ready"])
        self.assertEqual(
            report["playlists"]["main"]["hold_reason"], "epg_incomplete"
        )
        actions = {item["name"]: item["publication_action"] for item in report["channels"]}
        self.assertEqual(actions["TVN"], "held_missing_epg")
        self.assertEqual(actions["ESPN"], "published")
        espn_state = health_state["channels"]["ESPN.us"]
        self.assertEqual(
            espn_state["resolver_url_hash"],
            update_m3u.resolver_url_fingerprint(external.url),
        )
        self.assertTrue(espn_state["last_resolver_validated_at"])
        self.assertNotIn(external.url, json.dumps(health_state))


if __name__ == "__main__":
    unittest.main()
