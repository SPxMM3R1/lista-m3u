import json
import unittest
from pathlib import Path

import update_m3u as runner


ROOT = Path(__file__).resolve().parents[1]
CANAL13_DIRECT_BACKUPS = [
    # 11c6a7ff…, 12d30345…, 2be18242… y 711575de… pasaron a backups.json el 2026-10-25
    # (audio dudoso 0,48; respaldo por decisión del usuario).
    # 79f8514f… (Canal 13 HD, 135 de Lista 2) pasó a backups.json el 2026-10-25 por pedido
    # del usuario; ya no es canal independiente.
    # PublicDirect.8baa0cba… (Canal 13 HD 190.108.91.206) pasó a backups.json el 2026-10-25:
    # segunda búsqueda de clones, misma señal por audio (0.988).
]
class ExplicitDirectBackupLinksTest(unittest.TestCase):
    EXPECTED = {
        "0107": CANAL13_DIRECT_BACKUPS,
        # A&E (PublicDirect.d9973a3b… y su ex respaldo 19fbfbd8…) salió el 2026-10-29: el usuario
        # pidió «elimina todos los a&e».
        "PublicDirect.8918c13cf06dc2f7416879f2": [
            "AMC.co@Direct181",
            "PublicDirect.5c8f98d3876cb07b0c0884f6",
        ],
        "PublicDirect.e6a2bc5a013c1c5b9656d441": [
            "PublicDirect.21d595905b477139407f7250",
        ],
        # AXN 842 (PublicDirect.1162bcbc…) salió de esta lista el 2026-10-25: el usuario lo pasó a
        # backups.json como respaldo del AXN de Lista 1. Su antiguo respaldo (AXN 210) sigue activo.
        "PublicDirect.9840c70e010eb35fb900c6b4": [
            "Cinecanal.co@Direct181",
        ],
    }

    def test_former_direct_backups_are_independent_list_2_channels(self):
        # 2026-10-22, pedido del usuario: «Pasa todos los respaldos directos a la lista 2. Deja
        # solo los respaldos que sean de TvVoo» / «pásalos como canales independientes».
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = {row["tvgId"]: row for row in layout["channels"] if row.get("tvgId")}
        active = [row for row in layout["channels"] if row.get("state") == "active"]
        self.assertFalse([row["tvgId"] for row in active if row.get("backupm3u")])
        self.assertFalse([row["tvgId"] for row in active if row.get("preferredM3u")])
        main_ids = {channel.tvg_id for channel in runner.parse_channels(
            (ROOT / "m3u.m3u").read_text(encoding="utf-8").splitlines())}
        external_ids = {channel.tvg_id for channel in runner.parse_channels(
            (ROOT / "m3u-externa.m3u").read_text(encoding="utf-8").splitlines())}
        for primary_id, former in self.EXPECTED.items():
            with self.subTest(primary=primary_id):
                self.assertEqual("active", rows[primary_id]["state"])
                for backup_id in former:
                    backup = rows[backup_id]
                    self.assertEqual("active", backup["state"])
                    self.assertEqual("2.m3u", backup["sourceList"])
                    self.assertIn(backup_id, external_ids)
                    self.assertNotIn(backup_id, main_ids)


class EspnChilePlacementTest(unittest.TestCase):
    TARGET_ID = "ESPN.co@Direct181"

    def test_espn_is_after_tnt_sports_4_at_the_matching_number(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = [row for row in layout["channels"] if row.get("state") == "active"]
        target = next(row for row in rows if row.get("tvgId") == self.TARGET_ID)
        tnt4 = next(row for row in rows if row.get("kind") == "provider" and row.get("displayName") == "TNT Sports 4")
        ordered = sorted(rows, key=lambda row: row["order"])
        # 2026-10-25: TNT Sports Premium (Chile) quedó en 30 (Lista 1).
        self.assertEqual(33, target["number"])
        self.assertEqual(29, tnt4["number"])
        self.assertEqual("ESPN", target["displayName"])
        # Tras TNT Sports 4 quedan TNT Sports Premium (Chile) (30) y los dos Eurosport España (31/32), y luego ESPN.
        self.assertEqual(target, ordered[ordered.index(tnt4) + 4])
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

    def test_espn_2_feeds_are_independent_at_33_and_in_list_2(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = [row for row in layout["channels"] if row.get("state") == "active"]
        target = next(row for row in rows if row.get("tvgId") == self.TARGET_ID)
        second_feed = next(row for row in rows if row.get("tvgId") == "ESPN2.co@Direct181")
        espn = next(row for row in rows if row.get("tvgId") == self.ESPN_ID)
        ordered = sorted(rows, key=lambda row: row["order"])
        # 2026-10-25: TNT Sports Premium (Chile) y el 135 movidos; ESPN 2 bajó a 34 y ESPN a 33.
        self.assertEqual(34, target["number"])
        self.assertEqual(33, espn["number"])
        self.assertEqual("ESPN 2", target["displayName"])
        # 2026-10-22: sin respaldos directos (pasaron a Lista 2 como canales independientes).
        self.assertFalse(target.get("backupm3u"))
        # Renumeración sin huecos (2026-10-18): la segunda señal sigue en la Lista 2, después de
        # los 56 canales de la Lista 1.
        self.assertEqual("2.m3u", second_feed["sourceList"])
        self.assertGreater(second_feed["number"], 56)
        # La limpieza de Lista 2 (2026-10-18) quitó "HD" del nombre visible; la
        # independencia sigue garantizada por la identidad estable (tvg-id).
        self.assertEqual("ESPN 2", second_feed["displayName"])
        self.assertEqual("active", second_feed["state"])
        self.assertFalse(any(second_feed["tvgId"] in row.get("backupm3u", []) for row in rows))
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

    def test_espn4_is_after_espn3_sur_at_number_35(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = [row for row in layout["channels"] if row.get("state") == "active"]
        target = next(row for row in rows if row.get("tvgId") == self.TARGET_ID)
        espn3 = next(row for row in rows if row.get("tvgId") == self.ESPN3_ID)
        ordered = sorted(rows, key=lambda row: row["order"])
        # Renumeración sin huecos (2026-10-18): el hueco del 37 desapareció.
        # 2026-10-25: corrido +1 por TNT Sports Premium (Chile) en Lista 1.
        self.assertEqual(36, target["number"])
        self.assertEqual(35, espn3["number"])
        self.assertEqual("ESPN 4", target["displayName"])
        self.assertEqual(target, ordered[ordered.index(espn3) + 1])
        self.assertEqual(len(rows), len({row["number"] for row in rows}))

        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        for playlist_name in ("1.m3u", "m3u.m3u"):
            order = presentation["orders"][playlist_name]
            target_index = order.index(self.TARGET_ID)
            self.assertEqual(self.ESPN3_ID, order[target_index - 1])
            channels = runner.parse_channels((ROOT / playlist_name).read_text(encoding="utf-8").splitlines())
            self.assertEqual("ESPN 4", next(channel.name for channel in channels if channel.tvg_id == self.TARGET_ID))


if __name__ == "__main__":
    unittest.main()
