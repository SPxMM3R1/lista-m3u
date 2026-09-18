import unittest
from pathlib import Path
import tempfile

import update_m3u

from targeted_update import (
    apply_playlist_text_updates,
    merge_epg_xml,
    reorder_playlist_lines,
)


def xml(*programmes: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<tv data-generated-at="2026-09-18T12:00:00+00:00">'
        '<channel id="one"><display-name>One</display-name></channel>'
        '<channel id="two"><display-name>Two</display-name></channel>'
        + "".join(programmes)
        + "</tv>\n"
    ).encode()


class TargetedUpdateTest(unittest.TestCase):
    def test_epg_override_is_validated_and_applied_without_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "epg-overrides.json"
            path.write_text(
                '{"channels": {"temporary": {"source": "sky-oficial", '
                '"source_id": "4091"}}}',
                encoding="utf-8",
            )
            previous = update_m3u.EPG_PROGRAMME_SOURCES.get("temporary")
            try:
                applied = update_m3u.apply_epg_overrides(path)
                self.assertEqual(("sky-oficial", "4091"), applied["temporary"])
            finally:
                if previous is None:
                    update_m3u.EPG_PROGRAMME_SOURCES.pop("temporary", None)
                else:
                    update_m3u.EPG_PROGRAMME_SOURCES["temporary"] = previous

    def test_reorder_keeps_records_and_rebuilds_group_headers(self) -> None:
        lines = [
            "#EXTM3U",
            "# News",
            '#EXTINF:-1 tvg-id="one" group-title="News",One',
            "https://example.test/one.m3u8",
            "# Sports",
            '#EXTINF:-1 tvg-id="two" group-title="Sports",Two',
            "https://example.test/two.m3u8",
        ]

        reordered = reorder_playlist_lines(lines, ["two", "one"])

        self.assertLess(
            reordered.index('#EXTINF:-1 tvg-id="two" group-title="Sports",Two'),
            reordered.index('#EXTINF:-1 tvg-id="one" group-title="News",One'),
        )
        self.assertIn("# Sports", reordered)
        self.assertIn("# News", reordered)

    def test_stream_update_changes_only_requested_record(self) -> None:
        playlist = """#EXTM3U
#EXTINF:-1 tvg-id="one",One
https://example.test/one.m3u8
#EXTINF:-1 tvg-id="two",Two
https://example.test/two.m3u8
"""

        updated = apply_playlist_text_updates(
            {"channel-catalog.m3u": playlist},
            {"two": "https://example.test/two-new.m3u8"},
            {},
        )["channel-catalog.m3u"]

        self.assertIn("https://example.test/one.m3u8", updated)
        self.assertIn("https://example.test/two-new.m3u8", updated)
        self.assertNotIn("https://example.test/two.m3u8", updated)

    def test_merge_replaces_only_requested_channel(self) -> None:
        existing = xml(
            '<programme channel="one" start="20260918100000 +0000" stop="20260918110000 +0000"><title>Old one</title></programme>',
            '<programme channel="two" start="20260918100000 +0000" stop="20260918110000 +0000"><title>Keep two</title></programme>',
        )
        replacement = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<tv data-generated-at="2026-09-18T13:00:00+00:00">'
            '<channel id="one"><display-name>One fresh</display-name></channel>'
            '<programme channel="one" start="20260918100000 +0000" stop="20260918110000 +0000"><title>New one</title></programme>'
            '</tv>\n'
        ).encode()

        merged = merge_epg_xml(existing, replacement, {"one"})
        text = merged.decode()

        self.assertIn("One fresh", text)
        self.assertIn("New one", text)
        self.assertIn("Keep two", text)
        self.assertNotIn("Old one", text)
        self.assertIn('data-generated-at="2026-09-18T13:00:00+00:00"', text)

    def test_merge_fails_when_target_has_no_replacement_channel(self) -> None:
        existing = xml(
            '<programme channel="one" start="20260918100000 +0000" stop="20260918110000 +0000"><title>Old one</title></programme>'
        )
        replacement = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<tv><channel id="two"><display-name>Two</display-name></channel>'
            '<programme channel="two" start="20260918100000 +0000" stop="20260918110000 +0000"><title>Two</title></programme>'
            '</tv>\n'
        ).encode()

        with self.assertRaises(ValueError):
            merge_epg_xml(existing, replacement, {"one"})


if __name__ == "__main__":
    unittest.main()
