import unittest

import update_m3u


class EpgTitleCapsTest(unittest.TestCase):
    def test_short_codes_keep_uppercase(self) -> None:
        self.assertEqual("Antena A3D", update_m3u.normalize_epg_title("ANTENA A3D"))
        self.assertEqual("Fútbol 4K En Vivo", update_m3u.normalize_epg_title("FÚTBOL 4K EN VIVO"))

    def test_sports_acronyms_keep_uppercase(self) -> None:
        self.assertEqual("NFL: Partido Del Día", update_m3u.normalize_epg_title("NFL: PARTIDO DEL DÍA"))

    def test_letter_after_colon_is_uppercase(self) -> None:
        self.assertEqual("Fútbol: La final", update_m3u.normalize_epg_title("Fútbol: la final"))
        self.assertEqual("Noticias: Edición Central", update_m3u.normalize_epg_title("NOTICIAS: EDICIÓN CENTRAL"))

    def test_times_are_not_touched(self) -> None:
        self.assertEqual("Partido 20:30 en vivo", update_m3u.normalize_epg_title("Partido 20:30 en vivo"))

    def test_normal_text_is_untouched(self) -> None:
        self.assertEqual("La ley y el orden", update_m3u.normalize_epg_title("La ley y el orden"))


if __name__ == "__main__":
    unittest.main()
