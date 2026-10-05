import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

import update_m3u as runner


class CncVerseContractTest(unittest.TestCase):
    def test_reference_contains_only_editorial_group_and_signal(self):
        ref = "sportsworld|TNT Sports UK|TNT Sports 1"
        uri = "vibem3u://resolver/cncverse/" + quote(ref, safe="")
        self.assertEqual(ref, runner.cncverse_reference_id(uri))
        channel = runner.parse_channels([
            '#EXTINF:-1 tvg-id="TNTSports1.uk@CNCVerse",TNT Sports 1 [CNCVerse]', uri,
        ])[0]
        self.assertEqual({"x-resolver": "cncverse", "x-resolver-id": ref,
                          "x-resolver-refresh": "on_play"}, runner.resolver_attributes_for(channel))

    def test_rejects_session_material_and_malformed_references(self):
        for ref in ["opaque-data", "sportsworld|TNT|", "sportsworld|TNT|token=secret",
                    "sportsworld|TNT|https://example.invalid/a", "sportsworld|TNT|a\nb",
                    "sportsworld| TNT|TNT Sports 1", "sportsworld|TNT|a" + "x" * 260]:
            self.assertEqual("", runner.cncverse_reference_id(
                "vibem3u://resolver/cncverse/" + quote(ref, safe="")))
        self.assertEqual("", runner.cncverse_reference_id(
            "vibem3u://resolver/cncverse/sportsworld%7CTNT%7CTNT?token=secret"))

    def test_generated_catalog_is_valid_and_has_bounded_tokenless_config(self):
        catalog = runner.build_resolver_catalog()
        cnc = next(p for p in catalog["providers"] if p["id"] == "cncverse")
        self.assertEqual(120, cnc["cacheTtlSeconds"])
        self.assertEqual(20000, cnc["config"]["resolutionBudgetMs"])
        self.assertNotIn("clearkey", json.dumps(cnc).lower())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resolver-catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            runner.validate_resolver_catalog(path)

    def test_playlist_contract_accepts_reference_without_resolving_or_persisting_url(self):
        ref = "sportsworld|TNT Sports UK|TNT Sports 1"
        lines = runner.CHANNEL_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
        lines += [
            '#EXTINF:-1 tvg-id="TNTSports1.uk@CNCVerse" x-resolver="cncverse" '
            f'x-resolver-id="{ref}" x-resolver-refresh="on_play",TNT Sports 1 [CNCVerse]',
            "vibem3u://resolver/cncverse/" + quote(ref, safe=""),
        ]
        self.assertEqual(1, runner.validate_playlist_resolvers(lines)["cncverse"])

    def test_playlist_contract_rejects_mismatched_reference_metadata(self):
        ref = "sportsworld|TNT Sports UK|TNT Sports 1"
        lines = [
            '#EXTINF:-1 tvg-id="TNTSports1.uk@CNCVerse" x-resolver="cncverse" '
            'x-resolver-id="sportsworld|TNT Sports UK|TNT Sports 2" '
            'x-resolver-refresh="on_play",TNT Sports 1 [CNCVerse]',
            "vibem3u://resolver/cncverse/" + quote(ref, safe=""),
        ]
        with self.assertRaisesRegex(ValueError, "fuera del contrato"):
            runner.validate_playlist_resolvers(lines)


if __name__ == "__main__":
    unittest.main()
