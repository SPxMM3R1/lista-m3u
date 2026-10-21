# Verificado en la corrida EPG 39531971168 (2026-10-21).
import unittest

import update_m3u


class EsMovistarBackupTest(unittest.TestCase):
    """Las cuatro guías españolas que EPGShare ES1 dejó sin futuro."""

    BACKUPS = {
        "AlJazeera.qa": ("es2", "AlJazeera.qa"),
        "DAZNF1.es@TvVoo": ("es2", "DAZNF1.uk"),
        "Vavoo.es.EUROSPORT1@TvVoo": ("es2", "Eurosport1.fr"),
        "Eurosport2.es@TvVoo": ("es2", "Eurosport2.fr"),
    }

    def test_source_is_configured(self):
        self.assertEqual(
            "https://oscarbc96.github.io/epg-spain/guide.xml.gz",
            update_m3u.EPG_SOURCES["es2"],
        )

    def test_each_channel_falls_back_to_es2(self):
        for channel_id, expected in self.BACKUPS.items():
            with self.subTest(channel=channel_id):
                self.assertEqual(expected, update_m3u.EPGSHARE_BACKUP_CHANNELS[channel_id])
                chain = update_m3u.epg_source_chain(channel_id)
                self.assertIn(expected, chain)
                self.assertGreater(chain.index(expected), 0)


if __name__ == "__main__":
    unittest.main()
