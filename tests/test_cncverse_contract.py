import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

import update_m3u as runner


class CncVerseContractTest(unittest.TestCase):
    def test_chile_exact_channel_auto_mode_and_not_247_annotation(self):
        for ref in ["chiletv|13C (1080p)|auto", "chiletv|Holvoet TV (720p) [Not 24/7]|auto"]:
            self.assertEqual(ref, runner.cncverse_reference_id(
                "vibem3u://resolver/cncverse/" + quote(ref, safe="")))
        for ref in ["chiletv|13C|other", "chiletv|http://local|auto", "unknown|13C|auto",
                    "chiletv|13C?token=a|auto", "sportsworld|TV [Not 24/7]|auto"]:
            self.assertEqual("", runner.cncverse_reference_id(
                "vibem3u://resolver/cncverse/" + quote(ref, safe="")))

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

    def all_trial_specs(self):
        root = runner.CHANNEL_CATALOG_PATH.parent / "contracts"
        return [spec for filename in ["cncverse-trial-channels.json", "cncverse-chile-trial-channels.json"]
                for spec in json.loads((root / filename).read_text(encoding="utf-8"))["channels"]]

    def link_audit(self):
        path = runner.CHANNEL_CATALOG_PATH.parent / "contracts/cncverse-link-audit-20261005.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def not247_exclusions(self):
        path = runner.CHANNEL_CATALOG_PATH.parent / "contracts/cncverse-not247-exclusions.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def removed_trial_ids(self):
        failed = {row["tvgId"] for row in self.link_audit()["channels"]
                  if row["decision"].startswith("removed_")}
        requested = {row["tvgId"] for row in self.not247_exclusions()["channels"]}
        numbered = {row["tvgId"] for row in self.number_exclusions()["channels"]}
        supplemental = {row["tvgId"] for row in self.t13_exclusions()["channels"]}
        # Las bajas siguen siendo historia; solo la nueva orden explícita puede revertirlas.
        restored = set(self.inventory_request()["reintroducedIds"])
        return (failed | requested | numbered | supplemental) - restored

    def inventory_request(self):
        path = runner.CHANNEL_CATALOG_PATH.parent / "contracts/cncverse-inventory-trials-20261007.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def t13_exclusions(self):
        path = runner.CHANNEL_CATALOG_PATH.parent / "contracts/channel-number-exclusions-20261006-t13.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_supplemental_number_removals_are_exact_without_rewriting_prior_decisions(self):
        manifest = self.t13_exclusions()
        requested = {329, 345, 346, 347, 348, 349, 350, 351, 355, 357, 360, 358, 361, 362,
                     364, 365, 366, 367, 369, 370, 371, 372, 376, 377, 378}
        self.assertEqual(requested, set(manifest["requestedNumbers"]))
        self.assertEqual([349], manifest["alreadyAbsentNumbers"])
        self.assertEqual(24, manifest["removed"])
        self.assertEqual(24, manifest["removedCncVerse"])
        self.assertEqual(24, len(manifest["channels"]))
        self.assertEqual(requested - {349}, {r["number"] for r in manifest["channels"]})
        original = {spec["tvgId"]: (121 + i, spec["name"])
                    for i, spec in enumerate(self.all_trial_specs())}
        for row in manifest["channels"]:
            self.assertEqual(original[row["tvgId"]], (row["number"], row["name"]))
        self.assertEqual(24, len({r["tvgId"] for r in manifest["channels"]}))
        self.assertEqual(16, manifest["remainingCncVerse"])

    def test_t13_has_217_as_active_backup_not_a_deleted_or_excluded_source(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        manifest = self.t13_exclusions()
        layout = json.loads((root / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        by_id = {r.get("tvgId"): r for r in layout["channels"]}
        owner, backup = by_id["0124"], by_id[manifest["backup"]["backupId"]]
        self.assertEqual((9, "T13", "active"), (owner["number"], owner["name"], owner["state"]))
        shift = json.loads((root / "contracts/channel-position-change-20261006-france24.json").read_text(encoding="utf-8"))["numberShift"]["delta"]
        self.assertEqual((217 + shift, "active", True), (backup["number"], backup["state"], backup["trial"]))
        self.assertIn(backup["tvgId"], owner["backupm3u"])
        self.assertNotIn(backup["tvgId"], layout["excludedM3u"])
        self.assertEqual("0.5.73", manifest["minimumBackupAppVersion"])
        ids = {c.tvg_id for c in runner.parse_channels((root / "1.m3u").read_text(encoding="utf-8").splitlines())}
        self.assertTrue({owner["tvgId"], backup["tvgId"]} <= ids)
        self.assertNotIn(backup["tvgId"], self.removed_trial_ids())

    def number_exclusions(self):
        path = runner.CHANNEL_CATALOG_PATH.parent / "contracts/channel-number-exclusions-20261006.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_requested_number_exclusions_are_exact_and_preserve_historical_decisions(self):
        manifest = self.number_exclusions()
        self.assertEqual("removed_by_user_numbers", manifest["decision"])
        self.assertEqual(152, len(set(manifest["requestedNumbers"])))
        self.assertEqual([188], manifest["alreadyAbsentNumbers"])
        self.assertEqual(151, manifest["removed"])
        self.assertEqual(151, len(manifest["channels"]))
        self.assertEqual(151, len({r["tvgId"] for r in manifest["channels"]}))
        self.assertEqual(set(manifest["requestedNumbers"]) - {188},
                         {r["number"] for r in manifest["channels"]})
        original = {spec["tvgId"]: (121 + i, spec["name"])
                    for i, spec in enumerate(self.all_trial_specs())}
        cnc = [r for r in manifest["channels"] if r["tvgId"].endswith("@CNCVerse")]
        self.assertEqual(150, manifest["removedCncVerse"])
        self.assertEqual(150, len(cnc))
        for row in cnc:
            self.assertEqual(original[row["tvgId"]], (row["number"], row["name"]))
        self.assertEqual([{"number": 86, "name": "TV+ [DPS]", "tvgId": "TVPlus.cl@DPS"}],
                         [r for r in manifest["channels"] if not r["tvgId"].endswith("@CNCVerse")])
        previous = {r["tvgId"] for r in self.link_audit()["channels"]
                    if r["decision"].startswith("removed_")}
        previous |= {r["tvgId"] for r in self.not247_exclusions()["channels"]}
        self.assertFalse(previous & {r["tvgId"] for r in manifest["channels"]})
        self.assertEqual(40, manifest["remainingCncVerse"])

    def trial_specs(self):
        return self.inventory_request()["activeChannels"]

    def test_user_not247_exclusions_are_exact_and_separate_from_link_failures(self):
        exclusions = self.not247_exclusions()
        self.assertEqual("removed_by_user_not_247", exclusions["decision"])
        self.assertEqual(12, exclusions["removed"])
        self.assertEqual(190, exclusions["remainingCncVerse"])
        self.assertEqual([140, 156, 204, 208, 227, 228, 229, 243, 247, 251, 258, 265],
                         sorted(row["number"] for row in exclusions["channels"]))
        requested = {row["tvgId"] for row in exclusions["channels"]}
        self.assertEqual(12, len(requested))
        previously_retained = {row["tvgId"] for row in self.link_audit()["channels"]
                               if row["decision"] == "retained_active_link" and row["not247"]}
        self.assertEqual(previously_retained, requested)
        specs = {spec["tvgId"]: spec for spec in self.all_trial_specs()}
        for row in exclusions["channels"]:
            self.assertEqual(specs[row["tvgId"]]["name"], row["name"])
            self.assertIn("[Not 24/7]", row["name"])
        # La nueva petición de todo el inventario admite también las pruebas Not 24/7.
        approved = {spec["tvgId"] for spec in self.inventory_request()["addedChannels"]}
        self.assertTrue({spec["tvgId"] for spec in self.trial_specs()
                         if "[Not 24/7]" in spec["name"]} <= approved)

    def test_link_audit_requires_fresh_recheck_before_removal(self):
        audit = self.link_audit()
        original_ids = {spec["tvgId"] for spec in self.all_trial_specs()}
        self.assertEqual(258, len(original_ids))
        self.assertEqual(original_ids, {row["tvgId"] for row in audit["channels"]})
        self.assertEqual(258, audit["checked"])
        self.assertEqual(258, len(audit["channels"]))
        removed = []
        for row in audit["channels"]:
            attempts = row["attempts"]
            self.assertTrue(attempts)
            for attempt in attempts:
                self.assertTrue(attempt["startedAtUtc"].endswith("Z"))
                self.assertIsInstance(attempt["hlsValidated"], bool)
            if row["decision"].startswith("removed_"):
                removed.append(row["tvgId"])
                self.assertEqual([1, 2], [attempt["round"] for attempt in attempts])
                if row["decision"] == "removed_no_active_link":
                    self.assertTrue(all(not attempt["hlsValidated"] for attempt in attempts))
                else:
                    self.assertEqual("removed_no_signal_plate", row["decision"])
                    self.assertTrue(all(attempt["decodedFrame"] and attempt["noSignalPlate"]
                                        for attempt in attempts))
            else:
                self.assertEqual("retained_active_link", row["decision"])
                self.assertTrue(any(attempt["hlsValidated"] for attempt in attempts))
        self.assertEqual(len(removed), audit["removed"])
        self.assertEqual(258 - len(removed), audit["retained"])
        for forbidden in ["https://", "token=", "clearkey", "/proxy/"]:
            self.assertNotIn(forbidden, json.dumps(audit).lower())

    def test_removed_trials_are_purged_not_hidden_and_cannot_be_reimported(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        removed = self.removed_trial_ids()
        self.assertTrue(removed)
        layout = json.loads((root / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        presentation = json.loads((root / "presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertFalse(removed & {row.get("tvgId") for row in layout["channels"]})
        self.assertTrue(removed <= set(layout["excludedM3u"]))
        self.assertTrue(removed <= set(presentation["excluded_m3u"]))
        for filename in ["channel-catalog.m3u", "m3u.m3u", "1.m3u"]:
            ids = {channel.tvg_id for channel in runner.parse_channels(
                (root / filename).read_text(encoding="utf-8").splitlines())}
            self.assertFalse(removed & ids)
        for order in presentation["orders"].values():
            self.assertFalse(removed & set(order))

    def test_trials_are_the_tail_of_both_main_aliases_and_exist_in_inventory(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        specs = self.trial_specs()
        expected = [spec["tvgId"] for spec in specs]
        self.assertEqual(len(self.inventory_request()["activeCncIds"]), len(set(expected)))
        main = (root / "m3u.m3u").read_text(encoding="utf-8")
        self.assertEqual(main, (root / "1.m3u").read_text(encoding="utf-8"))
        channels = runner.parse_channels(main.splitlines())
        self.assertEqual(expected, [channel.tvg_id for channel in channels[-len(expected):]])
        presentation = json.loads((root / "presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertEqual(presentation["orders"]["1.m3u"], presentation["orders"]["m3u.m3u"])
        self.assertEqual(expected, presentation["orders"]["m3u.m3u"][-len(expected):])
        inventory = {channel.tvg_id: channel for channel in runner.parse_channels(
            runner.CHANNEL_CATALOG_PATH.read_text(encoding="utf-8").splitlines())}
        for spec, channel in zip(specs, channels[-len(expected):]):
            with self.subTest(tvgId=spec["tvgId"]):
                ref = f'{spec.get("catalog", "sportsworld")}|{spec["group"]}|{spec["label"]}'
                self.assertEqual(ref, runner.cncverse_reference_id(channel.url))
                self.assertEqual(channel.url, inventory[channel.tvg_id].url)
                self.assertEqual(spec["name"], channel.name)
        # The validator requires the full resolver inventory, not a public partition.
        self.assertEqual(len(specs), runner.validate_playlist_resolvers(
            runner.CHANNEL_CATALOG_PATH.read_text(encoding="utf-8").splitlines())["cncverse"])

    def test_trials_have_active_editorial_rows_and_numbers_at_the_end(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        layout = json.loads((root / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        active = sorted((row for row in layout["channels"] if row["state"] == "active"),
                        key=lambda row: row["order"])
        specs = self.trial_specs()
        self.assertEqual([spec["tvgId"] for spec in specs], [row["tvgId"] for row in active[-len(specs):]])
        # Mantener números previos; únicamente las altas explícitas usan el nuevo rango final.
        self.assertEqual([spec["number"] for spec in specs],
                         [row["number"] for row in active[-len(specs):]])
        for row in active[-len(specs):]:
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

    def test_chile_fixture_is_242_exact_names_and_tsn5_without_provider_ids(self):
        root = runner.CHANNEL_CATALOG_PATH.parent
        fixture = json.loads((root / "contracts/cncverse-chile-trial-channels.json").read_text(encoding="utf-8"))
        self.assertEqual("0.5.68", fixture["minimumAppVersion"])
        self.assertEqual("TSN5.ca@CNCVerse", fixture["channels"][0]["tvgId"])
        chile = fixture["channels"][1:]
        self.assertEqual(242, len(chile))
        self.assertEqual(242, len({s["group"] for s in chile}))
        self.assertEqual(242, len({s["tvgId"] for s in chile}))
        for spec in chile:
            self.assertEqual("chiletv", spec["catalog"])
            self.assertEqual("auto", spec["label"])
            self.assertEqual({"tvgId", "name", "catalog", "group", "label", "logoPath"}, set(spec))
            self.assertTrue(spec["tvgId"].startswith("CNCVerse.Chile."))


if __name__ == "__main__":
    unittest.main()
