import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import update_m3u


REFERENCE_ID = "unitedkingdom|vavoo_SKY%201%7Cgroup%3Auk"
REFERENCE_ALIAS = "vavoo_SKY%201%7Cgroup%3Auk"
REFERENCE_URI = (
    "tvvoo://channel/unitedkingdom%7Cvavoo_SKY%25201%257Cgroup%253Auk"
)


def reference_lines() -> list[str]:
    return [
        "#EXTM3U",
        (
            f'#EXTINF:-1 tvg-id="{REFERENCE_ID}@TvVoo" '
            'tvg-name="Sky 1" tvg-logo="https://logos.example/sky.png" '
            'group-title="Deportes" x-resolver="tvvoo" '
            f'x-resolver-id="{REFERENCE_ALIAS}" '
            f'x-resolver-ids="{REFERENCE_ALIAS}" '
            'x-resolver-country="unitedkingdom" '
            'x-resolver-refresh="on_play",Sky 1'
        ),
        REFERENCE_URI,
    ]


class TvVooReferenceTests(unittest.TestCase):
    def test_reference_is_metadata_only_and_is_not_probed_or_renewed(self) -> None:
        channel = update_m3u.parse_channels(reference_lines())[0]
        self.assertTrue(update_m3u.is_tvvoo_reference(channel))
        self.assertEqual(update_m3u.resolver_engine_for(channel), "tvvoo")
        with patch.object(update_m3u, "fetch_channel_bytes") as fetch:
            result = update_m3u.check_channel(channel)
        fetch.assert_not_called()
        self.assertTrue(result.ok)
        self.assertNotIn("HLS valida", result.detail)

        factory = Mock(side_effect=AssertionError("must not resolve"))
        outcome = update_m3u.refresh_dynamic_channel(
            channel,
            factory,
            running_in_ci=False,
            current_result=result,
        )
        factory.assert_not_called()
        self.assertTrue(outcome.skipped)
        self.assertFalse(outcome.changed)
        self.assertEqual(outcome.resolved_url, REFERENCE_URI)

    def test_reference_contract_is_valid_without_legacy_map_entry(self) -> None:
        lines = reference_lines()
        lines.extend(
            [
                '#EXTINF:-1 tvg-id="Meganoticias.cl" '
                'x-resolver="meganoticias" x-resolver-refresh="on_play",Meganoticias',
                "https://example.invalid/mega.m3u8",
            ]
        )
        with patch.dict(update_m3u.TVVOO_STREAM_RESOLVER_IDS, {}, clear=True), patch.dict(
            update_m3u.HIGHFLY_RESOLVER_CHANNELS, {}, clear=True
        ):
            counts = update_m3u.validate_playlist_resolvers(lines)
        self.assertEqual(counts["tvvoo"], 1)
        self.assertEqual(counts["meganoticias"], 1)

    def test_malformed_tvvoo_uri_fails_contract_without_becoming_direct(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="bad@TvVoo" x-resolver="tvvoo" '
            'x-resolver-id="bad",Bad reference',
            "tvvoo://not-a-channel",
        ]
        channel = update_m3u.parse_channels(lines)[0]
        self.assertEqual(update_m3u.resolver_engine_for(channel), "tvvoo")
        with self.assertRaisesRegex(ValueError, "referencia TvVoo invalida"):
            update_m3u.validate_playlist_resolvers(lines)

    def test_reference_health_is_identity_only_without_stream_validation_time(self) -> None:
        lines = reference_lines()
        channel = update_m3u.parse_channels(lines)[0]
        result = update_m3u.check_channel(channel)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(update_m3u, "HEALTH_STATE_PATH", root / "health.json"), patch.object(
                update_m3u, "REPORT_PATH", root / "report.json"
            ):
                report = update_m3u.write_report(
                    [channel],
                    [result],
                    False,
                    epg_status={"ok": True},
                    main_channel_ids={channel.tvg_id},
                    main_epg_status={"ok": True},
                )
            entry = report["channels"][0]
            health = json.loads((root / "health.json").read_text(encoding="utf-8"))
        self.assertEqual(entry["status"], "identity_only")
        self.assertTrue(entry["identity_only"])
        self.assertIsNone(entry["last_ok_at"])
        self.assertEqual(
            health["channels"][channel.tvg_id]["status"], "identity_only"
        )

    def test_pin_and_order_preserve_reference_metadata_uri_and_slot(self) -> None:
        lines = reference_lines()
        lines.extend(
            [
                '#EXTINF:-1 tvg-id="0104" group-title="Nacionales",TVN',
                "https://example.invalid/tvn.m3u8",
            ]
        )
        original_info = lines[1]
        update_m3u.pin_resolver_metadata(lines)
        self.assertEqual(lines[1], original_info)
        self.assertEqual(lines[2], REFERENCE_URI)

        update_m3u.order_channels_by_content(lines)
        channels = update_m3u.parse_channels(lines)
        self.assertEqual(channels[0].url, REFERENCE_URI)
        self.assertEqual(channels[0].logo_url, "https://logos.example/sky.png")
        reference_info = lines[channels[0].info_line]
        self.assertIn('x-resolver="tvvoo"', reference_info)
        self.assertIn(f'x-resolver-id="{REFERENCE_ALIAS}"', reference_info)

    def test_public_reference_counts_as_legacy_catalog_membership(self) -> None:
        catalog_lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="SkySportsMainEvent.uk@TvVoo" '
            'x-resolver="tvvoo" x-resolver-ids="legacy",Sky 1',
            "https://example.invalid/legacy.m3u8",
        ]
        with tempfile.TemporaryDirectory() as directory:
            main_path = Path(directory) / "m3u.m3u"
            main_path.write_text("\n".join(reference_lines()) + "\n", encoding="utf-8")
            catalog = update_m3u.parse_channels(catalog_lines)
            self.assertEqual(
                frozenset({"SkySportsMainEvent.uk@TvVoo"}),
                update_m3u.load_manual_main_channel_ids(catalog, main_path),
            )

        external_lines = ["#EXTM3U"]
        result = update_m3u.validate_public_playlist_partition(
            catalog_lines,
            reference_lines(),
            external_lines,
            {"SkySportsMainEvent.uk@TvVoo"},
        )
        self.assertEqual(1, result["main_channels"])


if __name__ == "__main__":
    unittest.main()
