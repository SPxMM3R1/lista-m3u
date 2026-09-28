import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import update_m3u

NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


class OfficialEpgSourcesTest(unittest.TestCase):
    """Cada fuente EPG oficial vive en epg_sources/ y falla sola."""

    def test_every_source_has_its_fetch_function(self) -> None:
        names = [source.name for source in update_m3u.OFFICIAL_EPG_SOURCES]
        self.assertEqual(len(names), len(set(names)))
        for source in update_m3u.OFFICIAL_EPG_SOURCES:
            fetch = getattr(update_m3u, source.fetch)
            self.assertTrue(fetch.__module__.startswith("epg_sources."), source.fetch)

    def test_a_crashing_source_does_not_stop_the_others(self) -> None:
        def quiet(*_args):
            return None, None

        patches = [
            patch.object(update_m3u, source.fetch, side_effect=quiet)
            for source in update_m3u.OFFICIAL_EPG_SOURCES
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        with patch.object(
            update_m3u, "fetch_tvn_official_epg", side_effect=RuntimeError("caida")
        ), patch.object(
            update_m3u, "fetch_la_red_official_epg", return_value=(b"<tv/>", None)
        ):
            documents, errors = update_m3u.fetch_official_epg_sources([], NOW)

        self.assertEqual({update_m3u.LA_RED_OFFICIAL_EPG_SOURCE: b"<tv/>"}, documents)
        self.assertEqual(
            {update_m3u.TVN_OFFICIAL_EPG_SOURCE: "RuntimeError: caida"}, errors
        )

    def test_la_red_replaces_only_its_listed_sources(self) -> None:
        lookup = {
            ("cl", "Canal.La.Red.(Chile).cl"): {"0102"},
            (update_m3u.ZAPPING_EPG_SOURCE, "0102"): {"0102"},
            ("otra", "compartida"): {"0102", "0999"},
        }
        update_m3u.prefer_official_epg_sources(
            lookup, [update_m3u.LA_RED_OFFICIAL_EPG_SOURCE], {"0102", "0999"}
        )
        self.assertEqual(
            {
                ("otra", "compartida"): {"0102", "0999"},
                (update_m3u.LA_RED_OFFICIAL_EPG_SOURCE, "0102"): {"0102"},
            },
            lookup,
        )

    def test_exclusive_source_replaces_every_other_source_of_the_channel(self) -> None:
        lookup = {("cl", "TVN"): {"0104"}, ("cl", "Mega"): {"0105"}}
        update_m3u.prefer_official_epg_sources(
            lookup, [update_m3u.TVN_OFFICIAL_EPG_SOURCE], {"0104", "0105"}
        )
        self.assertEqual(
            {
                ("cl", "Mega"): {"0105"},
                (update_m3u.TVN_OFFICIAL_EPG_SOURCE, "0104"): {"0104"},
            },
            lookup,
        )

    def test_unavailable_source_keeps_the_fallback(self) -> None:
        lookup = {("cl", "TVN"): {"0104"}}
        update_m3u.prefer_official_epg_sources(lookup, [], {"0104"})
        self.assertEqual({("cl", "TVN"): {"0104"}}, lookup)


if __name__ == "__main__":
    unittest.main()
