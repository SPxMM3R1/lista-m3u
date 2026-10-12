import json
from pathlib import Path
import hashlib
import unittest
import nauta_reference
import update_m3u as runner
import catalog_baseline
import os

# Pruebas del catálogo publicado (2026-10-12): comparan las listas y el layout ya publicados.
# Los runners de guía y canales las saltan (M3U_RUNNER_TESTS=1) porque generan esas listas
# después de probar; si una baja reciente aún no se regeneró, bloquearían la propia
# regeneración. Al publicar desde el editor o subir código corren completas.
live_catalog = unittest.skipIf(
    os.environ.get("M3U_RUNNER_TESTS") == "1",
    "catálogo publicado: lo revisa el flujo del editor, no el runner",
)

ROOT = Path(__file__).resolve().parents[1]


def authorized_restorations():
    record = json.loads((ROOT/"contracts/nauta-restoration-20261008-sports.json").read_text(encoding="utf-8"))
    return {r["tvgId"] for r in record["channels"]}


def authorized_followup_deletions():
    record = json.loads((ROOT/"contracts/nauta-247-cleanup-20261008.json").read_text(encoding="utf-8"))
    return {r["tvgId"] for r in record["channels"]}


def previously_listed_nauta_ids():
    fixture = json.loads((ROOT/"contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
    ids = {row["tvgId"] for row in fixture["channels"]}
    removed = {row["tvgId"] for row in audit["channels"] if row["decision"] == "remove"}
    removed -= authorized_restorations()
    removed |= authorized_followup_deletions()
    return ids - removed


def selected_nauta_rows(layout):
    return {row["tvgId"]: row for row in layout["channels"]
            if str(row.get("tvgId", "")).startswith("Nauta.")}


class NautaReferenceTest(unittest.TestCase):
    def test_roundtrip_exact_name_with_region_and_slashes(self):
        for name in ["ESPN 1 | Chile", "South Park 24/7", "TUDN ", "El canal, HD"]:
            self.assertEqual(("cat_4", name), nauta_reference.parse_reference(nauta_reference.reference("cat_4", name)))

    def test_invalid_or_sensitive_locators_fail_closed(self):
        for url in ["vibem3u://resolver/nauta/cat_4%7CX?token=x", "vibem3u://user@resolver/nauta/cat_4%7CX",
                    "vibem3u://resolver/nauta/opaque-provider-id", "vibem3u://resolver/nauta/cat_4%7Chttps%3A%2F%2Fhost"]:
            self.assertIsNone(nauta_reference.parse_reference(url))

    @live_catalog
    def test_currently_listed_nauta_is_opt_in_from_the_live_editor_catalog(self):
        fixture = json.loads((ROOT/"contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
        snapshot_ids = {r["tvgId"] for r in fixture["channels"]}
        ids = previously_listed_nauta_ids()
        self.assertEqual(fixture["distinctNames"], len(snapshot_ids))
        self.assertEqual(353, len(ids))
        self.assertGreaterEqual(fixture["providerEntries"], len(ids))
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        selected = selected_nauta_rows(layout)
        unselected = ids - selected.keys()
        self.assertTrue(unselected.isdisjoint(r.get("tvgId") for r in layout["channels"]))
        self.assertTrue(unselected.issubset(presentation["excluded_m3u"]))
        self.assertTrue(unselected.isdisjoint(layout["excludedM3u"]))
        self.assertTrue(unselected.isdisjoint(presentation["trial_m3u"]))
        for order in presentation["orders"].values():
            self.assertTrue(unselected.isdisjoint(order))
        for file in ["m3u.m3u", "1.m3u", "channel-catalog.m3u"]:
            lines = (ROOT/file).read_text(encoding="utf-8").splitlines()
            channels = [c for c in runner.parse_channels(lines) if c.tvg_id in unselected]
            self.assertEqual([], channels)
        self.assertEqual((ROOT/"m3u.m3u").read_bytes(), (ROOT/"1.m3u").read_bytes())

    @live_catalog
    def test_old_editorial_rows_match_latest_approved_baseline(self):
        # La base guardada es la aprobada (digest 0f3350… / ad6addb…, 2026-10-11) y se verifica
        # aquí; después solo se aceptan bajas del usuario a la papelera (app o editor).
        def editorial_digest(layout):
            current = json.loads(json.dumps(layout))
            current["channels"] = [row for row in current["channels"]
                                   if not str(row.get("tvgId", "")).startswith("Nauta.")]
            current["excludedM3u"] = sorted(id for id in current["excludedM3u"] if not id.endswith("@Nauta"))
            # Deshacer solo la inserción editorial ESPN 7 del 10-10 antes de comparar.
            for row in current["channels"]:
                if 38 <= row["order"] <= 261:
                    row["order"] -= 1
                if row["state"] == "active" and 38 <= row["number"] <= 94:
                    row["number"] -= 1
            return hashlib.sha256(json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

        base = catalog_baseline.BASELINE
        self.assertEqual("0f335001f13d3718d5d82bf51b53bd16204e2d999ae51a57744893b972ec4f13",
                         editorial_digest(base["layout"]))
        base_selection = json.dumps(base["selection"], ensure_ascii=False, indent=2) + "\n"
        self.assertEqual("ad6addb253c0c93e28b115ac81bb19273d259633b110b1954f63e010870f2de9",
                         hashlib.sha256(base_selection.encode()).hexdigest())
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        selection = json.loads((ROOT/"data/vibem3u-selection.json").read_text(encoding="utf-8"))
        trashed = catalog_baseline.user_trashed_rows(layout)
        self.assertEqual(catalog_baseline.layout_without_trash(base["layout"], trashed),
                         catalog_baseline.layout_without_trash(layout, trashed))
        self.assertEqual(catalog_baseline.selection_without_trash(base["selection"], trashed),
                         catalog_baseline.selection_without_trash(selection, trashed))

    @live_catalog
    def test_cleanup_has_repeated_evidence_and_cannot_resurrect_removed_rows(self):
        audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
        fixture = json.loads((ROOT/"contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
        self.assertEqual({r["tvgId"] for r in fixture["channels"]}, {r["tvgId"] for r in audit["channels"]})
        removed = {r["tvgId"] for r in audit["channels"] if r["decision"] == "remove"}
        retained = {r["tvgId"] for r in audit["channels"] if r["decision"] == "retain"}
        self.assertEqual((533, 394, 139), (audit["reviewed"], len(retained), len(removed)))
        for row in audit["channels"]:
            checks = row["checks"]
            if row["decision"] == "retain":
                self.assertTrue(any(c["status"] == "video_ok" and c["decoded"] and c["appResolved"] for c in checks))
            else:
                self.assertEqual(3, len(checks))
                self.assertTrue(all(c["status"] == row["reason"] for c in checks))
                self.assertNotIn("video_ok", [c["status"] for c in checks])
                if row["reason"] == "provider_update_slate":
                    self.assertTrue(all(c["decoded"] and c["frameSha256"] in audit["verifiedUpdateSlateSha256"] for c in checks))
                elif row["reason"] == "playback_connection_error":
                    self.assertTrue(all(c["mediaHttpCodes"] and set(c["mediaHttpCodes"]) == {404} for c in checks))
                else:
                    self.assertEqual("provider_name_missing", row["reason"])
        # Cleanup facts remain immutable; this later editorial authorization restores a closed subset.
        removed -= authorized_restorations()
        followup_removed = authorized_followup_deletions()
        removed |= followup_removed
        retained -= followup_removed
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertTrue(removed.issubset(layout["excludedM3u"]))
        self.assertTrue(removed.issubset(presentation["excluded_m3u"]))
        self.assertTrue(removed.isdisjoint(r.get("tvgId") for r in layout["channels"]))
        self.assertTrue(removed.isdisjoint(presentation["trial_m3u"]))
        for order in presentation["orders"].values():
            self.assertTrue(removed.isdisjoint(order))
        for file in ["1.m3u", "m3u.m3u", "channel-catalog.m3u", "2.m3u", "m3u-externa.m3u"]:
            self.assertTrue(removed.isdisjoint(c.tvg_id for c in runner.parse_channels((ROOT/file).read_text(encoding="utf-8").splitlines())))
        expected = {r["tvgId"]: (r["number"], r["order"]) for r in audit["preservedRows"]}
        unselected = previously_listed_nauta_ids()
        expected_current = expected.keys() - followup_removed - unselected
        current_rows = {r["tvgId"]: (r["number"], r["order"]) for r in layout["channels"]
                        if r.get("tvgId") in retained and r.get("tvgId") not in unselected}
        self.assertEqual(expected_current, current_rows.keys())
        self.assertEqual({id: value for id, value in expected.items()
                          if id not in followup_removed and id not in unselected}, current_rows)
        for name in ["ESPN 1 | Chile", "DSports 2 HD"]:
            control = next(r for r in audit["channels"] if r["name"] == name)
            self.assertEqual(["video_ok"] * 3, [c["status"] for c in control["checks"]])

    @live_catalog
    def test_cleanup_preserves_other_presentation_and_contains_no_secrets(self):
        audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        nauta_logos = presentation.get("logos", {})
        nauta_asset_paths = {path for channel_id, path in nauta_logos.items()
                             if str(channel_id).endswith("@Nauta")}
        non_nauta_asset_paths = {path for channel_id, path in nauta_logos.items()
                                 if not str(channel_id).endswith("@Nauta")}
        nauta_only_assets = nauta_asset_paths - non_nauta_asset_paths

        def strip_nauta(value):
            if isinstance(value, list):
                return [strip_nauta(v) for v in value
                        if not (isinstance(v, str) and
                                (v.endswith("@Nauta") or v in nauta_only_assets))]
            if isinstance(value, dict):
                return {k: strip_nauta(v) for k, v in value.items() if not k.endswith("@Nauta")}
            return value

        def digest(value):
            return hashlib.sha256(json.dumps(strip_nauta(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

        # La base aprobada conserva el digest de la auditoría; lo publicado solo puede diferir
        # en canales que el usuario envió después a la papelera (app o editor).
        base = catalog_baseline.BASELINE["presentation"]
        self.assertEqual(audit["nonNautaPresentationSha256"], digest(base))
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        trashed = catalog_baseline.user_trashed_ids(layout)
        self.assertEqual(strip_nauta(catalog_baseline.presentation_without_trash(base, trashed)),
                         strip_nauta(catalog_baseline.presentation_without_trash(presentation, trashed)))
        allowed = {"atUtc", "status", "appResolved", "decoded", "audioDetected", "mediaHttpCodes", "apiHttpCodes", "frameSha256"}
        self.assertTrue(all(set(c).issubset(allowed) for r in audit["channels"] for c in r["checks"]))
        self.assertTrue(all(not c["apiHttpCodes"] for r in audit["channels"] for c in r["checks"]))

    @live_catalog
    def test_sports_restoration_is_exactly_authorized_and_preserves_history(self):
        record = json.loads((ROOT/"contracts/nauta-restoration-20261008-sports.json").read_text(encoding="utf-8"))
        expected_numbers = {108,114,165,204,205,216,271,277,295,306,308,309,311,315,319,320,323,325,337,394,424,463,476,545,562,563,564,573,584,597,598,607,608,617}
        self.assertEqual(expected_numbers, {r["originalNumber"] for r in record["channels"]})
        self.assertEqual(34, len(record["channels"]))
        self.assertEqual(34, len(authorized_restorations()))
        self.assertEqual((34,105,428), (record["restored"], record["remainingRemoved"], record["activeNauta"]))
        for file, field in [("contracts/nauta-validation-20261008.json", "originalCleanupSha256"),
                            ("contracts/nauta-trial-channels-20261007.json", "originalSnapshotSha256"),
                            ("NAUTA_CANALES_ELIMINADOS_20261008.md", "originalRemovalReportSha256")]:
            self.assertEqual(record[field], hashlib.sha256((ROOT/file).read_bytes()).hexdigest())
        audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
        removed = {r["tvgId"] for r in audit["channels"] if r["decision"] == "remove"}
        self.assertTrue(authorized_restorations().issubset(removed))

    @live_catalog
    def test_restored_rows_have_original_numbers_trial_refs_and_no_tombstones(self):
        record = json.loads((ROOT/"contracts/nauta-restoration-20261008-sports.json").read_text(encoding="utf-8"))
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        restored = authorized_restorations()
        deleted = authorized_followup_deletions()
        surviving = restored - deleted
        # Las restauradas que el usuario envió después a la papelera quedan fuera como las demás.
        rows = {r.get("tvgId"): r for r in layout["channels"]
                if r.get("tvgId") in surviving and r["state"] != "deleted"}
        self.assertTrue(all(row["state"] == "active" and row["trial"] for row in rows.values()))
        self.assertEqual(253 + len(selected_nauta_rows(layout)), len(layout["channels"]))
        self.assertTrue(surviving.isdisjoint(layout["excludedM3u"]))
        self.assertTrue((surviving - rows.keys()).issubset(presentation["excluded_m3u"]))
        self.assertTrue((surviving - rows.keys()).isdisjoint(presentation["trial_m3u"]))
        self.assertTrue(rows.keys() <= set(presentation["trial_m3u"]))
        self.assertTrue(rows.keys().isdisjoint(presentation["excluded_m3u"]))
        self.assertTrue(surviving.issubset(previously_listed_nauta_ids()))
        for row in record["channels"]:
            if row["tvgId"] in deleted:
                continue
            self.assertEqual(row["tvgId"], nauta_reference.channel_id(row["name"]))
        # Las filas en la papelera siguen en el catálogo de resolutores (igual que cualquier
        # fila «deleted»); solo las que ya no están en el layout deben faltar también ahí.
        trashed_in_layout = {r.get("tvgId") for r in layout["channels"] if r["state"] == "deleted"}
        for file in ["1.m3u", "m3u.m3u", "channel-catalog.m3u"]:
            absent = surviving - rows.keys()
            if file == "channel-catalog.m3u":
                absent -= trashed_in_layout
            channels = [c for c in runner.parse_channels((ROOT/file).read_text(encoding="utf-8").splitlines())
                        if c.tvg_id in absent]
            self.assertEqual([], channels)
            self.assertTrue(absent.isdisjoint(presentation["orders"][file]))
        self.assertEqual(0, len((surviving - rows.keys()) & {c.tvg_id for c in runner.main_playlist_channels()}))

    def test_restoration_reports_failure_and_retest_separately_without_secrets(self):
        record = json.loads((ROOT/"contracts/nauta-restoration-20261008-sports.json").read_text(encoding="utf-8"))
        allowed = {"atUtc", "status", "appResolved", "decoded"}
        for row in record["channels"]:
            self.assertEqual(3, len(row["retestChecks"]))
            self.assertTrue(all(set(c) == allowed for c in row["retestChecks"]))
            self.assertEqual(sum(c["status"] == "video_ok" for c in row["retestChecks"]), row["videoPasses"])
        passed = {r["originalNumber"]: r["videoPasses"] for r in record["channels"] if r["videoPasses"]}
        self.assertEqual({295:1,306:3,308:3,320:3}, passed)
        text = json.dumps(record)
        for secret in [".m3u8", "http://", "https://", "Authorization", "Cookie", "token=", "sourceUrl"]:
            self.assertNotIn(secret, text)

    def test_requested_positions_and_every_24_7_title_are_removed_exactly_once(self):
        record = json.loads((ROOT/"contracts/nauta-247-cleanup-20261008.json").read_text(encoding="utf-8"))
        explicit = {271,306,308,309,311,321}
        removed = {r["tvgId"] for r in record["channels"]}
        self.assertEqual((6,70,75), (record["resultingCounts"]["explicitPositions"], record["resultingCounts"]["titleMatches24_7"], len(removed)))
        self.assertEqual((428,353,681,606), (record["resultingCounts"]["activeNautaBefore"], record["resultingCounts"]["activeNautaAfter"], record["resultingCounts"]["editorialRowsBefore"], record["resultingCounts"]["editorialRowsAfter"]))
        self.assertEqual(explicit, {r["numberAtRemoval"] for r in record["channels"] if r["userSpecifiedPosition"]})
        titleMatches = {r["tvgId"] for r in record["channels"] if "name_contains_24_7" in r["requestedReasons"]}
        self.assertEqual(70, len(titleMatches))
        self.assertIn(321, {r["numberAtRemoval"] for r in record["channels"] if "name_contains_24_7" in r["requestedReasons"]})
        self.assertTrue(all(r["kind"] == "m3u" and r["sourceList"] == "1.m3u" for r in record["channels"]))
        self.assertTrue(all(r["tvgId"] == nauta_reference.channel_id(r["name"].removesuffix(" [Nauta]")) for r in record["channels"]))

    @live_catalog
    def test_requested_deletions_are_tombstoned_absent_and_other_numbers_preserved(self):
        record = json.loads((ROOT/"contracts/nauta-247-cleanup-20261008.json").read_text(encoding="utf-8"))
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        removed = authorized_followup_deletions()
        self.assertEqual(75, len(removed))
        self.assertTrue(removed.issubset(layout["excludedM3u"]))
        self.assertTrue(removed.issubset(presentation["excluded_m3u"]))
        self.assertTrue(removed.isdisjoint({r.get("tvgId") for r in layout["channels"]}))
        self.assertTrue(removed.isdisjoint(presentation["trial_m3u"]))
        self.assertTrue(all(removed.isdisjoint(order) for order in presentation["orders"].values()))
        self.assertEqual(len(selected_nauta_rows(layout)),
                         sum(r["kind"] == "m3u" and r["sourceList"] == "1.m3u" and r["tvgId"].endswith("@Nauta")
                             for r in layout["channels"]))
        self.assertFalse(any((r.get("tvgId") or "").endswith("@Nauta") and "24/7" in r.get("name", "") for r in layout["channels"]))
        expected_numbers = {r["tvgId"]: r["number"] for r in record["preservedRows"]}
        unselected = previously_listed_nauta_ids()
        selected = selected_nauta_rows(layout)
        current_by_id = {r.get("tvgId"): r for r in layout["channels"]}
        # Una baja posterior del usuario conserva el número que tenía; se compara contra la base.
        trashed = catalog_baseline.user_trashed_ids(layout)
        base_by_id = {r.get("tvgId"): r for r in catalog_baseline.BASELINE["layout"]["channels"]}
        self.assertEqual({id: base_by_id[id]["number"] if id in trashed else
                          number + (1 if 37 <= number <= 93 and current_by_id[id]["state"] == "active" else 0)
                          for id, number in expected_numbers.items()
                          if id not in unselected and id not in selected},
                         {r["tvgId"]: r["number"] for r in layout["channels"]
                          if r.get("tvgId") in expected_numbers and r.get("tvgId") not in selected})
        for file in ["1.m3u", "m3u.m3u", "channel-catalog.m3u"]:
            found = {c.tvg_id for c in runner.parse_channels((ROOT/file).read_text(encoding="utf-8").splitlines())}
            self.assertTrue(removed.isdisjoint(found))
            self.assertEqual((ROOT/"m3u.m3u").read_bytes(), (ROOT/"1.m3u").read_bytes())

    def test_nauta_followup_delete_manifest_has_no_secret_material(self):
        record = json.loads((ROOT/"contracts/nauta-247-cleanup-20261008.json").read_text(encoding="utf-8"))
        self.assertEqual(75, len(record["channels"]))
        text = json.dumps(record)
        for secret in [".m3u8", "http://", "https://", "Authorization", "Cookie", "token=", "sourceUrl"]:
            self.assertNotIn(secret, text)
