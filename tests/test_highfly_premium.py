import unittest

import update_m3u


class HighflyPremiumTest(unittest.TestCase):
    def test_premium_placeholder_is_detected(self) -> None:
        payload = {"streams": [{"name": "\U0001f512 Leaf · (4k) : SKY SPORTS F1",
                                "title": "3840x2160 · \U0001f512 Upgrade to Premium",
                                "url": "https://www.google.com"}]}
        self.assertEqual([], update_m3u.highfly_stream_urls_from_payload(payload))
        self.assertTrue(update_m3u.highfly_payload_premium_locked(payload))
        self.assertFalse(update_m3u.highfly_payload_premium_locked(
            {"streams": [{"name": "Leaf · (FHD)", "url": "https://papacito.cfd/m3u/x/live.m3u8"}]}))


if __name__ == "__main__":
    unittest.main()
