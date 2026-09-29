import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import update_m3u  # noqa: E402


def channel(name: str, url: str, engine: str = "direct") -> update_m3u.Channel:
    return update_m3u.Channel(name, url, 0, 1, tvg_id=f"{name}.id")


class ChannelPartsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engines = {}
        patcher = patch.object(
            update_m3u,
            "resolver_engine_for",
            side_effect=lambda item: self.engines.get(item.name, "direct"),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_part_round_trips_with_dynamic_outcome(self) -> None:
        highfly = channel("Sky F1", "https://a.invalid/old.m3u8")
        self.engines["Sky F1"] = "highfly"
        result = update_m3u.CheckResult("Sky F1", highfly.url, False, "HTTP 404")
        renewed = update_m3u.CheckResult("Sky F1", "https://a.invalid/new.m3u8", True, "ok")
        outcome = update_m3u.DynamicRefreshOutcome(
            channel="Sky F1",
            resolver="highfly",
            accepted=True,
            changed=True,
            skipped=False,
            detail="renovado",
            resolved_url=renewed.url,
            check_result=renewed,
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            update_m3u.write_channel_part(
                directory, "highfly", [highfly], {"Sky F1": result}, [outcome]
            )
            entries = update_m3u.read_channel_part(directory, "highfly")

        self.assertEqual(
            entries["Sky F1"],
            update_m3u.ChannelPartEntry(url=highfly.url, result=result, outcome=outcome),
        )

    def test_only_same_url_results_are_reused(self) -> None:
        kept = channel("Canal A", "https://a.invalid/a.m3u8")
        moved = channel("Canal B", "https://a.invalid/b-nueva.m3u8")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            update_m3u.write_channel_part(
                directory,
                "direct",
                [kept, channel("Canal B", "https://a.invalid/b-vieja.m3u8")],
                {
                    "Canal A": update_m3u.CheckResult("Canal A", kept.url, True, "ok"),
                    "Canal B": update_m3u.CheckResult("Canal B", "vieja", True, "ok"),
                },
                [],
            )
            usable = update_m3u.load_channel_parts(directory, [kept, moved])

        self.assertEqual(set(usable), {"Canal A"})

    def test_missing_provider_parts_are_verified_here(self) -> None:
        direct = channel("Canal A", "https://a.invalid/a.m3u8")
        tvn = channel("TVN", "https://a.invalid/tvn.m3u8")
        self.engines["TVN"] = "tvn"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            update_m3u.write_channel_part(
                directory,
                "direct",
                [direct],
                {"Canal A": update_m3u.CheckResult("Canal A", direct.url, True, "de la parte")},
                [],
            )
            update_m3u.channel_part_path(directory, "tvn").write_text("{roto", encoding="utf-8")
            parts = update_m3u.load_channel_parts(directory, [direct, tvn])
            verified = []

            def fake_verify(channels, *, allow_ci_geo_block):
                verified.extend(item.name for item in channels)
                return [update_m3u.CheckResult(item.name, item.url, True, "aqui") for item in channels]

            with patch.object(update_m3u, "verify_all", side_effect=fake_verify):
                results = update_m3u.verify_with_channel_parts(
                    [direct, tvn], parts, allow_ci_geo_block=True
                )

        self.assertEqual(verified, ["TVN"])
        self.assertEqual([item.detail for item in results], ["de la parte", "aqui"])

    def test_no_parts_dir_verifies_everything(self) -> None:
        self.assertEqual(update_m3u.load_channel_parts(None, [channel("A", "u")]), {})

    def test_part_names_cover_every_check_policy(self) -> None:
        self.assertEqual(
            set(update_m3u.CHANNEL_PART_NAMES), set(update_m3u.CHANNEL_CHECK_POLICIES)
        )


if __name__ == "__main__":
    unittest.main()
