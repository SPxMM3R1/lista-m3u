import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import update_m3u


def channel(name: str, tvg_id: str) -> update_m3u.Channel:
    return update_m3u.Channel(
        name=name,
        url="tvvoo://channel/example",
        url_line=1,
        tvg_id=tvg_id,
        display_name=name,
        stream_format="reference",
    )


class TvVooEpgAliasTests(unittest.TestCase):
    def test_shared_source_is_copied_to_legacy_and_stable_ids(self) -> None:
        legacy_id = "LegacyTvVoo.uk@TvVoo"
        stable_id = "unitedkingdom|vavoo_EXAMPLE%7Cgroup%3Auk@TvVoo"
        source_key = ("test-source", "legacy-channel")
        previous_legacy = update_m3u.EPG_PROGRAMME_SOURCES.get(legacy_id)
        previous_stable = update_m3u.EPG_PROGRAMME_SOURCES.get(stable_id)
        update_m3u.EPG_PROGRAMME_SOURCES[legacy_id] = source_key
        update_m3u.EPG_PROGRAMME_SOURCES[stable_id] = source_key
        now = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
        source = b'''<?xml version="1.0" encoding="utf-8"?>
<tv><channel id="legacy-channel"><display-name>Example</display-name></channel>
<programme channel="legacy-channel" start="20260919130000 +0000" stop="20260919140000 +0000">
  <title>Example programme</title>
</programme></tv>'''
        try:
            output, status = update_m3u.build_epg(
                {source_key[0]: source},
                [channel("Example", legacy_id), channel("Example", stable_id)],
                {},
                now=now,
            )
        finally:
            if previous_legacy is None:
                update_m3u.EPG_PROGRAMME_SOURCES.pop(legacy_id, None)
            else:
                update_m3u.EPG_PROGRAMME_SOURCES[legacy_id] = previous_legacy
            if previous_stable is None:
                update_m3u.EPG_PROGRAMME_SOURCES.pop(stable_id, None)
            else:
                update_m3u.EPG_PROGRAMME_SOURCES[stable_id] = previous_stable

        root = ET.fromstring(output)
        programmes = root.findall("programme")
        self.assertEqual({legacy_id, stable_id}, {item.get("channel") for item in programmes})
        legacy_programmes = sum(item.get("channel") == legacy_id for item in programmes)
        stable_programmes = sum(item.get("channel") == stable_id for item in programmes)
        self.assertGreater(legacy_programmes, 0)
        self.assertEqual(legacy_programmes, stable_programmes)
        self.assertEqual("test-source", status["guide_sources"][stable_id])


if __name__ == "__main__":
    unittest.main()
