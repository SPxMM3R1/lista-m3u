import unittest

import update_m3u


class EpgTitleCapsTest(unittest.TestCase):
    def test_short_codes_keep_uppercase(self) -> None:
        self.assertEqual("Antena A3D", update_m3u.normalize_epg_title("ANTENA A3D"))
        self.assertEqual("Fútbol 4K En Vivo", update_m3u.normalize_epg_title("FÚTBOL 4K EN VIVO"))

    def test_sports_acronyms_keep_uppercase(self) -> None:
        self.assertEqual("NFL: Partido Del Día", update_m3u.normalize_epg_title("NFL: PARTIDO DEL DÍA"))

    def test_letter_after_colon_is_uppercase(self) -> None:
        self.assertEqual("Noticias: La final", update_m3u.normalize_epg_title("Noticias: la final"))
        self.assertEqual("Noticias: Edición Central", update_m3u.normalize_epg_title("NOTICIAS: EDICIÓN CENTRAL"))

    def test_known_acronyms_uppercase_in_mixed_titles(self) -> None:
        self.assertEqual("CSI: Miami", update_m3u.normalize_epg_title("Csi: Miami"))
        self.assertEqual("CSI", update_m3u.normalize_epg_title("csi"))
        self.assertEqual("NCIS: Los Ángeles", update_m3u.normalize_epg_title("Ncis: Los Ángeles"))
        self.assertEqual("Previa ESPN", update_m3u.normalize_epg_title("Previa Espn"))
        self.assertEqual("TyC Sports", update_m3u.normalize_epg_title("TyC Sports"))
        self.assertEqual("Ella usa el auto", update_m3u.normalize_epg_title("Ella usa el auto"))
        self.assertEqual("XXX: Reactivado", update_m3u.normalize_epg_title("Xxx: Reactivado"))
        self.assertEqual("XXX", update_m3u.normalize_epg_title("XXX"))
        self.assertEqual("XXX", update_m3u.normalize_epg_title("xXx"))

    def test_times_are_not_touched(self) -> None:
        self.assertEqual("Partido 20:30 en vivo", update_m3u.normalize_epg_title("Partido 20:30 en vivo"))

    def test_normal_text_is_untouched(self) -> None:
        self.assertEqual("La ley y el orden", update_m3u.normalize_epg_title("La ley y el orden"))

    def test_category_prefixes_are_removed(self) -> None:
        # 2026-10-31, pedido del usuario: el partido «directamente», sin la liga delante.
        cases = {
            "Fútbol Chileno Primera División : Coquimbo Unido vs. CD Unión La Calera":
                "Coquimbo Unido vs. CD Unión La Calera",
            "Baloncesto NBA : Portland Trail Blazers vs. Los Angeles Lakers":
                "Portland Trail Blazers vs. Los Angeles Lakers",
            "Fútbol: Previa : Liga de Primera 2026": "Previa: Liga de Primera 2026",
            "Live: WTA Tokyo Final": "WTA Tokyo Final",
            "Live PL: Liverpool v Arsenal": "Liverpool v Arsenal",
            "Live NBA: Thunder @ Cavaliers": "Thunder @ Cavaliers",
            "SNF: Aston Villa v Fulham Hlts": "Aston Villa v Fulham Hlts",
            "Replay : Históricos clásicos universitarios": "Replay: Históricos clásicos universitarios",
        }
        for source, expected in cases.items():
            self.assertEqual(expected, update_m3u.normalize_epg_title(source), source)

    def test_names_that_belong_to_the_title_stay(self) -> None:
        for title in ("Live", "UFC 333: Volkanovski vs Evloev", "Duelo de parrillas: Flay vs. Symon",
                      "Maze Runner: La cura mortal", "Fútbol Chileno Primera División", "CSI: Miami"):
            self.assertEqual(title, update_m3u.normalize_epg_title(title))


if __name__ == "__main__":
    unittest.main()
