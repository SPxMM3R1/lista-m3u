import unittest

import update_m3u


def extinf(tvg_id: str, name: str, group: str = "legacy") -> str:
    return (
        f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" '
        f'group-title="{group}",{name}'
    )


class PlaylistOrderTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
