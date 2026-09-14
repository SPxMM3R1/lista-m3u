import unittest
from unittest.mock import patch

import update_m3u


CLEAR_MPD = b'''<?xml version="1.0" encoding="utf-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="dynamic">
  <BaseURL>https://cdn.example/live/</BaseURL>
  <Period>
    <AdaptationSet contentType="audio" mimeType="audio/mp4">
      <SegmentTemplate timescale="1" initialization="init-$RepresentationID$.mp4" media="a-$Time$.m4s">
        <SegmentTimeline><S t="100" d="5" r="1" /></SegmentTimeline>
      </SegmentTemplate>
      <Representation id="audio" bandwidth="128000" />
    </AdaptationSet>
    <AdaptationSet contentType="video" mimeType="video/mp4">
      <SegmentTemplate timescale="1" initialization="init-$RepresentationID$.mp4" media="v-$Time$.m4s">
        <SegmentTimeline><S t="100" d="5" r="1" /></SegmentTimeline>
      </SegmentTemplate>
      <Representation id="video" bandwidth="1000000" width="1280" height="720" />
    </AdaptationSet>
  </Period>
</MPD>
'''


class DashSupportTests(unittest.TestCase):
    def test_mpd_is_proven_with_initialization_and_recent_fragments(self) -> None:
        def fake_fetch(url, headers, **kwargs):
            self.assertTrue(url.startswith("https://cdn.example/live/"))
            self.assertNotIn("?", url)
            return 200, b"fragment", url

        with patch.object(update_m3u, "fetch_bytes", side_effect=fake_fetch):
            ok, detail = update_m3u.check_dash_first_segments(
                "https://cdn.example/live/channel.mpd",
                {"User-Agent": "test"},
                initial_body=CLEAR_MPD,
                initial_final_url="https://cdn.example/live/channel.mpd",
            )

        self.assertTrue(ok, detail)
        self.assertIn("video 1280x720", detail)
        self.assertIn("audio", detail)
        self.assertIn("fragmentos recientes validos", detail)

    def test_drm_and_query_urls_are_rejected(self) -> None:
        drm_mpd = CLEAR_MPD.replace(
            b'<Period>',
            b'<ContentProtection schemeIdUri="urn:uuid:edef8ba9"/><Period>',
            1,
        )
        ok, detail = update_m3u.check_dash_first_segments(
            "https://cdn.example/live/channel.mpd",
            {},
            initial_body=drm_mpd,
            initial_final_url="https://cdn.example/live/channel.mpd",
        )
        self.assertFalse(ok)
        self.assertIn("DRM", detail)

        ok, detail = update_m3u.check_dash_first_segments(
            "https://cdn.example/live/channel.mpd?token=temporary",
            {},
            initial_body=CLEAR_MPD,
            initial_final_url="https://cdn.example/live/channel.mpd?token=temporary",
        )
        self.assertFalse(ok)
        self.assertIn("HTTPS estable", detail)

    def test_dash_format_is_inferred_from_mpd_url(self) -> None:
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="TestDash" group-title="Deportes",Test DASH',
            "https://cdn.example/live/test.mpd",
        ]
        channel = update_m3u.parse_channels(lines)[0]
        self.assertEqual(channel.stream_format, "dash")

    def test_dash_candidate_is_a_direct_probe(self) -> None:
        channel = update_m3u.Channel(
            name="MNB Sport",
            url="https://cdn.example/live/mnb.mpd",
            url_line=1,
            tvg_id="MNBSport.mn@DirectDASH",
            stream_format="dash",
        )
        self.assertTrue(update_m3u.is_direct_probe(channel))


if __name__ == "__main__":
    unittest.main()
