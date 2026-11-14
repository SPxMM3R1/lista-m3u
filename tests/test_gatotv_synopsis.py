"""GatoTV: título y sinopsis por fila (2026-11-14, HBO casi sin detalle)."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epg_sources.gatotv import gatotv_programmes  # noqa: E402

ROW_WITH_LINK = """<tr class="tbl_EPG_row">
<td><div class="tbl_EPG_TimesColumn"><time datetime="04:00">04:00</time></div></td>
<td><div class="tbl_EPG_TimesColumn"><time datetime="06:00">06:00</time></div></td>
<td colspan="5" class="pelicula"><div class="tbl_EPG_ProgramsColumn pelicula">
<div class="div_program_title_on_channel">
<a itemprop="url" href="https://www.gatotv.com/pelicula/godzilla" title="Godzilla y Kong" >
<span>Godzilla y Kong</span>
</a>
</div>
Godzilla y Kong se unen para enfrentar a una colosal amenaza escondida dentro de la tierra.
</div></td></tr>"""
ROW_PLAIN = """<tr class="tbl_EPG_rowAlternate">
<td><div class="tbl_EPG_TimesColumn"><time datetime="06:00">06:00</time></div></td>
<td><div class="tbl_EPG_TimesColumn"><time datetime="08:23">08:23</time></div></td>
<td colspan="5" class="pelicula"><div class="tbl_EPG_ProgramsColumn pelicula">
<div class="div_program_title_on_channel">
<span>El conjuro 4</span>
</div>
</div></td></tr>"""
PAGE = "<script>utcOffset: -3</script><table>" + ROW_WITH_LINK + ROW_PLAIN + "</table>"


class GatoTvSynopsisTests(unittest.TestCase):
    def test_rows_with_and_without_link_keep_their_own_synopsis(self):
        items = gatotv_programmes(PAGE, date(2026, 11, 14))
        self.assertEqual([item[2] for item in items], ["Godzilla y Kong", "El conjuro 4"])
        self.assertTrue(items[0][3].startswith("Godzilla y Kong se unen"))
        self.assertEqual(items[1][3], "")  # no hereda la sinopsis de la fila anterior
        self.assertEqual(items[0][0].hour, 7)  # 04:00 en -3 = 07:00 UTC


if __name__ == "__main__":
    unittest.main()
