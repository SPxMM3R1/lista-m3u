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
        existing = runner.validate_playlist_resolvers(lines).get("cncverse", 0)
        lines += [
            '#EXTINF:-1 tvg-id="ContractProbe@CNCVerse" x-resolver="cncverse" '
            f'x-resolver-id="{ref}" x-resolver-refresh="on_play",Contract probe [CNCVerse]',
            "vibem3u://resolver/cncverse/" + quote(ref, safe=""),
        ]
        self.assertEqual(existing + 1, runner.validate_playlist_resolvers(lines)["cncverse"])

    def trial_specs(self):
        path = runner.CHANNEL_CATALOG_PATH.parent / "contracts/cncverse-trial-channels.json"
        return json.loads(path.read_text(encoding="utf-8"))["channels"]

    def test_trials_are_the_tail_of_both_main_aliases_and_exist_in_inventory(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        specs = self.trial_specs()
        expected = [spec["tvgId"] for spec in specs]
        self.assertEqual(15, len(set(expected)))
        main = (root / "m3u.m3u").read_text(encoding="utf-8")
        self.assertEqual(main, (root / "1.m3u").read_text(encoding="utf-8"))
        channels = runner.parse_channels(main.splitlines())
        self.assertEqual(expected, [channel.tvg_id for channel in channels[-15:]])
        presentation = json.loads((root / "presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertEqual(presentation["orders"]["1.m3u"], presentation["orders"]["m3u.m3u"])
        self.assertEqual(expected, presentation["orders"]["m3u.m3u"][-15:])
        inventory = {channel.tvg_id: channel for channel in runner.parse_channels(
            runner.CHANNEL_CATALOG_PATH.read_text(encoding="utf-8").splitlines())}
        for spec, channel in zip(specs, channels[-15:]):
            with self.subTest(tvgId=spec["tvgId"]):
                ref = f'sportsworld|{spec["group"]}|{spec["label"]}'
                self.assertEqual(ref, runner.cncverse_reference_id(channel.url))
                self.assertEqual(channel.url, inventory[channel.tvg_id].url)
                self.assertEqual(spec["name"], channel.name)
        # The validator requires the full resolver inventory, not a public partition.
        self.assertEqual(15, runner.validate_playlist_resolvers(
            runner.CHANNEL_CATALOG_PATH.read_text(encoding="utf-8").splitlines())["cncverse"])

    def test_trials_have_active_editorial_rows_and_numbers_at_the_end(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        layout = json.loads((root / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        active = sorted((row for row in layout["channels"] if row["state"] == "active"),
                        key=lambda row: row["order"])
        specs = self.trial_specs()
        self.assertEqual([spec["tvgId"] for spec in specs], [row["tvgId"] for row in active[-15:]])
        self.assertEqual(list(range(121, 136)), [row["number"] for row in active[-15:]])
        for row in active[-15:]:
            self.assertEqual("m3u", row["kind"])
            self.assertEqual("1.m3u", row["sourceList"])
            self.assertIs(True, row["trial"])
            self.assertNotIn(row["tvgId"], layout.get("excludedM3u", []))

    def test_trials_remain_outside_epg_scope_and_have_no_persisted_session_material(self):
        ids = {spec["tvgId"] for spec in self.trial_specs()}
        self.assertTrue(ids <= runner.trial_m3u_ids())
        self.assertFalse(ids & {channel.tvg_id for channel in runner.main_playlist_channels()})
        text = json.dumps(self.trial_specs()).lower()
        for forbidden in ["clearkey", "token=", "https://", "/proxy/", "license"]:
            self.assertNotIn(forbidden, text)

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
