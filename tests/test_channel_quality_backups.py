import json
import unittest
from pathlib import Path

import update_m3u as runner
import os

from catalog_approval import live_catalog  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_ESPN7 = "Nauta.52bb87a2e2911ed34f7ae3bc@Nauta"
OFFICIAL_ESPN1_AR = "Nauta.4dec2794ee77cb450b79aa5b@Nauta"
OFFICIAL_ESPN1_MX = "Nauta.267720adcfe18e0c87fca46c@Nauta"
OFFICIAL_MTV_LIVE = "Nauta.d6c4cf31e1a88709b605ac8f@Nauta"
ESPN1_BACKUPS = [
    "Nauta.dac26a78f5bdf111bc9b9ffc@Nauta",  # ESPN 1 | Sur
    "Nauta.81dc69c20557da0672921475@Nauta",  # ESPN 1 | Chile
]
# Primeras bajas desde la app (2026-10-11). Las siguientes, hechas desde la app o el editor,
# se leen del layout: cualquier fila «deleted» es una decisión del usuario y no rompe pruebas.
FIRST_APP_TRASHED_NAUTA = {
    "Nauta.6186c37c4a108ec7eb171697@Nauta",  # ESPN 2 | Sur
    "Nauta.d3d2698fec772d9095f5ed4d@Nauta",  # ESPN 1 | Colombia
    "Nauta.4ad5525f8e38f0915deaa561@Nauta",  # ESPN Deportes
    "Nauta.8297a7fa0389cc7cf1d200dd@Nauta",  # ESPN 3 | Mexico
}


def current_nauta_ids():
    snapshot = json.loads((ROOT / "contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
    restorations = json.loads((ROOT / "contracts/nauta-restoration-20261008-sports.json").read_text(encoding="utf-8"))
    followup = json.loads((ROOT / "contracts/nauta-247-cleanup-20261008.json").read_text(encoding="utf-8"))
    snapshot_ids = {row["tvgId"] for row in snapshot["channels"]}
    removed = {row["tvgId"] for row in audit["channels"] if row["decision"] == "remove"}
    removed -= {row["tvgId"] for row in restorations["channels"]}
    removed |= {row["tvgId"] for row in followup["channels"]}
    return snapshot_ids - removed


@live_catalog
class NautaChannelsAreOptInTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        cls.presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        cls.nauta_ids = current_nauta_ids()
        cls.selected_nauta = {
            row["tvgId"]: row for row in cls.layout["channels"]
            if str(row.get("tvgId", "")).startswith("Nauta.")
        }

    def test_unselected_nauta_remains_opt_in_and_only_approved_rows_are_official(self):
        self.assertEqual(353, len(self.nauta_ids))
        unselected = self.nauta_ids - self.selected_nauta.keys()
        self.assertTrue(unselected.isdisjoint(row.get("tvgId") for row in self.layout["channels"]))
        self.assertTrue(unselected.issubset(self.presentation["excluded_m3u"]))
        # These are publication exclusions, not trash/tombstones: the live Nauta tab
        # checks layout.excludedM3u, so previously active unselected rows remain selectable.
        self.assertTrue(unselected.isdisjoint(self.layout["excludedM3u"]))
        self.assertTrue(unselected.isdisjoint(self.presentation["trial_m3u"]))
        APP_TRASHED_NAUTA = {key for key, row in self.selected_nauta.items() if row["state"] == "deleted"}
        self.assertTrue(FIRST_APP_TRASHED_NAUTA <= APP_TRASHED_NAUTA)
        self.assertTrue(all(row["state"] == "active" and row["sourceList"] == "1.m3u"
                            for key, row in self.selected_nauta.items()
                            if key not in APP_TRASHED_NAUTA))
        self.assertTrue(all(self.selected_nauta[key]["sourceList"] == "1.m3u"
                            for key in APP_TRASHED_NAUTA))
        official = {OFFICIAL_ESPN7, OFFICIAL_ESPN1_AR, OFFICIAL_ESPN1_MX, OFFICIAL_MTV_LIVE}
        self.assertEqual(official, {key for key, row in self.selected_nauta.items() if "trial" not in row})
        self.assertEqual(self.selected_nauta.keys() - official - APP_TRASHED_NAUTA,
                         set(self.presentation["trial_m3u"]) & self.selected_nauta.keys())
        self.assertEqual("ESPN 7", self.selected_nauta[OFFICIAL_ESPN7]["displayName"])
        self.assertEqual(39, self.selected_nauta[OFFICIAL_ESPN7]["number"])
        self.assertEqual("logos/espn-7.png", self.selected_nauta[OFFICIAL_ESPN7]["logoOverride"])
        self.assertEqual("ESPN 7", self.presentation["names"][OFFICIAL_ESPN7])
        self.assertEqual("logos/espn-7.png", self.presentation["logos"][OFFICIAL_ESPN7])
        self.assertIn(OFFICIAL_ESPN7, {c.tvg_id for c in runner.main_playlist_channels()})
        self.assertIn(("co1", "ESPN.7.HD.co"), runner.epg_source_chain(OFFICIAL_ESPN7))
        rows = self.selected_nauta
        self.assertEqual("ESPN 1 Argentina", rows[OFFICIAL_ESPN1_AR]["displayName"])
        self.assertEqual("logos/espn.svg", rows[OFFICIAL_ESPN1_AR]["logoOverride"])
        self.assertEqual(33, rows[OFFICIAL_ESPN1_AR]["number"])
        self.assertEqual("ESPN 1 MX", rows[OFFICIAL_ESPN1_MX]["displayName"])
        self.assertEqual("logos/espn.svg", rows[OFFICIAL_ESPN1_MX]["logoOverride"])
        self.assertEqual(34, rows[OFFICIAL_ESPN1_MX]["number"])
        self.assertEqual("MTV Live", rows[OFFICIAL_MTV_LIVE]["displayName"])
        self.assertEqual("logos/tvvoo/mtv-live-hd-nl.png", rows[OFFICIAL_MTV_LIVE]["logoOverride"])
        self.assertEqual(52, rows[OFFICIAL_MTV_LIVE]["number"])
        self.assertEqual(("ar1", "Canal.ESPN.(Argentina).ar"),
                         runner.EPG_PROGRAMME_SOURCES[OFFICIAL_ESPN1_AR])
        self.assertEqual(("mx1", "ESPN.MX.mx"), runner.EPG_PROGRAMME_SOURCES[OFFICIAL_ESPN1_MX])
        self.assertEqual(("us2", "MTVLIVE.us2"), runner.EPG_PROGRAMME_SOURCES[OFFICIAL_MTV_LIVE])
        self.assertIn(("ar1", "Canal.ESPN.(Argentina).ar"), runner.epg_source_chain(OFFICIAL_ESPN1_AR))
        self.assertIn(("mx1", "ESPN.MX.mx"), runner.epg_source_chain(OFFICIAL_ESPN1_MX))
        self.assertIn(("us2", "MTVLIVE.us2"), runner.epg_source_chain(OFFICIAL_MTV_LIVE))
        self.assertEqual("ESPN 1 Argentina", self.presentation["names"][OFFICIAL_ESPN1_AR])
        self.assertEqual("ESPN 1 MX", self.presentation["names"][OFFICIAL_ESPN1_MX])
        self.assertEqual("MTV Live", self.presentation["names"][OFFICIAL_MTV_LIVE])
        self.assertEqual("logos/espn.svg", self.presentation["logos"][OFFICIAL_ESPN1_AR])
        self.assertEqual("logos/espn.svg", self.presentation["logos"][OFFICIAL_ESPN1_MX])
        self.assertEqual("logos/tvvoo/mtv-live-hd-nl.png", self.presentation["logos"][OFFICIAL_MTV_LIVE])
        self.assertEqual(
            APP_TRASHED_NAUTA,
            self.selected_nauta.keys() & set(self.presentation["excluded_m3u"]),
        )
        for order in self.presentation["orders"].values():
            self.assertTrue(unselected.isdisjoint(order))
        for filename in ["channel-catalog.m3u", "m3u.m3u", "1.m3u", "m3u-externa.m3u", "2.m3u"]:
            channels = runner.parse_channels((ROOT / filename).read_text(encoding="utf-8").splitlines())
            self.assertTrue(unselected.isdisjoint(channel.tvg_id for channel in channels), filename)
        self.assertEqual((ROOT / "m3u.m3u").read_bytes(), (ROOT / "1.m3u").read_bytes())

    def test_nauta_rows_are_explicit_and_only_user_linked_rows_are_backups(self):
        nauta_rows = [row for row in self.layout["channels"] if str(row.get("tvgId", "")).startswith("Nauta.")]
        self.assertEqual(set(self.selected_nauta), {row["tvgId"] for row in nauta_rows})
        rows = {row["tvgId"]: row for row in nauta_rows}
        parent = rows[OFFICIAL_ESPN1_AR]
        self.assertEqual(ESPN1_BACKUPS, parent["backupm3u"])
        self.assertTrue(all(rows[key].get("trial") is True for key in ESPN1_BACKUPS))
        self.assertFalse(any(key in runner.EPG_PROGRAMME_SOURCES for key in ESPN1_BACKUPS))
        self.assertEqual({OFFICIAL_ESPN1_AR}, {
            row["tvgId"] for row in self.layout["channels"]
            if any(str(backup).startswith("Nauta.") for backup in row.get("backupm3u", []))
        })

    def test_runner_materializes_only_explicit_editor_rows(self):
        lines = (ROOT / "channel-catalog.m3u").read_text(encoding="utf-8").splitlines()
        before = {channel.tvg_id for channel in runner.parse_channels(lines)}
        changed = runner.apply_editor_nauta_channels(lines)
        after = {channel.tvg_id for channel in runner.parse_channels(lines)}
        self.assertEqual(bool(self.selected_nauta.keys() - before), changed)
        self.assertEqual(self.selected_nauta.keys() - before, after - before)
        self.assertTrue((self.nauta_ids - self.selected_nauta.keys()).isdisjoint(after))

    def test_tvn_uses_only_its_official_row(self):
        rows = {
            row["tvgId"]: row for row in self.layout["channels"]
            if row.get("kind") == "m3u" and row.get("tvgId")
        }
        tvn = rows["0104"]
        self.assertEqual(1, tvn["number"])
        self.assertEqual("active", tvn["state"])
        self.assertFalse(tvn.get("preferredM3u"))
        self.assertFalse(tvn.get("backupm3u"))
        self.assertFalse(tvn.get("backupTvVoo"))
        playlist = (ROOT / "m3u.m3u").read_text(encoding="utf-8").splitlines()
        tvn_entry = next(line for line in playlist if line.startswith("#EXTINF") and 'tvg-id="0104"' in line)
        self.assertIn('x-resolver="tvn"', tvn_entry)

    def test_canal13_uses_only_its_official_row(self):
        rows = {
            row["tvgId"]: row for row in self.layout["channels"]
            if row.get("kind") == "m3u" and row.get("tvgId")
        }
        canal13 = rows["0107"]
        self.assertEqual("Canal 13", canal13["name"])
        self.assertEqual("active", canal13["state"])
        self.assertEqual("1.m3u", canal13["sourceList"])
        self.assertNotIn("preferredM3u", canal13)
        self.assertFalse(canal13.get("backupm3u"))
        self.assertFalse(canal13.get("backupTvVoo"))
        playlist = (ROOT / "m3u.m3u").read_text(encoding="utf-8").splitlines()
        canal13_index = next(index for index, line in enumerate(playlist)
                             if line.startswith("#EXTINF") and 'tvg-id="0107"' in line)
        self.assertEqual("https://redirector.dps.live/hls/13cl/playlist.m3u8", playlist[canal13_index + 1])

        former_backups = {
            "TVN.cl@Direct38b",
            "TVN.cl@Direct45",
            "Canal13.cl@Direct187",
            "T13EnVivo.cl@DPS",
        }
        self.assertTrue(former_backups.isdisjoint(rows))
        self.assertTrue(former_backups.issubset(self.layout["excludedM3u"]))
        self.assertTrue(former_backups.issubset(self.presentation["excluded_m3u"]))
        self.assertTrue(former_backups.issubset(runner.PERMANENTLY_REMOVED_CHANNEL_IDS))
        for filename in ["channel-catalog.m3u", "m3u.m3u", "1.m3u"]:
            active_ids = {channel.tvg_id for channel in runner.parse_channels(
                (ROOT / filename).read_text(encoding="utf-8").splitlines())}
            self.assertTrue(former_backups.isdisjoint(active_ids), filename)


class ExplicitDirectBackupLinksTest(unittest.TestCase):
    EXPECTED = {
        "PublicDirect.d9973a3bfb28634698473218": [
            "PublicDirect.19fbfbd8b220cd0fb65ac244",
        ],
        "PublicDirect.8918c13cf06dc2f7416879f2": [
            "AMC.co@Direct181",
            "PublicDirect.5c8f98d3876cb07b0c0884f6",
        ],
        "PublicDirect.e6a2bc5a013c1c5b9656d441": [
            "PublicDirect.21d595905b477139407f7250",
        ],
        "PublicDirect.1162bcbccc1aa298b25757a3": [
            "PublicDirect.07595a53d0527c27f68b4e29",
        ],
        "PublicDirect.9840c70e010eb35fb900c6b4": [
            "Cinecanal.co@Direct181",
        ],
        "PublicDirect.d6cca6d4aa23a69d50439c22": [
            "ESPN2.co@Direct181",
        ],
    }

    def test_requested_hd_rows_use_only_the_explicit_direct_backups(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = {row["tvgId"]: row for row in layout["channels"] if row.get("tvgId")}
        active_playlist_ids = {
            channel.tvg_id
            for channel in runner.parse_channels(
                (ROOT / "m3u.m3u").read_text(encoding="utf-8").splitlines()
            )
        }
        linked_ids = []

        for primary_id, backup_ids in self.EXPECTED.items():
            with self.subTest(primary=primary_id):
                primary = rows[primary_id]
                self.assertEqual("m3u", primary["kind"])
                self.assertEqual("active", primary["state"])
                self.assertEqual(backup_ids, primary["backupm3u"])
                self.assertIn(primary_id, active_playlist_ids)
                for backup_id in backup_ids:
                    backup = rows[backup_id]
                    self.assertEqual("m3u", backup["kind"])
                    self.assertEqual("active", backup["state"])
                    self.assertIn(backup_id, active_playlist_ids)
                    self.assertFalse(backup.get("backupm3u"), "no bidirectional backup cycle")
                    linked_ids.append(backup_id)

        self.assertEqual(len(linked_ids), len(set(linked_ids)))


class EspnChilePlacementTest(unittest.TestCase):
    TARGET_ID = "ESPN.co@Direct181"

    def test_espn_is_after_tnt_sports_4_at_the_matching_number(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = [row for row in layout["channels"] if row.get("state") == "active"]
        target = next(row for row in rows if row.get("tvgId") == self.TARGET_ID)
        tnt4 = next(row for row in rows if row.get("kind") == "provider" and row.get("displayName") == "TNT Sports 4")
        ordered = sorted(rows, key=lambda row: row["order"])
        self.assertEqual(33, target["number"])
        self.assertEqual(32, tnt4["number"])
        self.assertEqual("ESPN", target["displayName"])
        self.assertEqual(target, ordered[ordered.index(tnt4) + 1])
        self.assertEqual(len(rows), len({row["number"] for row in rows}))

        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertEqual("ESPN", presentation["names"][self.TARGET_ID])
        for playlist_name in ("1.m3u", "m3u.m3u", "channel-catalog.m3u"):
            order = presentation["orders"][playlist_name]
            target_index = order.index(self.TARGET_ID)
            if playlist_name != "channel-catalog.m3u":
                self.assertEqual("PublicDirect.d6cca6d4aa23a69d50439c22", order[target_index + 1])
            channels = runner.parse_channels((ROOT / playlist_name).read_text(encoding="utf-8").splitlines())
            self.assertEqual("ESPN", next(channel.name for channel in channels if channel.tvg_id == self.TARGET_ID))


class Espn2PlacementTest(unittest.TestCase):
    TARGET_ID = "PublicDirect.d6cca6d4aa23a69d50439c22"
    ESPN_ID = "ESPN.co@Direct181"

    def test_espn_2_464_is_after_espn_at_number_34(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = [row for row in layout["channels"] if row.get("state") == "active"]
        target = next(row for row in rows if row.get("tvgId") == self.TARGET_ID)
        espn = next(row for row in rows if row.get("tvgId") == self.ESPN_ID)
        ordered = sorted(rows, key=lambda row: row["order"])
        self.assertEqual(34, target["number"])
        self.assertEqual(33, espn["number"])
        self.assertEqual("ESPN 2", target["displayName"])
        self.assertEqual(["ESPN2.co@Direct181"], target["backupm3u"])
        self.assertEqual(target, ordered[ordered.index(espn) + 1])
        self.assertEqual(len(rows), len({row["number"] for row in rows}))

        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertEqual("ESPN 2", presentation["names"][self.TARGET_ID])
        for playlist_name in ("1.m3u", "m3u.m3u", "channel-catalog.m3u"):
            order = presentation["orders"][playlist_name]
            target_index = order.index(self.TARGET_ID)
            if playlist_name != "channel-catalog.m3u":
                self.assertEqual(self.ESPN_ID, order[target_index - 1])
            channels = runner.parse_channels((ROOT / playlist_name).read_text(encoding="utf-8").splitlines())
            self.assertEqual("ESPN 2", next(channel.name for channel in channels if channel.tvg_id == self.TARGET_ID))


class Espn4PlacementTest(unittest.TestCase):
    TARGET_ID = "ESPN4.co@Direct181"
    ESPN3_ID = "WinSports.co@Direct181"

    def test_espn4_166_is_after_espn3_sur_at_number_37(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = [row for row in layout["channels"] if row.get("state") == "active"]
        target = next(row for row in rows if row.get("tvgId") == self.TARGET_ID)
        espn3 = next(row for row in rows if row.get("tvgId") == self.ESPN3_ID)
        ordered = sorted(rows, key=lambda row: row["order"])
        self.assertEqual(37, target["number"])
        self.assertEqual(36, espn3["number"])
        self.assertEqual("ESPN 4 HD", target["displayName"])
        self.assertEqual(target, ordered[ordered.index(espn3) + 1])
        self.assertNotIn(166, {row["number"] for row in rows})
        self.assertEqual(len(rows), len({row["number"] for row in rows}))

        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        for playlist_name in ("1.m3u", "m3u.m3u"):
            order = presentation["orders"][playlist_name]
            target_index = order.index(self.TARGET_ID)
            self.assertEqual(self.ESPN3_ID, order[target_index - 1])
            channels = runner.parse_channels((ROOT / playlist_name).read_text(encoding="utf-8").splitlines())
            self.assertEqual("ESPN 4 HD", next(channel.name for channel in channels if channel.tvg_id == self.TARGET_ID))


if __name__ == "__main__":
    unittest.main()
