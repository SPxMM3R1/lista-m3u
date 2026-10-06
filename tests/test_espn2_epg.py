"""ESPN 2 Sur: exact regional guide, UTC times and stable app identity."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import update_m3u

TARGETS = ("Vavoo.es.ESPN2@TvVoo", "Vavoo.ar.ESPN2@TvVoo")
SOURCE = "[ESP2LS].ESPN.2.uy"
ES_ALIAS = "vavoo_ESPN%202%7Cgroup%3Aes"
AR_ALIAS = "vavoo_ESPN%202%7Cgroup%3Aar"
APP_ID = f"spain|{ES_ALIAS}@TvVoo"
SLOTS = (
    ("20261006204500 +0000", "20261006214500 +0000", "ESPN Compact",
     "Los momentos más destacados de la final masculina del Premier Pádel P2, 2026 en Róterdam."),
    ("20261006214500 +0000", "20261006220000 +0000", "F2: Chasing the Dream", "Bakú"),
)


def channel(target):
    return update_m3u.Channel(name="ESPN 2", display_name="ESPN 2",
                              tvg_id=target, url="https://example.invalid/live.m3u8", url_line=0)


def guide(source, titles=None):
    root = ET.Element("tv")
    for index, (start, stop, title, description) in enumerate(SLOTS):
        p = ET.SubElement(root, "programme", {"channel": source, "start": start, "stop": stop})
        ET.SubElement(p, "title", {"lang": "es"}).text = titles[index] if titles else title
        ET.SubElement(p, "desc", {"lang": "es"}).text = description
    return root


class Espn2EpgTest(unittest.TestCase):
    def test_both_resolver_aliases_use_exact_sur_entry_without_unverified_regional_backup(self):
        for target in TARGETS:
            with self.subTest(target=target):
                self.assertEqual(("uy1", SOURCE), update_m3u.EPG_PROGRAMME_SOURCES[target])
                chain = update_m3u.epg_source_chain(target)
                self.assertIn(("uy1", SOURCE), chain)
                self.assertNotIn(("cl", "Canal.ESPN.2.(Chile).cl"), chain)
                self.assertNotIn(("ar1", "Canal.ESPN.2.(Bolivia).ar"), chain)
                self.assertNotIn(("uy1", "ESPN.2.HD.uy"), chain)
                self.assertEqual(frozenset({"uy1"}), update_m3u.epgshare_source_names_for([channel(target)]))

    def build(self):
        fresh = guide(SOURCE)
        fresh.extend(guide("ESPN.2.HD.uy", ["Tenis ATP", "Tenis ATP"]))
        previous = ET.Element("tv")
        for target in TARGETS:
            previous.extend(guide(target, ["UEFA Nations League Highlights", "Fútbol internacional"]))
        return update_m3u.build_epg(
            {"uy1": ET.tostring(fresh),
             "cl": ET.tostring(guide("Canal.ESPN.2.(Chile).cl", ["Fútbol", "Fútbol"])),
             update_m3u.PUBLISHED_EPG_FALLBACK_SOURCE: ET.tostring(previous)},
            [channel(target) for target in TARGETS], {},
            now=datetime(2026, 10, 6, 21, 20, tzinfo=timezone.utc))

    def test_fresh_sur_guide_replaces_wrong_football_and_preserves_description_and_times(self):
        output, status = self.build()
        root = ET.fromstring(output)
        self.assertEqual(4, len(root.findall("programme")))
        for target in TARGETS:
            self.assertEqual("uy1", status["guide_sources"][target])
            programmes = root.findall(f"programme[@channel='{target}']")
            self.assertEqual(2, len(programmes))
            for p, (start, stop, title, description) in zip(programmes, SLOTS):
                self.assertEqual(title, p.findtext("title"))
                self.assertEqual(description, p.findtext("desc"))
                self.assertEqual(update_m3u.xmltv_datetime(start), update_m3u.xmltv_datetime(p.get("start")))
                self.assertEqual(update_m3u.xmltv_datetime(stop), update_m3u.xmltv_datetime(p.get("stop")))

    def test_sur_guide_reaches_stable_app_id_without_duplicate_or_identity_change(self):
        output, _ = self.build()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "channel-catalog.m3u"
            catalog.write_text("#EXTM3U\n" + "".join(
                f'#EXTINF:-1 tvg-id="{target}" x-resolver="tvvoo" x-resolver-ids="{alias}",ESPN 2\n'
                "https://example.invalid/live.m3u8\n"
                for target, alias in zip(TARGETS, (ES_ALIAS, AR_ALIAS))), encoding="utf-8")
            selection = root / "selection.json"
            selection.write_text(json.dumps({"schemaVersion": 1, "sources": [{
                "provider": "tvvoo", "enabled": True, "channels": [{
                    "provider": "tvvoo", "catalogKey": f"spain|{ES_ALIAS}",
                    "providerResourceId": f"spain|{ES_ALIAS}", "countryKey": "spain",
                    "identityState": "canonical", "name": "ESPN 2", "group": "España", "order": 1,
                    "aliases": [ES_ALIAS, AR_ALIAS], "resolverAliases": [ES_ALIAS, AR_ALIAS],
                }],
            }]}), encoding="utf-8")
            aliased = update_m3u.add_app_epg_aliases(output, catalog, selection)
            published = ET.fromstring(aliased)
            programmes = published.findall(f"programme[@channel='{APP_ID}']")
            self.assertEqual(2, len(programmes))
            self.assertEqual("ESPN Compact", programmes[0].findtext("title"))
            self.assertIn("Premier Pádel", programmes[0].findtext("desc"))
            self.assertEqual(aliased, update_m3u.add_app_epg_aliases(aliased, catalog, selection))


if __name__ == "__main__":
    unittest.main()
