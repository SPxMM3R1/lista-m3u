import json
import unittest
from datetime import datetime, timezone

import publish_epg

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def guide(programmes: list[tuple[str, str, str]], generated: str = "a", extra: str = "") -> bytes:
    body = "".join(
        f'<programme start="{start} +0000" stop="{stop} +0000" channel="c"><title>{title}</title></programme>'
        for start, stop, title in programmes
    )
    return (f'<?xml version="1.0"?><tv data-generated-at="{generated}" {extra}>'
            f'<channel id="c"><display-name>C</display-name></channel>{body}</tv>').encode()


PAST = ("20261015080000", "20261015090000", "Pasado")
NOW_ON = ("20261015110000", "20261015130000", "Ahora")
LATER = ("20261015130000", "20261015140000", "Luego")


class PublishEpgTest(unittest.TestCase):
    def test_dropping_only_ended_programmes_is_prune_only(self) -> None:
        old = guide([PAST, NOW_ON, LATER], generated="a")
        new = guide([NOW_ON, LATER], generated="b")
        self.assertTrue(publish_epg.is_prune_only(old, new, NOW))

    def test_new_or_changed_programmes_are_published(self) -> None:
        old = guide([PAST, NOW_ON])
        self.assertFalse(publish_epg.is_prune_only(old, guide([NOW_ON, LATER]), NOW))
        changed = ("20261015130000", "20261015140000", "Otro")
        self.assertFalse(publish_epg.is_prune_only(guide([NOW_ON, LATER]), guide([NOW_ON, changed]), NOW))

    def test_removing_a_running_or_future_programme_is_published(self) -> None:
        old = guide([PAST, NOW_ON, LATER])
        self.assertFalse(publish_epg.is_prune_only(old, guide([PAST, LATER]), NOW))
        self.assertFalse(publish_epg.is_prune_only(old, guide([PAST, NOW_ON]), NOW))

    def test_channel_or_root_changes_are_published(self) -> None:
        old = guide([PAST, NOW_ON])
        self.assertFalse(publish_epg.is_prune_only(old, guide([NOW_ON], extra='data-x="1"'), NOW))
        renamed = guide([NOW_ON]).replace(b"<display-name>C<", b"<display-name>D<")
        self.assertFalse(publish_epg.is_prune_only(old, renamed, NOW))

    def test_unparseable_guide_is_published(self) -> None:
        self.assertFalse(publish_epg.is_prune_only(b"<tv>", guide([NOW_ON]), NOW))

    def test_index_only_timestamp(self) -> None:
        before = json.dumps({"schema": 1, "generatedAt": "a", "channels": [{"id": "c"}]}).encode()
        after = json.dumps({"schema": 1, "generatedAt": "b", "channels": [{"id": "c"}]}).encode()
        other = json.dumps({"schema": 1, "generatedAt": "b", "channels": [{"id": "d"}]}).encode()
        self.assertTrue(publish_epg.index_only_timestamp_changed(before, after))
        self.assertFalse(publish_epg.index_only_timestamp_changed(before, other))


if __name__ == "__main__":
    unittest.main()
