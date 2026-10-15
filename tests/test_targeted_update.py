import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import update_m3u
import targeted_update
import change_plan

from targeted_update import (
    apply_playlist_text_updates,
    merge_epg_xml,
    reorder_playlist_lines,
)
import os

from catalog_approval import live_catalog  # noqa: E402


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
    def test_repository_plan_skips_binary_web_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            asset = project_root / "site" / "assets" / "fonts" / "font.ttf"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"\x00\xff\xfe")
            diff_result = CompletedProcess(
                args=["git", "diff"],
                returncode=0,
                stdout="site/assets/fonts/font.ttf\n",
                stderr="",
            )
            show_result = CompletedProcess(
                args=["git", "show"],
                returncode=0,
                stdout=b"\x00\xff\xfe",
                stderr=b"",
            )
            with (
                patch.object(targeted_update, "PROJECT_ROOT", project_root),
                patch.object(
                    targeted_update.subprocess,
                    "run",
                    side_effect=[diff_result, show_result],
                ),
            ):
                plan, before, after = targeted_update.repository_plan("a" * 40)

        self.assertEqual(change_plan.ChangeKind.FULL, plan.kind)
        self.assertEqual(("site/assets/fonts/font.ttf",), plan.changed_files)
        self.assertEqual({}, before)
        self.assertEqual({}, after)

    @live_catalog
    def test_presentation_intent_is_persisted_for_the_scheduled_runner(self) -> None:
        before = {
            "channel-catalog.m3u": (
                '#EXTM3U\n'
                '#EXTINF:-1 tvg-id="one" group-title="News",One\n'
                'https://example.test/one.m3u8\n'
                '#EXTINF:-1 tvg-id="two" group-title="Sports",Two\n'
                'https://example.test/two.m3u8\n'
            )
        }
        after = {
            "channel-catalog.m3u": (
                '#EXTM3U\n'
                '#EXTINF:-1 tvg-id="two" group-title="Sports",Two\n'
                'https://example.test/two.m3u8\n'
                '#EXTINF:-1 tvg-id="one" group-title="News",One editado\n'
                'https://example.test/one.m3u8\n'
            )
        }
        plan = change_plan.ChangePlan(
            change_plan.ChangeKind.PRESENTATION,
            channel_ids=("one", "two"),
            changed_files=("channel-catalog.m3u",),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "presentation-overrides.json"
            with patch.object(targeted_update, "PRESENTATION_OVERRIDES_PATH", path):
                self.assertTrue(
                    targeted_update.persist_presentation_overrides(
                        plan, before, after
                    )
                )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            ["two", "one"],
            payload["orders"]["channel-catalog.m3u"],
        )
        self.assertIn("One editado", payload["info_lines"]["one"])

    def test_stream_intent_is_persisted_for_the_scheduled_runner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream-overrides.json"
            with patch.object(targeted_update, "STREAM_OVERRIDES_PATH", path):
                self.assertTrue(
                    targeted_update.persist_stream_overrides(
                        {"one": "https://example.test/new.m3u8"}, {}
                    )
                )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            "https://example.test/new.m3u8",
            payload["channels"]["one"]["url"],
        )

    def test_stream_intent_rejects_a_signed_playback_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream-overrides.json"
            with patch.object(targeted_update, "STREAM_OVERRIDES_PATH", path):
                with self.assertRaises(change_plan.ChangePlanError):
                    targeted_update.persist_stream_overrides(
                        {"one": "https://cdn.example/live.m3u8?token=secret"},
                        {},
                    )

    def test_direct_epg_change_is_locked_for_future_full_refreshes(self) -> None:
        locked = (
            b'<?xml version="1.0" encoding="utf-8"?>\n'
            b'<tv><channel id="one"><display-name>One manual</display-name>'
            b'</channel><programme channel="one" start="20260918100000 +0000" '
            b'stop="20260918110000 +0000"><title>Manual</title></programme></tv>\n'
        )
        generated = (
            b'<?xml version="1.0" encoding="utf-8"?>\n'
            b'<tv><channel id="one"><display-name>One automatic</display-name>'
            b'</channel><programme channel="one" start="20260918100000 +0000" '
            b'stop="20260918110000 +0000"><title>Automatic</title></programme></tv>\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "epg-manual-overrides.xml"
            path.write_bytes(locked)
            output = update_m3u.apply_epg_manual_overrides(generated, path)

        self.assertIn(b"Manual", output)
        self.assertNotIn(b"Automatic", output)

    def test_partial_epg_refresh_ignores_locks_for_other_channels(self) -> None:
        locked = (
            b'<tv><channel id="one" /><channel id="two" />'
            b'<programme channel="one" start="1" stop="2" />'
            b'<programme channel="two" start="1" stop="2" /></tv>'
        )
        generated = b'<tv><channel id="one" /><programme channel="one" /></tv>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "epg-manual-overrides.xml"
            path.write_bytes(locked)
            output = update_m3u.apply_epg_manual_overrides(
                generated,
                path,
                allowed_ids={"one"},
            )

        self.assertIn(b'channel="one"', output)
        self.assertNotIn(b'channel="two"', output)

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

    def test_targeted_epg_validation_uses_only_refreshed_channels(self) -> None:
        document = (
            b'<tv><channel id="active"/><channel id="inactive"/>'
            b'<programme channel="active" start="20261014000000 +0000" '
            b'stop="20261014130000 +0000"><title>Active</title></programme>'
            b'<programme channel="inactive" start="20261014000000 +0000" '
            b'stop="20261014130000 +0000"><title>Inactive</title></programme></tv>'
        )
        target_ids = {"active"}
        with patch.object(update_m3u, "epg_status_from_xml") as validate:
            targeted_update._validate_targeted_epg(
                document,
                target_ids,
                main_target_ids=target_ids,
                optional_target_ids=set(),
            )

        validated_document, expected_ids = validate.call_args.args
        validation_options = validate.call_args.kwargs
        self.assertEqual(target_ids, expected_ids)
        self.assertIn(b'id="active"', validated_document)
        self.assertNotIn(b'id="inactive"', validated_document)
        self.assertEqual(
            update_m3u.EPG_NON_MAIN_MINIMUM_FUTURE,
            validation_options["minimum_future"],
        )
        self.assertEqual(
            {"active": update_m3u.EPG_MAIN_MINIMUM_FUTURE},
            validation_options["minimum_future_by_channel"],
        )

    def test_targeted_epg_rejects_channels_outside_published_scope(self) -> None:
        active = update_m3u.Channel("Active", "", 0, tvg_id="active")
        managed = update_m3u.Channel("Managed", "", 0, tvg_id="managed")
        with (
            patch.object(update_m3u, "main_playlist_channels", return_value=[active]),
            patch.object(
                update_m3u,
                "epg_scope_channels",
                return_value=([active, managed], {"active", "managed"}),
            ),
        ):
            main_targets, optional_targets = targeted_update._epg_target_scope(
                {"active", "managed"}
            )
            self.assertEqual({"active"}, main_targets)
            self.assertEqual({"managed"}, optional_targets)
            with self.assertRaisesRegex(RuntimeError, "no se especificaron"):
                targeted_update._epg_target_scope(set())
            with self.assertRaisesRegex(RuntimeError, "fuera del alcance publicado"):
                targeted_update._epg_target_scope({"inactive"})

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

    def test_catalog_filter_reparses_line_offsets_after_presentation_reorder(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="one" group-title="News",One',
            "https://example.test/one.m3u8",
            '#EXTINF:-1 tvg-id="two" group-title="Sports",Two',
            "https://example.test/two.m3u8",
            '#EXTINF:-1 tvg-id="three" group-title="News",Three',
            "https://example.test/three.m3u8",
        ]
        stale_offsets = update_m3u.parse_channels(lines)
        self.assertEqual(["one", "two", "three"], [row.tvg_id for row in stale_offsets])
        update_m3u.apply_presentation_overrides(
            lines,
            "channel-catalog.m3u",
            {"orders": {"channel-catalog.m3u": ["three", "two", "one"]}},
        )

        filtered = targeted_update._filter_catalog_membership(lines, {"one", "three"})

        self.assertEqual(
            {"one", "three"},
            {row.tvg_id for row in update_m3u.parse_channels(filtered)},
        )

    def test_scheduled_runner_reapplies_presentation_order_and_metadata(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="one" group-title="News",One',
            "https://example.test/one.m3u8",
            '#EXTINF:-1 tvg-id="two" group-title="Sports",Two',
            "https://example.test/two.m3u8",
        ]
        overrides = {
            "orders": {"channel-catalog.m3u": ["two", "one"]},
            "info_lines": {
                "one": '#EXTINF:-1 tvg-id="one" group-title="News",One editado'
            },
        }

        changed = update_m3u.apply_presentation_overrides(
            lines,
            "channel-catalog.m3u",
            overrides,
        )

        self.assertTrue(changed)
        self.assertLess(
            lines.index('#EXTINF:-1 tvg-id="two" group-title="Sports",Two'),
            lines.index('#EXTINF:-1 tvg-id="one" group-title="News",One editado'),
        )

    def test_presentation_logo_override_uses_repository_asset(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="one" tvg-logo="https://old.example/one.png",One',
            "https://example.test/one.m3u8",
        ]

        changed = update_m3u.apply_presentation_overrides(
            lines,
            "m3u.m3u",
            {"logos": {"one": "logos/13c.png"}},
        )

        self.assertTrue(changed)
        self.assertIn(
            f'tvg-logo="{update_m3u.LOCAL_LOGOS_PUBLIC_BASE}/13c.png"',
            lines[1],
        )
        self.assertNotIn("old.example", lines[1])

    def test_presentation_logo_override_can_use_historical_repository_asset(self) -> None:
        history_root = Path(__file__).resolve().parents[1] / "logos" / "history"
        supported_extensions = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
        historical_logo = next(
            path
            for path in sorted(history_root.iterdir())
            if path.suffix.casefold() in supported_extensions
        )
        logo_path = historical_logo.relative_to(history_root.parents[1]).as_posix()
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="one" tvg-logo="https://old.example/one.png",One',
            "https://example.test/one.m3u8",
        ]

        changed = update_m3u.apply_presentation_overrides(
            lines,
            "m3u.m3u",
            {"logos": {"one": logo_path}},
        )

        self.assertTrue(changed)
        self.assertIn(f"{update_m3u.LOCAL_LOGOS_PUBLIC_BASE}/history/", lines[1])
        self.assertIn(historical_logo.name, lines[1])
        self.assertNotIn("old.example", lines[1])

    def test_presentation_name_override_changes_app_label_without_changing_identity(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="one" tvg-name="Nombre fuente",Nombre fuente',
            "https://example.test/one.m3u8",
        ]

        changed = update_m3u.apply_presentation_overrides(
            lines,
            "m3u.m3u",
            {"names": {"one": "Mi canal favorito"}},
        )

        self.assertTrue(changed)
        self.assertTrue(lines[1].endswith(",Mi canal favorito"))
        parsed = update_m3u.parse_channels(lines)
        self.assertEqual("one", parsed[0].tvg_id)
        self.assertEqual("Mi canal favorito", parsed[0].display_name)

    @patch.dict(
        update_m3u.TVVOO_STREAM_RESOLVER_IDS,
        {"Sky Sports F1": ("vavoo_SKY%20SPORTS%20F1%7Cgroup%3Auk",)},
    )
    def test_name_override_keeps_catalog_name_of_name_keyed_tvvoo_channel(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="SkySportsF1.uk" tvg-name="Sky Sports F1" '
            'x-resolver="tvvoo",Sky Sports F1',
            "https://example.test/f1.m3u8",
        ]

        changed = update_m3u.apply_presentation_overrides(
            lines,
            "channel-catalog.m3u",
            {"names": {"SkySportsF1.uk": "SKY SPORTS F1"}},
        )

        self.assertFalse(changed)
        channel = update_m3u.parse_channels(lines)[0]
        self.assertEqual("Sky Sports F1", channel.name)
        self.assertEqual("tvvoo", update_m3u.resolver_attributes_for(channel)["x-resolver"])

    def test_provider_name_override_maps_only_after_identity_match(self) -> None:
        from types import SimpleNamespace

        reconciliation = SimpleNamespace(matched=(SimpleNamespace(
            row=SimpleNamespace(catalog_key="spain|vavoo_ESPN%201%7Cgroup%3Aes"),
            catalog_id="ESPN1.es@TvVoo",
        ),))
        result = update_m3u.apply_provider_name_overrides(
            {"names": {"spain|vavoo_ESPN%201%7Cgroup%3Aes": "ESPN Deportes"}},
            reconciliation,
        )

        self.assertEqual("ESPN Deportes", result["names"]["ESPN1.es@TvVoo"])
        self.assertEqual(
            "ESPN Deportes",
            result["names"]["spain|vavoo_ESPN%201%7Cgroup%3Aes"],
        )

    def test_presentation_name_loader_rejects_newlines_and_urls(self) -> None:
        for label in ("Canal\ninyectado", "https://example.test/live.m3u8"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "presentation-overrides.json"
                path.write_text(json.dumps({"schema": 1, "names": {"one": label}}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "nombre visible invalido"):
                    update_m3u.load_presentation_overrides(path)

    def test_presentation_logo_override_ignores_paths_outside_logo_directory(self) -> None:
        lines = ["#EXTM3U", '#EXTINF:-1 tvg-id="one",One', "stream"]
        original = lines[1]

        with contextlib.redirect_stderr(io.StringIO()):
            changed = update_m3u.apply_presentation_overrides(
                lines,
                "m3u.m3u",
                {"logos": {"one": "logos/../../outside.png"}},
            )

        self.assertFalse(changed)
        self.assertEqual(original, lines[1])

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

    def test_scheduled_runner_applies_a_stream_lock(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="one",One',
            "https://example.test/one-old.m3u8",
        ]

        applied = update_m3u.apply_stream_overrides(
            lines,
            {"one": "https://example.test/one-fixed.m3u8"},
        )

        self.assertEqual({"one"}, applied)
        self.assertEqual("https://example.test/one-fixed.m3u8", lines[-1])

    def test_repair_does_not_replace_a_stream_lock(self) -> None:
        channel = update_m3u.Channel(
            name="Canal fijado",
            url="https://example.test/fixed.m3u8",
            url_line=1,
            tvg_id="fixed",
        )
        lines = ["#EXTM3U", channel.url]
        result = update_m3u.CheckResult(channel.name, channel.url, False, "down")

        with patch.object(update_m3u, "discover_official_candidates") as discover:
            repaired = update_m3u.repair_failed_channels(
                lines,
                [channel],
                [result],
                allow_ci_geo_block=False,
                protected_channel_ids={"fixed"},
            )

        self.assertEqual([], repaired)
        self.assertEqual(channel.url, lines[1])
        discover.assert_not_called()

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
