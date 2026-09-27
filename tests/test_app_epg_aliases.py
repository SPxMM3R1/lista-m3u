import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import update_m3u

ALIAS = "vavoo_DAZN%20F1%7Cgroup%3Aes"
APP_ID = f"spain|{ALIAS}@TvVoo"


class AppEpgAliasesTest(unittest.TestCase):
    """La app busca la guía TvVoo con ``countryKey|alias@TvVoo``; la EPG usa el tvg-id del catálogo."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.catalog = root / "channel-catalog.m3u"
        self.catalog.write_text(
            "#EXTM3U\n"
            f'#EXTINF:-1 tvg-id="DAZNF1.es@TvVoo" x-resolver="tvvoo" x-resolver-ids="{ALIAS}",DAZN F1\n'
            "http://example.test/dazn\n",
            encoding="utf-8",
        )
        channel = {
            "provider": "tvvoo", "catalogKey": f"spain|{ALIAS}", "providerResourceId": f"spain|{ALIAS}",
            "name": "DAZN F1", "group": "España", "identityState": "canonical", "order": 1,
            "countryKey": "spain", "aliases": [ALIAS],
        }
        orphan = dict(channel, catalogKey="spain|vavoo_SIN%7Cgroup%3Aes",
                      providerResourceId="spain|vavoo_SIN%7Cgroup%3Aes", name="Sin catálogo",
                      aliases=["vavoo_SIN%7Cgroup%3Aes"], order=2)
        self.selection = root / "vibem3u-selection.json"
        self.selection.write_text(json.dumps({
            "schemaVersion": 1,
            "sources": [{"provider": "tvvoo", "enabled": True, "channels": [channel, orphan]}],
        }), encoding="utf-8")
        self.epg = (
            b'<?xml version="1.0" encoding="utf-8"?><tv>'
            b'<channel id="DAZNF1.es@TvVoo"><display-name>DAZN F1</display-name></channel>'
            b'<programme channel="DAZNF1.es@TvVoo" start="20260927120000 -0300" stop="20260927130000 -0300">'
            b'<title>Clasificacion</title></programme></tv>'
        )

    def test_copies_guide_under_the_app_id_only_for_confirmed_matches(self) -> None:
        output = update_m3u.add_app_epg_aliases(self.epg, self.catalog, self.selection)
        root = ET.fromstring(output)

        ids = [channel.get("id") for channel in root.findall("channel")]
        self.assertEqual(["DAZNF1.es@TvVoo", APP_ID], ids)
        titles = [p.findtext("title") for p in root.findall(f"programme[@channel='{APP_ID}']")]
        self.assertEqual(["Clasificacion"], titles)
        self.assertNotIn("spain|vavoo_SIN%7Cgroup%3Aes@TvVoo", ids)

    def test_scope_filter_keeps_aliases_of_allowed_channels(self) -> None:
        output = update_m3u.add_app_epg_aliases(self.epg, self.catalog, self.selection)

        filtered, _ = update_m3u.filter_epg_to_channel_ids(output, {"DAZNF1.es@TvVoo"})
        self.assertIn(APP_ID, {c.get("id") for c in ET.fromstring(filtered).findall("channel")})

        dropped, _ = update_m3u.filter_epg_to_channel_ids(output, {"OtroCanal"})
        self.assertEqual([], ET.fromstring(dropped).findall("channel"))

    def test_is_idempotent(self) -> None:
        once = update_m3u.add_app_epg_aliases(self.epg, self.catalog, self.selection)
        twice = update_m3u.add_app_epg_aliases(once, self.catalog, self.selection)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
