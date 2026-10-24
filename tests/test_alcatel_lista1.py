import json
import unittest
from pathlib import Path

import update_m3u as runner


ROOT = Path(__file__).resolve().parents[1]

ALCATEL_LISTA1 = {
    "PublicDirect.a247897d9a490d19fa633661": {
        "name": "AXN",
        "logo": "logos/catalogue/axnlatinamerica-us.png",
        "trial": True,
    },
    "PublicDirect.39057ce89326a34e33998e2e": {
        "name": "History Channel 2",
        "logo": "logos/catalogue/history2latinamerica-us.png",
        "trial": False,
    },
    "PublicDirect.8da65ba545fa9fd2512f9901": {
        "name": "History Channel",
        "logo": "logos/catalogue/history-channel-lam.png",
        "trial": False,
    },
    "PublicDirect.9c28a0d10a09856e98930cdc": {
        "name": "Sony Channel",
        "logo": "logos/catalogue/sonychannelandes-us.png",
        "trial": False,
    },
    "PublicDirect.376c74e4d0452f743fd2c811": {
        "name": "Sony Movies",
        "logo": "logos/catalogue/sonymovieslatinamerica-us.png",
        # 2026-10-21: definitivo para recibir guía (Claro Argentina), a pedido.
        "trial": False,
    },
    "PublicDirect.8b604de41196cd4fe991d551": {
        "name": "Studio Universal",
        "logo": "logos/catalogue/studiouniversallatinamerica-white.png",
        "trial": False,
    },
    "PublicDirect.12addda8ba8591c579cdebfa": {
        "name": "Telehit",
        "logo": "logos/catalogue/telehit-mx.png",
        "trial": False,
    },
    "PublicDirect.bf407e29eec656d628dfa2d7": {
        "name": "Universal TV",
        "logo": "logos/catalogue/universaltvlatinamerica-us.png",
        "trial": False,
    },
    "PublicDirect.1701b6c4abbcc431fb481536": {
        "name": "USA Network",
        "logo": "logos/catalogue/usa-network-us.svg",
        "trial": False,
    },
}

EPG_OVERRIDES = {
    "PublicDirect.39057ce89326a34e33998e2e": ("pa1", "Canal.History.2.(Panamá).pa"),
    "PublicDirect.8da65ba545fa9fd2512f9901": ("pa1", "Canal.History.(Panamá).pa"),
    "PublicDirect.9c28a0d10a09856e98930cdc": ("pa1", "Canal.Sony.(Panamá).pa"),
    "PublicDirect.8b604de41196cd4fe991d551": ("pa1", "Canal.Studio.Universal.(Panamá).pa"),
    "PublicDirect.12addda8ba8591c579cdebfa": ("mx1", "Canal.Telehit.mx"),
    "PublicDirect.bf407e29eec656d628dfa2d7": ("pa1", "Canal.Universal.TV.(Panamá).pa"),
    "PublicDirect.1701b6c4abbcc431fb481536": ("pa1", "Canal.USA.Network.(Panamá).pa"),
}


class AlcatelLista1Test(unittest.TestCase):
    def test_requested_channels_have_clean_names_logos_and_expected_epg_state(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = {row["tvgId"]: row for row in layout["channels"] if row.get("tvgId")}
        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        epg = json.loads((ROOT / "epg-overrides.json").read_text(encoding="utf-8"))["channels"]

        for channel_id, expected in ALCATEL_LISTA1.items():
            with self.subTest(channel=channel_id):
                row = rows[channel_id]
                self.assertEqual("1.m3u", row["sourceList"])
                self.assertEqual("active", row["state"])
                self.assertEqual(expected["name"], row["displayName"])
                self.assertEqual(expected["name"], presentation["names"][channel_id])
                self.assertEqual(expected["logo"], row["logoPath"])
                self.assertEqual(expected["logo"], presentation["logos"][channel_id])
                self.assertTrue((ROOT / expected["logo"]).is_file())
                self.assertEqual(expected["trial"], row.get("trial", False))
                self.assertEqual(expected["trial"], channel_id in presentation["trial_m3u"])

        # 2026-10-24: guía Claro elegida con fotograma; la anterior queda de respaldo.
        for channel_id, (source, source_id) in EPG_OVERRIDES.items():
            self.assertEqual("claro-guia", epg[channel_id]["source"])
            self.assertEqual({"source": source, "source_id": source_id}, epg[channel_id]["backup"])
        # AXN #57: guía Claro Argentina (Criminal Minds) verificada con el fotograma.
        self.assertEqual("claro-guia", epg["PublicDirect.a247897d9a490d19fa633661"]["source"])
        self.assertNotIn("PublicDirect.376c74e4d0452f743fd2c811", epg)

    def test_telehit_and_requested_rows_are_ordered_in_lista1_only(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = {row["tvgId"]: row for row in layout["channels"] if row.get("tvgId")}
        telehit_musica = rows["TelehitMusica.mx@SD"]
        telehit = rows["PublicDirect.12addda8ba8591c579cdebfa"]
        # 2026-10-21: RWND pasó al primer lugar de Música (#41) y Telehit bajó uno.
        self.assertEqual(49, telehit["number"])
        self.assertEqual(50, telehit_musica["number"])
        self.assertEqual(telehit["number"] + 1, telehit_musica["number"])
        self.assertEqual("Telehit Música", telehit_musica["displayName"])
        # 2026-10-21: logo blanco «TELEHIT MÚSICA» (el que se usaba hasta el 20-10), a pedido.
        self.assertEqual("logos/telehit-musica-mx.png", telehit_musica["logoPath"])

        main_ids = {
            channel.tvg_id
            for channel in runner.parse_channels((ROOT / "m3u.m3u").read_text(encoding="utf-8").splitlines())
        }
        external_ids = {
            channel.tvg_id
            for channel in runner.parse_channels((ROOT / "m3u-externa.m3u").read_text(encoding="utf-8").splitlines())
        }
        self.assertTrue(set(ALCATEL_LISTA1).issubset(main_ids))
        self.assertTrue(set(ALCATEL_LISTA1).isdisjoint(external_ids))
        self.assertIn("TelehitMusica.mx@SD", main_ids)
        self.assertNotIn("PublicDirect.a8ae71c151a6f81599bff876", external_ids)

    def test_telehit_musica_uses_the_former_backup_as_its_only_source(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = {row["tvgId"]: row for row in layout["channels"] if row.get("tvgId")}
        primary = rows["TelehitMusica.mx@SD"]
        backup_id = "PublicDirect.a8ae71c151a6f81599bff876"
        backup = rows[backup_id]
        self.assertNotIn("backupm3u", primary)
        self.assertEqual("1.m3u", primary["sourceList"])
        self.assertEqual("2.m3u", backup["sourceList"])
        self.assertEqual("active", primary["state"])
        self.assertEqual("deleted", backup["state"])
        self.assertIs(backup.get("trial"), True)
        self.assertEqual("Telehit Música", backup["displayName"])
        self.assertEqual("logos/catalogue/telehitmusica-mx.png", backup["logoPath"])

        canonical = {
            channel.tvg_id: channel
            for channel in runner.parse_channels(
                (ROOT / "channel-catalog.m3u").read_text(encoding="utf-8").splitlines()
            )
        }
        self.assertEqual(canonical[backup_id].url, canonical["TelehitMusica.mx@SD"].url)
        self.assertEqual("logos/telehit-musica-mx.png", primary["logoPath"])


if __name__ == "__main__":
    unittest.main()
