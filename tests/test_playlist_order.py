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
    def test_official_short_aliases_match_canonical_playlists(self) -> None:
        for canonical, alias in update_m3u.SHORT_PLAYLIST_ALIASES:
            self.assertTrue(canonical.is_file(), canonical)
            self.assertTrue(alias.is_file(), alias)
            self.assertEqual(alias.read_bytes(), canonical.read_bytes())

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
        mismatched_resolver_state = {
            "channels": {
                "ESPN.us": {
                    "resolver": "tvvoo",
                    "last_resolver_validated_at": "2026-08-29T11:50:00Z",
                    "resolver_url_hash": update_m3u.resolver_url_fingerprint(
                        channel.url
                    ),
                }
            }
        }
        self.assertFalse(
            update_m3u.dynamic_validation_is_fresh(
                channel, current, mismatched_resolver_state, now=now
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

    def test_permanent_channel_exclusions_keep_unrelated_poland_channels(self) -> None:
        lines = ["#EXTM3U"]
        excluded = [
            ("bloomberg.channel", "Bloomberg TV Italia"),
            ("cnn.channel", "CNN Polonia"),
            ("trt.channel", "TRT World Turquía"),
            ("dazn-fast.channel", "DAZN FAST+"),
            ("rmc.channel", "RMC Sport 3 Francia"),
            ("turkey.channel", "Eurosport 1 Turquía"),
            ("balkan.channel", "Arena Sport 1 Balcanes"),
        ]
        retained = [
            ("bbc-earth.channel", "BBC Earth Polonia"),
            ("eurosport.channel", "Eurosport 3 Polonia"),
        ]
        for tvg_id, name in excluded + retained:
            lines.extend((extinf(tvg_id, name), f"https://example.invalid/{tvg_id}.m3u8"))

        removed = update_m3u.remove_permanently_removed_channels(lines)

        self.assertEqual(removed, [name for _, name in excluded])
        self.assertEqual(
            [channel.name for channel in update_m3u.parse_channels(lines)],
            [name for _, name in retained],
        )

    def test_permanent_channel_exclusions_remove_reuters_and_stingray_djazz(self) -> None:
        lines = ["#EXTM3U"]
        excluded = [
            ("ReutersTV.us", "Reuters"),
            ("Vavoo.nl.STINGRAYDJAZZ@TvVoo", "Stingray DJAZZ Países Bajos"),
            ("MTVClassic.us", "MTV Classic"),
        ]
        retained = [("StingrayClassica.ca", "Stingray Classica")]
        for tvg_id, name in excluded + retained:
            lines.extend((extinf(tvg_id, name), f"https://example.invalid/{tvg_id}.m3u8"))

        removed = update_m3u.remove_permanently_removed_channels(lines)

        self.assertEqual(removed, [name for _, name in excluded])
        self.assertEqual(
            [channel.name for channel in update_m3u.parse_channels(lines)],
            [name for _, name in retained],
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
            extinf("13Cultura.cl@DPS", "13 Cultura", "Misceláneos"),
            "https://example.invalid/13cultura.m3u8",
            extinf("1437", "TVN3", "Misceláneos"),
            "https://example.invalid/tvn3.m3u8",
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
            [
                "24 Horas",
                "NTV",
                "TVN3",
                "13C",
                "13 Cultura",
                "RWND",
                "BBC News",
            ],
        )
        self.assertEqual(
            [channel.group for channel in channels],
            [
                "Noticias nacionales",
                "Misceláneos",
                "Misceláneos",
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

    def test_nhk_and_arirang_stay_adjacent_in_international_news(self) -> None:
        lines = [
            "#EXTM3U",
            extinf(
                "NHKWorldJapan.jp",
                "NHK World Japan",
                "Noticias internacionales",
            ),
            "https://example.invalid/nhk.m3u8",
            extinf("news-int.channel", "BBC News", "Noticias internacionales"),
            "https://example.invalid/bbc.m3u8",
            extinf("ArirangTV.kr", "Arirang TV", "Misceláneos"),
            "https://example.invalid/arirang.m3u8",
            extinf(
                "AlJazeera.qa",
                "Al Jazeera English",
                "Noticias internacionales",
            ),
            "https://example.invalid/aljazeera.m3u8",
        ]

        update_m3u.order_channels_by_content(lines)

        ordered = update_m3u.parse_channels(lines)
        self.assertEqual(
            [channel.tvg_id for channel in ordered],
            [
                "NHKWorldJapan.jp",
                "ArirangTV.kr",
                "news-int.channel",
                "AlJazeera.qa",
            ],
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

    def test_selected_dynamic_channels_are_published_in_main(self) -> None:
        selected = [
            update_m3u.Channel(
                name="Sky Sports F1",
                url="https://leaf.highfly.dev/m3u/now-sky-sports-f1-free/live.m3u8",
                url_line=0,
                tvg_id="SkySportsF1.uk",
            ),
            update_m3u.Channel(
                name="Sky Sports Tennis",
                url="https://leaf.highfly.dev/m3u/now-sky-sports-tennis/live.m3u8",
                url_line=1,
                tvg_id="SkySportsTennis.uk",
            ),
            update_m3u.Channel(
                name="ESPN",
                url="https://leaf.highfly.dev/m3u/us-espn-hd/live.m3u8",
                url_line=2,
                tvg_id="ESPN.us",
            ),
            update_m3u.Channel(
                name="Sky Sports Main Event",
                url="https://example.invalid/sky-main-event.m3u8",
                url_line=3,
                tvg_id="SkySportsMainEvent.uk@TvVoo",
            ),
            update_m3u.Channel(
                name="Eurosport 1",
                url="https://example.invalid/eurosport-1.m3u8",
                url_line=4,
                tvg_id="Eurosport1.fr@TvVoo",
            ),
            update_m3u.Channel(
                name="DAZN 3 España",
                url="https://example.invalid/dazn-3-es.m3u8",
                url_line=5,
                tvg_id="DAZN3.es@TvVoo",
            ),
        ]

        self.assertEqual(
            [update_m3u.playlist_key_for(item) for item in selected],
            ["main", "main", "external", "main", "main", "main"],
        )

    def test_all_catalogue_f1_variants_are_assigned_to_main(self) -> None:
        expected_ids = set(update_m3u.F1_CHANNEL_ORDER)
        self.assertEqual(expected_ids, update_m3u.F1_CHANNEL_IDS)
        channels = [
            update_m3u.Channel(
                name=channel_id,
                url="https://example.invalid/f1.m3u8",
                url_line=index,
                tvg_id=channel_id,
            )
            for index, channel_id in enumerate(update_m3u.F1_CHANNEL_ORDER)
        ]

        self.assertTrue(
            all(update_m3u.playlist_key_for(item) == "main" for item in channels)
        )

    def test_tvvoo_italian_f1_variant_is_restored_with_stable_contract(self) -> None:
        channel_id = "Vavoo.it.SKYSPORTF1@TvVoo"

        self.assertNotIn(channel_id, update_m3u.PERMANENTLY_REMOVED_CHANNEL_IDS)
        self.assertIn(channel_id, update_m3u.F1_CHANNEL_ORDER)
        self.assertEqual(
            update_m3u.TVVOO_STREAM_RESOLVER_IDS["Sky Sport F1 Italia"],
            ("vavoo_SKY%20SPORT%20F1%7Cgroup%3Ait",),
        )
        self.assertEqual(
            update_m3u.EPG_PROGRAMME_SOURCES[channel_id],
            ("it1", "Sky.Sport.F1.it"),
        )

    def test_highfly_f1_is_kept_when_health_check_fails(self) -> None:
        lines = [
            "#EXTM3U",
            "# Deportes",
            extinf("SkySportsF1.uk", "Sky Sports F1", "Deportes"),
            "https://leaf.highfly.dev/m3u/now-sky-sports-f1-free/live.m3u8",
        ]
        channel = update_m3u.parse_channels(lines)[0]

        self.assertTrue(update_m3u.is_protected_main_channel(channel))
        filtered = update_m3u.filter_playlist_to_working_channels(
            lines, [channel], set()
        )
        self.assertEqual(
            [item.tvg_id for item in update_m3u.parse_channels(filtered)],
            ["SkySportsF1.uk"],
        )

    def test_requested_sports_families_keep_order_in_one_contiguous_block(
        self,
    ) -> None:
        lines = ["#EXTM3U"]
        for index, channel_id in reversed(
            list(enumerate(update_m3u.SPORTS_CHANNEL_ORDER))
        ):
            lines.extend(
                (
                    extinf(channel_id, channel_id, "Deportes"),
                    f"https://example.invalid/f1-{index}.m3u8",
                )
            )
        lines.extend(
            (
                extinf("other.sport", "Otro deporte", "Deportes"),
                "https://example.invalid/other.m3u8",
            )
        )

        update_m3u.order_channels_by_content(lines)
        ordered_ids = [
            channel.tvg_id for channel in update_m3u.parse_channels(lines)
        ]

        sports_positions = [
            ordered_ids.index(channel_id)
            for channel_id in update_m3u.SPORTS_CHANNEL_ORDER
        ]
        self.assertEqual(
            sports_positions,
            list(range(min(sports_positions), max(sports_positions) + 1)),
        )
        self.assertEqual(
            ordered_ids[min(sports_positions) : max(sports_positions) + 1],
            list(update_m3u.SPORTS_CHANNEL_ORDER),
        )
        self.assertEqual(
            ordered_ids[:2],
            ["SkySportsF1.uk", "SkySportsTennis.uk"],
        )
        self.assertEqual(
            [channel_id for channel_id in ordered_ids if channel_id in update_m3u.F1_CHANNEL_IDS],
            list(update_m3u.F1_CHANNEL_ORDER),
        )

    def test_removed_direct_sky_probe_cannot_reenter_public_catalogue(self) -> None:
        lines = [
            "#EXTM3U",
            "# Deportes",
            extinf(
                "SkySportsF1.uk@Direct",
                "Sky Sports F1 UK (Directo)",
                "Deportes",
            ),
            "http://example.invalid/sky-f1.m3u8",
            extinf("ESPN.us", "ESPN", "Deportes"),
            "https://example.invalid/espn.m3u8",
        ]
        removed = update_m3u.remove_permanently_removed_channels(lines)

        self.assertEqual(
            removed,
            ["Sky Sports F1 UK (Directo)"],
        )
        self.assertEqual(
            [item.name for item in update_m3u.parse_channels(lines)],
            ["ESPN"],
        )
        self.assertFalse(
            update_m3u.is_direct_probe(
                update_m3u.Channel(
                    name="Sky Sports F1 UK (Directo)",
                    url="https://example.invalid/sky-f1.m3u8",
                    url_line=0,
                    tvg_id="SkySportsF1.uk@Direct",
                )
            )
        )

    def test_external_filter_does_not_leak_protected_main_f1(self) -> None:
        lines = [
            "#EXTM3U",
            "# Deportes",
            extinf("SkySportsF1.uk", "Sky Sports F1", "Deportes"),
            "https://leaf.highfly.dev/m3u/now-sky-sports-f1-free/live.m3u8",
            extinf("ESPN.us", "ESPN", "Deportes"),
            "https://example.invalid/espn.m3u8",
        ]
        channels = update_m3u.parse_channels(lines)

        external = update_m3u.filter_playlist_to_working_channels(
            lines,
            channels,
            {"ESPN"},
            preserve_protected_main=False,
        )
        self.assertEqual(
            [item.name for item in update_m3u.parse_channels(external)], ["ESPN"]
        )

    def test_report_marks_failed_highfly_f1_as_protected_fallback(self) -> None:
        channel = update_m3u.Channel(
            name="Sky Sports F1",
            url="https://leaf.highfly.dev/m3u/now-sky-sports-f1-free/live.m3u8",
            url_line=0,
            tvg_id="SkySportsF1.uk",
            display_name="Sky Sports F1",
        )
        result = update_m3u.CheckResult(channel.name, channel.url, False, "down")
        logo = update_m3u.LogoResult(channel.name, "", True, "ok")

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            with patch.object(
                update_m3u, "HEALTH_STATE_PATH", temporary / "health.json"
            ), patch.object(
                update_m3u, "REPORT_PATH", temporary / "report.json"
            ):
                report = update_m3u.write_report(
                    [channel],
                    [result],
                    False,
                    [logo],
                    epg_status={"ok": True},
                    main_epg_status={
                        "ok": True,
                        "required_channels": 1,
                        "guide_types": {channel.tvg_id: "real"},
                    },
                )

        entry = report["channels"][0]
        self.assertTrue(report["playlists"]["main"]["publication_ready"])
        self.assertTrue(entry["published"])
        self.assertEqual(entry["publication_action"], "protected_fallback")

    def test_sky_tennis_uses_highfly_after_slug_returns(self) -> None:
        channel = update_m3u.Channel(
            name="Sky Sports Tennis",
            url="https://leaf.highfly.dev/m3u/now-sky-sports-tennis/live.m3u8",
            url_line=0,
            tvg_id="SkySportsTennis.uk",
        )

        self.assertEqual(update_m3u.resolver_engine_for(channel), "highfly")
        self.assertEqual(
            update_m3u.resolver_attributes_for(channel),
            {
                "x-resolver": "highfly",
                "x-resolver-id": "now-sky-sports-tennis",
                "x-resolver-manifest": update_m3u.HIGHFLY_MANIFEST_URL,
                "x-resolver-refresh": "on_play",
            },
        )
        self.assertEqual(update_m3u.playlist_key_for(channel), "main")
        self.assertEqual(
            update_m3u.HIGHFLY_RESOLVER_CHANNELS["SkySportsTennis.uk"],
            "now-sky-sports-tennis",
        )

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
