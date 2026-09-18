import unittest

from change_plan import ChangeKind, ChangePlanError, classify_changes


BASE_PLAYLIST = """#EXTM3U
#EXTINF:-1 tvg-id=\"one\" group-title=\"News\",One
https://example.test/one.m3u8
#EXTINF:-1 tvg-id=\"two\" group-title=\"Sports\",Two
https://example.test/two.m3u8
"""


class ChangePlanTest(unittest.TestCase):
    def test_logo_change_is_presentation_only(self) -> None:
        plan = classify_changes(["logos/one.png"])

        self.assertEqual(ChangeKind.PRESENTATION, plan.kind)
        self.assertEqual((), plan.channel_ids)
        self.assertFalse(plan.full_run_required)

    def test_reordering_playlist_is_presentation_only(self) -> None:
        reordered = """#EXTM3U
#EXTINF:-1 tvg-id=\"two\" group-title=\"Sports\",Two
https://example.test/two.m3u8
#EXTINF:-1 tvg-id=\"one\" group-title=\"News\",One
https://example.test/one.m3u8
"""

        plan = classify_changes(
            ["channel-catalog.m3u"],
            before={"channel-catalog.m3u": BASE_PLAYLIST},
            after={"channel-catalog.m3u": reordered},
        )

        self.assertEqual(ChangeKind.PRESENTATION, plan.kind)
        self.assertEqual(("one", "two"), plan.channel_ids)

    def test_playlist_header_change_is_presentation_only(self) -> None:
        changed = BASE_PLAYLIST.replace(
            "#EXTM3U\n",
            '#EXTM3U x-tvg-url="https://example.test/epg.xml"\n',
        )

        plan = classify_changes(
            ["m3u.m3u"],
            before={"m3u.m3u": BASE_PLAYLIST},
            after={"m3u.m3u": changed},
        )

        self.assertEqual(ChangeKind.PRESENTATION, plan.kind)

    def test_single_stream_change_targets_only_changed_channel(self) -> None:
        changed = BASE_PLAYLIST.replace(
            "https://example.test/two.m3u8",
            "https://example.test/two-new.m3u8",
        )

        plan = classify_changes(
            ["channel-catalog.m3u"],
            before={"channel-catalog.m3u": BASE_PLAYLIST},
            after={"channel-catalog.m3u": changed},
        )

        self.assertEqual(ChangeKind.STREAM, plan.kind)
        self.assertEqual(("two",), plan.channel_ids)
        self.assertFalse(plan.full_run_required)

    def test_epg_manifest_targets_only_declared_channels(self) -> None:
        plan = classify_changes(
            ["epg-overrides.json"],
            after={
                "epg-overrides.json": (
                    '{"channels": [{"tvg_id": "two", "source": "sky-oficial", '
                    '"source_id": "4091"}]}'
                )
            },
        )

        self.assertEqual(ChangeKind.EPG, plan.kind)
        self.assertEqual(("two",), plan.channel_ids)

    def test_stream_manifest_targets_only_declared_channels(self) -> None:
        plan = classify_changes(
            ["stream-overrides.json"],
            after={
                "stream-overrides.json": (
                    '{"channels": [{"tvg_id": "one", '
                    '"url": "https://example.test/one-new.m3u8"}]}'
                )
            },
        )

        self.assertEqual(ChangeKind.STREAM, plan.kind)
        self.assertEqual(("one",), plan.channel_ids)

    def test_membership_change_is_deferred_to_full_window(self) -> None:
        added = BASE_PLAYLIST + (
            '#EXTINF:-1 tvg-id="three",Three\nhttps://example.test/three.m3u8\n'
        )

        plan = classify_changes(
            ["m3u.m3u"],
            before={"m3u.m3u": BASE_PLAYLIST},
            after={"m3u.m3u": added},
        )

        self.assertEqual(ChangeKind.FULL, plan.kind)
        self.assertTrue(plan.full_run_required)

    def test_logic_change_is_deferred_to_full_window(self) -> None:
        plan = classify_changes(["update_m3u.py"])

        self.assertEqual(ChangeKind.FULL, plan.kind)
        self.assertTrue(plan.full_run_required)

    def test_stream_and_epg_changes_are_not_mixed_automatically(self) -> None:
        with self.assertRaises(ChangePlanError):
            classify_changes(
                ["stream-overrides.json", "epg-overrides.json"],
                after={
                    "stream-overrides.json": (
                        '{"channels": [{"tvg_id": "one", '
                        '"url": "https://example.test/one-new.m3u8"}]}'
                    ),
                    "epg-overrides.json": (
                        '{"channels": [{"tvg_id": "one", "source": "sky-oficial", '
                        '"source_id": "4091"}]}'
                    )
                },
            )

    def test_duplicate_ids_in_playlist_fail_closed(self) -> None:
        duplicate = BASE_PLAYLIST + (
            '#EXTINF:-1 tvg-id="one",Duplicate\nhttps://example.test/dup.m3u8\n'
        )

        with self.assertRaises(ChangePlanError):
            classify_changes(
                ["channel-catalog.m3u"],
                before={"channel-catalog.m3u": BASE_PLAYLIST},
                after={"channel-catalog.m3u": duplicate},
            )


if __name__ == "__main__":
    unittest.main()
