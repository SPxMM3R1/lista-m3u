#!/usr/bin/env python3
"""Verify the published playlist and refresh expiring live stream links."""

from __future__ import annotations

import argparse
import copy
import gzip
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_PLAYLIST = Path(__file__).with_name("m3u.m3u")
EPG_PATH = Path(__file__).with_name("epg.xml")
REPORT_PATH = Path(__file__).with_name("channel-status.json")
PUBLIC_RAW_BASE = "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main"
EPG_PUBLIC_URL = f"{PUBLIC_RAW_BASE}/epg.xml"
LOCAL_LOGOS_PUBLIC_BASE = f"{PUBLIC_RAW_BASE}/logos"
TEST_GROUP_PREFIX = "PRUEBA - "
# Nombre corto mostrado por el reproductor -> nombre canonico que usa el
# actualizador. El tvg-id y la fuente de XITE no cambian.
DISPLAY_NAME_ALIASES = {
    "XITE Hits": "XITE Hits Germany",
}
# TvVoo responde para estas dos senales, pero no se encontro una parrilla
# XMLTV propia ni una fuente de terceros que identifique el canal exacto.
# Se publican en la lista principal sin inventar programas de continuidad.
NO_EPG_CHANNEL_IDS = {
    "RTFrance.fr@TvVoo",
    "DAZNFastPlus.de@TvVoo",
}
NHK_MASTER_URL = "https://masterpl.hls.nhkworld.jp/hls/w/live/smarttv.m3u8"
NHK_WORLD_LIVE_PAGE = "https://www3.nhk.or.jp/nhkworld/en/live_tv/"
NHK_WORLD_EPG_BASE_URL = "https://masterpl.hls.nhkworld.jp/epg/w"
NHK_OFFICIAL_EPG_SOURCE = "nhk-world-oficial"
FRANCE24_ES_1080_URL = (
    "https://live.france24.com/hls/live/2037220/F24_ES_HI_HLS/master_5000.m3u8"
)
# EPGShare es un agregador de respaldo. Las fuentes oficiales especificas se
# incorporan en refresh_epg y tienen prioridad cuando publican una parrilla.
EPG_SOURCES = {
    "cl": "https://epgshare01.online/epgshare01/epg_ripper_CL1.xml.gz",
    "es": "https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz",
    "fr": "https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
    "de": "https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz",
    "uk1": "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "ar1": "https://epgshare01.online/epgshare01/epg_ripper_AR1.xml.gz",
    "pt1": "https://epgshare01.online/epgshare01/epg_ripper_PT1.xml.gz",
    "nz1": "https://epgshare01.online/epgshare01/epg_ripper_NZ1.xml.gz",
    "us2": "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "pl": "https://epgshare01.online/epgshare01/epg_ripper_PL1.xml.gz",
    "lv": "https://epgshare01.online/epgshare01/epg_ripper_LV1.xml.gz",
    "nl": "https://epgshare01.online/epgshare01/epg_ripper_NL1.xml.gz",
    # PLEX1 cubre los canales FAST de BBC, Bloomberg, CBS, Qello, Stingray y
    # XITE. Las fuentes por pais completan noticias internacionales que no
    # aparecen en PLEX1, sin descargar el ALL_SOURCES de mas de 200 MB.
    "plex1": "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz",
    "tr1": "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "sg1": "https://epgshare01.online/epgshare01/epg_ripper_SG1.xml.gz",
    "ng1": "https://epgshare01.online/epgshare01/epg_ripper_NG1.xml.gz",
    # PlutoTV es la fuente de parrilla real para los canales lineales Pluto
    # usados por MTV. No se generan bloques de continuidad para esos IDs.
    "pluto": "https://i.mjh.nz/PlutoTV/all.xml.gz",
}
EPG_PROGRAMME_SOURCES = {
    "0104": ("cl", "Canal.TVN.(Chile).cl"),
    "0105": ("cl", "Canal.Mega.(Chile).cl"),
    "0106": ("cl", "Canal.Chilevisi\u00f3n.(CHV).cl"),
    "0107": ("cl", "Canal.13.de.Chile.cl"),
    "0201": ("cl", "Canal.24.Horas.(Chile).cl"),
    "0102": ("cl", "Canal.La.Red.(Chile).cl"),
    "DW.de": ("es", "Deutsche.Welle.es"),
    "France24.fr": ("fr", "France.24.Espanol.fr"),
    "EuronewsSpanish.fr": ("es", "Euronews.es"),
    "AlJazeera.qa": ("es", "Al.Jazeera.English.es"),
    "TVChile.cl": ("cl", "TV.Chile.cl"),
    "ArirangTV.kr": ("pl", "Arirang.TV.pl"),
    "XITEHits.nl@Germany": ("nl", "XITE.nl"),
    "DWEnglish.de": ("lv", "Deutsche.Welle.English.HD.lv"),
    "France24.fr@English": ("fr", "France.24.Anglais.fr"),
    "ESPN.us": ("us2", "ESPN.HD.us2"),
    "MarqueeSportsNetwork.us": ("us2", "Marquee.Sports.Network.HD.us2"),
    "NHLNetwork.us": ("us2", "NHL.Network.HD.us2"),
    "RewindTV.cl@SD": ("us2", "Rewind.TV.us2"),
    "TyCSports.ar": ("ar1", "Canal.TyC.Sports.ar"),
    "SkySport1.nz": ("nz1", "Sky.Sport.1.nz"),
    "SkySportsF1.uk": ("uk1", "SkySp.F1.HD.uk"),
    "SkySportsRacing.uk": ("uk1", "SkySp.Racing.HD.uk"),
    "SkySportsPremierLeague.uk": ("uk1", "SkySp.PL.HD.uk"),
    "SkySportsTennis.uk": ("uk1", "SkySp.Tennis.HD.uk"),
    "SkySportsGolf.uk": ("uk1", "SkySp.Golf.HD.uk"),
    "PremierSports1.ie": ("uk1", "Premier.Sports.1.HD.uk"),
    "PremierSports2.ie": ("uk1", "Premier.Sports.2.HD.uk"),
    "BeINSportsXtra.us": ("plex1", "plex.tv.beIN.SPORTS.XTRA.plex"),
    "BeINSportsXtra.us@Spanish": (
        "plex1",
        "plex.tv.beIN.Sports.Xtra.en.Español.plex",
    ),
    "RealWild.us": ("plex1", "plex.tv.Real.Wild.plex"),
    "XITENuevoLatino.us": ("plex1", "plex.tv.XITE.Nuevo.Latino.plex"),
    "XITESiempreLatino.us": ("plex1", "plex.tv.XITE.Siempre.Latino.plex"),
    "MTVClassic.us": ("pluto", "66a01dcb8561260008b0a41d"),
    "MTVBiggestPop.us": ("pluto", "6047fabfce6e8e00070bcc9f"),
    "MTVSpankinNew.us": ("pluto", "6541010f770cf1000866be98"),
    "MTVFlowLatino.us": ("pluto", "62b218fc511d4b00070ddc0c"),
    "YoMTV.us": ("pluto", "654102ed770cf1000866c307"),
    "SkySportsMainEvent.uk@TvVoo": ("uk1", "SkySpMainEvHD.uk"),
    "SkySportsPlus.uk@TvVoo": ("uk1", "SkySp+.uk"),
    "TNTSports3.uk@TvVoo": ("uk1", "TNT.Sports.3.HD.uk"),
    "CNN.us@TvVoo": ("uk1", "CNN.HD.uk"),
    "ESPN3.ar@TvVoo": ("ar1", "Canal.ESPN.3.(Argentina).ar"),
    "Eurosport1.fr@TvVoo": ("fr", "Eurosport.1.fr"),
    "RMCSport1.fr@TvVoo": ("fr", "RMC.Sport.1.fr"),
    "RMCSport2.fr@TvVoo": ("fr", "RMC.Sport.Live.2.fr"),
    "MTVHits.fr@TvVoo": ("nz1", "MTV.Hits.nz"),
    "M6Music.fr@TvVoo": ("fr", "M6.Music.fr"),
    "TraceUrban.fr@TvVoo": ("fr", "Trace.Urban.fr"),
    "DAZN2.de@TvVoo": ("de", "DAZN.2.de"),
    "SportTV1.pt@TvVoo": ("pt1", "SPORT.TV1.HD.pt"),
    "SportTV2.pt@TvVoo": ("pt1", "SPORT.TV2.HD.pt"),
    "ElevenSports1.pt@TvVoo": ("pl", "Eleven.Sports.1.HD.pl"),
    "ElevenSports2.pt@TvVoo": ("pl", "Eleven.Sports.2.HD.pl"),
    "Meganoticias.cl": ("tecnocentro", "LCH7159"),
    "0124": ("tecnocentro", "LCH6525"),
    "1153": ("tecnocentro", "LCH7017"),
    "45": ("tecnocentro", "LCH4087"),
    "M1.ua@SD": ("ukrainian-official", "M1.ua@SD"),
    "M2.ua@SD": ("ukrainian-official", "M2.ua@SD"),
    "BBCEarth.uk": ("plex1", "plex.tv.BBC.Earth.plex"),
    "BBCNews.uk": ("plex1", "plex.tv.BBC.News.(North.America).plex"),
    "BBCTravel.us": ("plex1", "plex.tv.BBC.Travel.plex"),
    "BloombergTV.us": ("plex1", "plex.tv.Bloomberg.TV.plex"),
    "BloombergOriginals.us": ("plex1", "plex.tv.Bloomberg.Originals.plex"),
    "CBSNews247.us": ("plex1", "plex.tv.CBS.News.24/7.plex"),
    "QelloConcertsbyStingray.ca": ("plex1", "plex.tv.Qello.Concerts.plex"),
    "StingrayClassica.ca": ("plex1", "plex.tv.Stingray.Classica.Stream.plex"),
    "StingrayDJAZZ.ca": ("plex1", "plex.tv.Stingray.DJAZZ.plex"),
    "XITE80sFlashback.us": ("plex1", "plex.tv.XITE.80s.Flashback.plex"),
    "XITE90sThrowback.us": ("plex1", "plex.tv.XITE.90s.Throwback.plex"),
    "XITERockxMetal.nl": ("plex1", "plex.tv.XITE.Rock.x.Metal.plex"),
    "XITEJustChill.nl": ("plex1", "plex.tv.XITE.Just.Chill.plex"),
    "TRTWorld.tr": ("tr1", "TRT.WORLD.HD.tr"),
    "CNA.sg": ("sg1", "CNA.(HD).sg"),
    "AfricanewsEnglish.fr": ("ng1", "Africanews.ng"),
}
# Zapping publica una guia HTML con marcas Unix absolutas para el programa
# actual, hoy y manana. Se usa solo para senales chilenas donde la fuente
# agregada estaba desplazada o no entregaba una parrilla util. TVN y Mega
# conservan sus adaptadores oficiales especificos; T13 usa Zapping y
# TecnoCentro porque no hay una parrilla oficial diaria de esa senal.
ZAPPING_EPG_SOURCE = "zapping-guia-publica"
ZAPPING_EPG_BASE_URL = "https://guia.zappingtv.com"
ZAPPING_EPG_CHANNELS = {
    "0106": "chv",
    "0107": "canal13",
    "0102": "lared",
    "0201": "24horas",
    "Meganoticias.cl": "meganoticias",
    "1153": "chvnoticias",
    "0124": "t13",
    "45": "ntv",
    "1437": "tvn3",
    "13C.cl@SD": "13cable",
}
TECNOCENTRO_EPG_URL = "https://tecnocentro.cl/"
try:
    CHILE_TIMEZONE = ZoneInfo("America/Santiago")
except ZoneInfoNotFoundError:
    CHILE_TIMEZONE = timezone(timedelta(hours=-4))
try:
    NHK_TIMEZONE = ZoneInfo("Asia/Tokyo")
except ZoneInfoNotFoundError:
    NHK_TIMEZONE = timezone(timedelta(hours=9))
try:
    UKRAINE_TIMEZONE = ZoneInfo("Europe/Kyiv")
except ZoneInfoNotFoundError:
    UKRAINE_TIMEZONE = timezone(timedelta(hours=3))
RED_BULL_SESSION_URL = (
    "https://api.redbull.tv/v3/session?category=smart_tv&os_family=android"
)
RED_BULL_OFFICIAL_EPG_URL = "https://api.redbull.tv/v3/epg?complete=true"
RED_BULL_SPANISH_EPG_PAGE = "https://www.redbull.tv/es/epg"
# Este relay esta documentado por iptv-org/epg, pero se usa solo como respaldo:
# su disponibilidad depende de la actualizacion diaria del proveedor.
RED_BULL_RELAY_EPG_URL = "https://nzxmltv.com/iptv/redbull.xml"
RED_BULL_WORLD_ID = "RedBullWorldEnglish.int"
RED_BULL_CHILE_ID = "RedBullChileEspanol.cl"
RED_BULL_CHANNEL_LOCALES = {
    RED_BULL_WORLD_ID: "en",
    RED_BULL_CHILE_ID: "es",
}
RED_BULL_WORLD_URL = (
    "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8"
)
RED_BULL_CHILE_URL = (
    "https://freqsyndlin.redbull.com/957/rbtv/hls/master/playlist.m3u8"
)
# La guia se actualiza junto con la validacion de canales cada 48 horas. Se
# conserva la reutilizacion de una guia valida si una ejecucion falla.
EPG_REFRESH_INTERVAL = timedelta(hours=48)
# El coordinador puede adelantar la siguiente ejecucion cuando una fuente real
# termina antes de las 48 horas. Los bloques de continuidad no cuentan para
# este calculo: solo sirven para que la guia no quede vacia mientras llega el
# siguiente refresco.
EPG_REFRESH_LEAD = timedelta(hours=6)
TVN_PROGRAMMING_PAGE = "https://www.tvn.cl/programacion"
TVN_PROGRAMMING_BASE_URL = "https://estaticos.tvn.cl/epg/tvn"
TVN_OFFICIAL_EPG_SOURCE = "tvn-oficial"
TVN_ALTERNATIVE_URL = "https://iptv2.intersurtv.cl/TVN/index.m3u8?PlaylistM3UCL"
LA_RED_PROGRAMMING_PAGE = "https://www.lared.cl/guia-programacion"
LA_RED_OFFICIAL_EPG_SOURCE = "la-red-oficial"
LA_RED_MASTER_URL = "https://tv-mgmt.gtd.cl/bpk-tv/LARED/default/index.m3u8"
ARIRANG_TV_MASTER_URL = (
    "http://amdlive-ch01.ctnd.com.edgesuite.net/"
    "arirang_1ch/smil:arirang_1ch.smil/playlist.m3u8"
)
TWENTYFOUR_LIVE_PAGE = "https://www.24horas.cl/envivo"
TWENTYFOUR_DEFAULT_ID = "57d1a22064f5d85712b20dab"
MEGA_LIVE_PAGE = "https://www.mega.cl/senal-en-vivo/"
MEGA_PROGRAMMING_PAGE = "https://www.mega.cl/programacion/"
MEGA_OFFICIAL_EPG_SOURCE = "mega-oficial"
MEGA_SOURCE_MASTER_URL = (
    "https://tr.live.clarovtrcdn.vtrplay.com/megahdchi/"
    "vxfmt=dp/playlist.m3u8?device_profile=STB_HLS_VCAS_LIVE_HD"
)
MEGANOTICIAS_LIVE_PAGE = "https://www.meganoticias.cl/senal-en-vivo/meganoticias/"
CANAL13_13C_PROGRAMMING_PAGE = "https://www.13.cl/c/programacion"
CANAL13_13C_OFFICIAL_EPG_SOURCE = "canal13-13c-oficial"
TVVOO_STREAM_BASE_URL = "https://tvvoo.hayd.uk/stream/tv"
# TvVoo publica varios alias para las mismas senales. Se prueban primero los
# alias que hoy entregan un segmento funcional y se conservan las variantes HD
# como respaldo para cuando el proveedor las vuelva a servir.
TVVOO_STREAM_RESOLVER_IDS = {
    "Premier Sports 1": (
        "vavoo_PREMIER%20SPORT%7Cgroup%3Auk",
        "vavoo_PREMIER%20SPORTS%201%7Cgroup%3Auk",
        "vavoo_PREMIER%20SPORTS%201%20HD%7Cgroup%3Auk",
    ),
    "Premier Sports 2": (
        "vavoo_PREMIER%20SPORT%202%7Cgroup%3Auk",
        "vavoo_PREMIER%20SPORTS%202%7Cgroup%3Auk",
        "vavoo_PREMIER%20SPORTS%202%20HD%7Cgroup%3Auk",
    ),
    "Sky Sports Main Event": (
        "vavoo_SKY%20SPORTS%20MAIN%20EVENT%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20MAIN%20EVENT%20HD%7Cgroup%3Auk",
    ),
    # El catalogo TvVoo conserva el alias ARENA; la parrilla actual se
    # identifica como Sky Sports+, por eso el tvg-id y la EPG usan Sky+.
    "Sky Sports+": (
        "vavoo_SKY%20SPORTS%20ARENA%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20ARENA%20HD%7Cgroup%3Auk",
    ),
    "TNT Sports 3": (
        "vavoo_TNT%20SPORTS%203%7Cgroup%3Auk",
        "vavoo_TNT%20SPORTS%203%20HD%7Cgroup%3Auk",
    ),
    "CNN": ("vavoo_CNN%7Cgroup%3Auk",),
    "RT France": ("vavoo_RT%20FRANCE%7Cgroup%3Afr",),
    "ESPN 3": ("vavoo_ESPN%203%7Cgroup%3Aar",),
    "Eurosport 1": (
        "vavoo_EUROSPORT%201%7Cgroup%3Afr",
        "vavoo_EUROSPORT%201%20FHD%7Cgroup%3Afr",
        "vavoo_EUROSPORT%201%20HD%7Cgroup%3Afr",
    ),
    "RMC Sport 1": (
        "vavoo_RMC%20SPORT%201%7Cgroup%3Afr",
        "vavoo_RMC%20SPORT%201%20FHD%7Cgroup%3Afr",
        "vavoo_RMC%20SPORT%201%20HD%7Cgroup%3Afr",
    ),
    "RMC Sport 2": (
        "vavoo_RMC%20SPORT%202%7Cgroup%3Afr",
        "vavoo_RMC%20SPORT%202%20FHD%7Cgroup%3Afr",
        "vavoo_RMC%20SPORT%202%20HD%7Cgroup%3Afr",
    ),
    "MTV Hits": (
        "vavoo_MTV%20HITS%7Cgroup%3Afr",
        "vavoo_MTV%20HITS%20HD%7Cgroup%3Afr",
        "vavoo_MTV%20HITS%20SD%7Cgroup%3Afr",
    ),
    "M6 Music": (
        "vavoo_M6%20MUSIC%7Cgroup%3Afr",
        "vavoo_M6%20MUSIC%20HD%7Cgroup%3Afr",
        "vavoo_M6%20MUSIC%20SD%7Cgroup%3Afr",
    ),
    "Trace Urban": (
        "vavoo_TRACE%20URBAN%7Cgroup%3Afr",
        "vavoo_TRACE%20URBAN%20HD%7Cgroup%3Afr",
        "vavoo_TRACE%20URBAN%20SD%7Cgroup%3Afr",
    ),
    "DAZN 2": (
        "vavoo_DAZN%202%7Cgroup%3Ade",
        "vavoo_DAZN%202%20HD%7Cgroup%3Ade",
        "vavoo_DAZN%202%20FHD%7Cgroup%3Ade",
    ),
    "DAZN FAST+": ("vavoo_DAZN%20FAST%2B%7Cgroup%3Ade",),
    "Sport TV 1": (
        "vavoo_SPORT%20TV%201%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%201%20HD%7Cgroup%3Apt",
    ),
    "Sport TV 2": (
        "vavoo_SPORT%20TV%202%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%202%20HD%7Cgroup%3Apt",
    ),
    "Eleven Sports 1": ("vavoo_ELEVEN%20SPORTS%201%20HD%7Cgroup%3Apt",),
    "Eleven Sports 2": ("vavoo_ELEVEN%20SPORTS%202%20HD%7Cgroup%3Apt",),
}
CI_GEO_RESTRICTED_CHANNELS = {
    "Mega",
    "NTV",
    "CHV",
    "CHV Deportes",
    "Canal 13",
    "24 Horas",
    "La Red",
    "TV Chile",
    "UChile TV",
    # GitHub Actions corre fuera de Chile y no puede validar estos maestros
    # cuando el emisor responde 401/403; la app resuelve su acceso al abrirlos.
    "TVN",
    "Meganoticias",
    # CNA publica el stream con restricciones regionales; la CDN puede
    # responder 403 desde GitHub aunque entregue segmentos desde Chile.
    "CNA",
}
# TVN mantiene su maestro original; la autenticacion de playback queda
# exclusivamente en la aplicacion y nunca se ejecuta desde Actions.
APP_HANDLED_CHANNELS = {"TVN"}
PREFERRED_LOGOS = {
    "TVN": f"{LOCAL_LOGOS_PUBLIC_BASE}/tvn.png",
    "Mega": f"{LOCAL_LOGOS_PUBLIC_BASE}/mega.png",
    "CHV": f"{LOCAL_LOGOS_PUBLIC_BASE}/chv.png",
    "Canal 13": f"{LOCAL_LOGOS_PUBLIC_BASE}/canal13.png",
    "La Red": f"{LOCAL_LOGOS_PUBLIC_BASE}/la-red.png",
    "24 Horas": f"{LOCAL_LOGOS_PUBLIC_BASE}/24-horas.svg",
    "Meganoticias": f"{LOCAL_LOGOS_PUBLIC_BASE}/meganoticias.png",
    "T13": f"{LOCAL_LOGOS_PUBLIC_BASE}/t13.svg",
    "CHV Noticias": f"{LOCAL_LOGOS_PUBLIC_BASE}/chv-noticias.svg",
    "NTV": f"{LOCAL_LOGOS_PUBLIC_BASE}/ntv.svg",
    "TVN3": f"{LOCAL_LOGOS_PUBLIC_BASE}/tvn3.svg",
    "CHV Deportes": f"{LOCAL_LOGOS_PUBLIC_BASE}/chv-deportes.svg",
    "DW Español": f"{LOCAL_LOGOS_PUBLIC_BASE}/dw.svg",
    "DW English": f"{LOCAL_LOGOS_PUBLIC_BASE}/dw.svg",
    "Autentic History": f"{LOCAL_LOGOS_PUBLIC_BASE}/autentic-history.svg",
    "France 24 Español": f"{LOCAL_LOGOS_PUBLIC_BASE}/france24.svg",
    "France 24 English": f"{LOCAL_LOGOS_PUBLIC_BASE}/france24.svg",
    "Euronews Español": f"{LOCAL_LOGOS_PUBLIC_BASE}/euronews-espanol.png",
    "NHK World Japan": f"{LOCAL_LOGOS_PUBLIC_BASE}/nhk-world.svg",
    "Al Jazeera English": f"{LOCAL_LOGOS_PUBLIC_BASE}/aljazeera.svg?v=2",
    "RedBull TV World": f"{LOCAL_LOGOS_PUBLIC_BASE}/red-bull-tv.png",
    "RedBull TV Español": f"{LOCAL_LOGOS_PUBLIC_BASE}/red-bull-tv.png",
    "XITE Hits Germany": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "XITE Nuevo Latino": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "XITE Siempre Latino": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "Arirang TV": f"{LOCAL_LOGOS_PUBLIC_BASE}/arirang.png",
    "M1": f"{LOCAL_LOGOS_PUBLIC_BASE}/m1.png",
    "M2": f"{LOCAL_LOGOS_PUBLIC_BASE}/m2.png",
    "13 Cultura": f"{LOCAL_LOGOS_PUBLIC_BASE}/13cultura.svg",
    "13C": f"{LOCAL_LOGOS_PUBLIC_BASE}/13c.png",
    "RWND": f"{LOCAL_LOGOS_PUBLIC_BASE}/rewind-v2.png",
    "BBC Earth FAST": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc-earth.svg",
    "BBC News": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc.svg",
    "BBC Travel": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc.svg",
    "Bloomberg TV US": f"{LOCAL_LOGOS_PUBLIC_BASE}/bloomberg.svg",
    "Bloomberg Originals": f"{LOCAL_LOGOS_PUBLIC_BASE}/bloomberg.svg",
    "CBS News 24/7": f"{LOCAL_LOGOS_PUBLIC_BASE}/cbs-news.svg",
    "TRT World": f"{LOCAL_LOGOS_PUBLIC_BASE}/trt-world.svg",
    "CNA": f"{LOCAL_LOGOS_PUBLIC_BASE}/cna.svg",
    "Africanews English": f"{LOCAL_LOGOS_PUBLIC_BASE}/africanews.svg",
    "Qello Concerts by Stingray": f"{LOCAL_LOGOS_PUBLIC_BASE}/qello-concerts.jpg",
    "Stingray Classica": f"{LOCAL_LOGOS_PUBLIC_BASE}/stingray-classica.svg",
    "Stingray DJAZZ": f"{LOCAL_LOGOS_PUBLIC_BASE}/stingray-djazz.svg",
    "XITE 80s Flashback": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "XITE 90s Throwback": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "MTV Classic": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-classic.svg",
    "MTV Biggest Pop": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-biggest-pop.svg",
    "MTV Spankin' New": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-spankin-new.svg",
    "MTV Flow Latino": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-flow-latino.svg",
    "Yo! MTV": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-yo.svg",
    "XITE Rock x Metal": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "MTV Rocks": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-rocks.svg",
    "XITE Just Chill": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "Sky Sports F1": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-f1.png",
    "ESPN HD": f"{LOCAL_LOGOS_PUBLIC_BASE}/espn.svg",
    "Marquee Sports Network HD": f"{LOCAL_LOGOS_PUBLIC_BASE}/marquee-sports-network.svg",
    "Sky Sports Racing": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-racing.png",
    "Sky Sports Premier League": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-premier-league.png",
    "Premier Sports 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/premier-sports-1.png",
    "Premier Sports 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/premier-sports-2.png",
    "Sky Sport 1 NZ": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sport-1-nz.png",
    "Sky Sports Tennis": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-tennis.png",
    "Sky Sports Golf": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-golf.png",
    "Totalmusic 80s": f"{LOCAL_LOGOS_PUBLIC_BASE}/totalmusic-80s.png",
    "Totalmusic 2000s": f"{LOCAL_LOGOS_PUBLIC_BASE}/totalmusic-2000s.png",
    "Totalmusic Concerts": f"{LOCAL_LOGOS_PUBLIC_BASE}/totalmusic-concerts.png",
    "Totalmusic Dance": f"{LOCAL_LOGOS_PUBLIC_BASE}/totalmusic-dance.png",
    "Reuters": f"{LOCAL_LOGOS_PUBLIC_BASE}/reuters.png",
    "Real Wild": f"{LOCAL_LOGOS_PUBLIC_BASE}/real-wild.png",
    "beIN SPORTS XTRA": f"{LOCAL_LOGOS_PUBLIC_BASE}/bein-sports-xtra.jpg",
    "beIN SPORTS XTRA Español": f"{LOCAL_LOGOS_PUBLIC_BASE}/bein-sports-xtra-es.jpg",
    "NHL Network": f"{LOCAL_LOGOS_PUBLIC_BASE}/nhl-network.png",
    "TyC Sports": f"{LOCAL_LOGOS_PUBLIC_BASE}/tyc-sports.png",
    "Sky Sports Main Event": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-main-event.png",
    "Sky Sports+": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-plus.png",
    "TNT Sports 3": f"{LOCAL_LOGOS_PUBLIC_BASE}/tnt-sports-3.png",
    "CNN": f"{LOCAL_LOGOS_PUBLIC_BASE}/cnn.png",
    "RT France": f"{LOCAL_LOGOS_PUBLIC_BASE}/rt-france.png",
    "ESPN 3": f"{LOCAL_LOGOS_PUBLIC_BASE}/espn-3.png",
    "Eurosport 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport-1.png",
    "RMC Sport 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/rmc-sport-1.png",
    "RMC Sport 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/rmc-sport-2.png",
    "MTV Hits": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-hits.png",
    "M6 Music": f"{LOCAL_LOGOS_PUBLIC_BASE}/m6-music.png",
    "Trace Urban": f"{LOCAL_LOGOS_PUBLIC_BASE}/trace-urban.png",
    "DAZN 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn-2.png",
    "DAZN FAST+": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn-fast.png",
    "Sport TV 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/sport-tv-1.png",
    "Sport TV 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/sport-tv-2.png",
    "Eleven Sports 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/eleven-sports-1.png",
    "Eleven Sports 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/eleven-sports-2.png",
}
CONTINUOUS_PROGRAMME_DETAILS = {
    "TVN3": (
        "Live",
        "",
    ),
    "CHV Deportes": (
        "Live",
        "",
    ),
    "XITE Hits Germany": (
        "XITE Hits Germany - videoclips",
        "Rotacion continua de videoclips musicales; no publica una parrilla horaria XMLTV estable.",
    ),
    "Arirang TV": (
        "Arirang TV en vivo",
        "Programacion continua de Arirang TV; la senal publica no ofrece una parrilla XMLTV estable.",
    ),
    "RedBull TV World": (
        "RedBull TV World en vivo",
        "Programacion continua de Red Bull TV; la senal inglesa no publica una parrilla XMLTV local estable.",
    ),
    "RedBull TV Español": (
        "RedBull TV Español en vivo",
        "Programacion continua de la senal chilena en espanol; la parrilla se obtiene desde Red Bull TV.",
    ),
    "M1": (
        "M1 - rotacion musical",
        "Rotacion continua de videos musicales de M1; los programas especiales pueden cambiar de horario.",
    ),
    "M2": (
        "M2 - rotacion musical",
        "Rotacion continua de videos musicales de M2; los programas especiales pueden cambiar de horario.",
    ),
    "XITE 80s Flashback": (
        "XITE 80s Flashback - videoclips",
        "Programacion musical de XITE; se conserva continuidad si la guia FAST no esta disponible.",
    ),
    "XITE 90s Throwback": (
        "XITE 90s Throwback - videoclips",
        "Programacion musical de XITE; se conserva continuidad si la guia FAST no esta disponible.",
    ),
    "MTV Classic": (
        "MTV Classic - videoclips",
        "Rotacion continua de videoclips clasicos de MTV; la senal no publica una parrilla XMLTV estable.",
    ),
    "MTV Biggest Pop": (
        "MTV Biggest Pop - videoclips",
        "Rotacion continua de videoclips pop de MTV; la senal no publica una parrilla XMLTV estable.",
    ),
    "MTV Spankin' New": (
        "MTV Spankin' New - videoclips",
        "Rotacion continua de novedades musicales de MTV; la senal no publica una parrilla XMLTV estable.",
    ),
    "XITE Rock x Metal": (
        "XITE Rock x Metal - videoclips",
        "Programacion musical de XITE; se conserva continuidad si la guia FAST no esta disponible.",
    ),
    "MTV Rocks": (
        "MTV Rocks - videoclips",
        "Rotacion continua de rock y videoclips de MTV; la senal no publica una parrilla XMLTV estable.",
    ),
    "XITE Just Chill": (
        "XITE Just Chill - videoclips",
        "Programacion musical de XITE; se conserva continuidad si la guia FAST no esta disponible.",
    ),
    "Premier Sports 1": (
        "Premier Sports 1 en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "Premier Sports 2": (
        "Premier Sports 2 en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "13 Cultura": (
        "13 Cultura en vivo",
        "Programacion continua de 13 Cultura; no publica una parrilla horaria XMLTV estable.",
    ),
    "13C": (
        "13C en vivo",
        "Programacion publica consultada en la guia de Zapping Chile.",
    ),
    "XITE Nuevo Latino": (
        "XITE Nuevo Latino - videoclips",
        "Rotacion continua de videoclips latinos; no publica una parrilla horaria XMLTV estable.",
    ),
    "XITE Siempre Latino": (
        "XITE Siempre Latino - videoclips",
        "Rotacion continua de videoclips latinos; no publica una parrilla horaria XMLTV estable.",
    ),
    "MTV Flow Latino": (
        "MTV Flow Latino - videoclips",
        "Rotacion continua de videoclips latinos de MTV; no publica una parrilla horaria XMLTV estable.",
    ),
    "Yo! MTV": (
        "Yo! MTV - videoclips",
        "Rotacion continua de videoclips de MTV; no publica una parrilla horaria XMLTV estable.",
    ),
    "Totalmusic 80s": (
        "Totalmusic 80s - videoclips",
        "Rotacion continua de videoclips de los 80; no publica una parrilla horaria XMLTV estable.",
    ),
    "Totalmusic 2000s": (
        "Totalmusic 2000s - videoclips",
        "Rotacion continua de videoclips de los 2000; no publica una parrilla horaria XMLTV estable.",
    ),
    "Totalmusic Concerts": (
        "Totalmusic Concerts - concierto",
        "Rotacion continua de conciertos y presentaciones musicales; no publica una parrilla horaria XMLTV estable.",
    ),
    "Totalmusic Dance": (
        "Totalmusic Dance - videoclips",
        "Rotacion continua de musica dance; no publica una parrilla horaria XMLTV estable.",
    ),
    "Reuters": (
        "Reuters en vivo",
        "Senal informativa continua de Reuters; no publica una parrilla horaria XMLTV estable.",
    ),
    "Real Wild": (
        "Real Wild en vivo",
        "Senal documental continua; no publica una parrilla horaria XMLTV estable.",
    ),
    "RWND": (
        "Live",
        "",
    ),
    "13 Kids": (
        "Live",
        "",
    ),
    "Autentic History": (
        "Live",
        "",
    ),
}
NEWS_CHANNEL_ORDER = ("24 Horas", "Meganoticias", "CHV Noticias", "T13")
PLAYER_USER_AGENT = "VLC/3.0.20 LibVLC/3.0.20"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
OFFICIAL_STREAM_PAGES = {
    "Mega": ["https://www.mega.cl/senal-en-vivo/"],
    "CHV": ["https://www.chilevision.cl/senal-online"],
    "Canal 13": ["https://www.13.cl/en-vivo"],
    "T13": ["https://www.t13.cl/en-vivo"],
    "24 Horas": ["https://www.24horas.cl/envivo"],
    "La Red": ["https://www.lared.cl/senal-online/"],
    "M1": ["https://m1.tv/live/"],
    "M2": ["https://m2.tv/stream/"],
}
OFFICIAL_CANDIDATE_HINTS = {
    "Mega": re.compile(r"mega", re.IGNORECASE),
    "Meganoticias": re.compile(r"(?:mega|meganoticias)", re.IGNORECASE),
    "CHV": re.compile(r"(?:chv|chilevision)", re.IGNORECASE),
    "Canal 13": re.compile(r"(?:13cl|canal.?13)", re.IGNORECASE),
    "T13": re.compile(r"(?:/t13/|t13\.)", re.IGNORECASE),
    "24 Horas": re.compile(
        r"(?:24horas|57d1a22064f5d85712b20dab|689ba606ecfe7915e1f8f741)",
        re.IGNORECASE,
    ),
    "La Red": re.compile(
        r"(?:lared|ds5i0a12qngha|airstream\.run|d1kqwrirylysyt)",
        re.IGNORECASE,
    ),
}
KNOWN_STREAM_FALLBACKS = {
    "TVN": [
        TVN_ALTERNATIVE_URL,
        "http://45.162.193.35/TVN/index.m3u8",
        "http://15.204.246.24:8080/TVNHD/index.m3u8",
    ],
    "Mega": [
        "http://tr.live.clarovtrcdn.vtrplay.com/megahdchi/vxfmt=dp/playlist.m3u8?device_profile=STB_HLS_VCAS_LIVE_HD",
        "https://iptv.bitred.cl/mega/index.m3u8",
        "http://15.204.246.24:8080/MEGAHD/index.m3u8",
        "https://unlimited1-cl-isp.dps.live/mega/mega.smil/playlist.m3u8",
        "https://pantera1-100gb-cl-movistar.dps.live/mega/mega.smil/playlist.m3u8",
    ],
    "CHV": [
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/chv/chv.smil/playlist.m3u8"
    ],
    "Canal 13": ["https://redirector.dps.live/hls/13cl/playlist.m3u8"],
    "T13": [
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/t13/t13.smil/playlist.m3u8"
    ],
    "24 Horas": [
        "https://mdstrm.com/live-stream-playlist/57d1a22064f5d85712b20dab.m3u8"
    ],
    "La Red": [
        LA_RED_MASTER_URL,
        "https://live2.airstream.run/3969875408/ts:abr.m3u8",
        "https://d1kqwrirylysyt.cloudfront.net/ts:abr.m3u8",
    ],
    "Arirang TV": [ARIRANG_TV_MASTER_URL],
    "DW Español": [
        "https://dwamdstream104.akamaized.net/hls/live/2015530/dwstream104/master.m3u8"
    ],
    "France 24 Español": [
        FRANCE24_ES_1080_URL
    ],
    "Euronews Español": [
        "https://cdn-euronews.akamaized.net/live/eds/euronews-es/25053/index.m3u8"
    ],
    "NHK World Japan": [NHK_MASTER_URL],
    "Al Jazeera English": ["https://live-hls-apps-aje-v3-fa.getaj.net/AJE/index.m3u8"],
    "RedBull TV World": [RED_BULL_WORLD_URL],
    "RedBull TV Español": [RED_BULL_CHILE_URL],
    "XITE Hits Germany": [
        "https://d726x48n2pd5h.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-skxr1pazhltvp/XITE_Hits.m3u8"
    ],
    "XITE 80s Flashback": [
        "https://d1n314cytqn9r3.cloudfront.net/XITE_80s_Flashback.m3u8"
    ],
    "XITE 90s Throwback": [
        "https://d284aawtm5vi48.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-fjdfi2br1jtq7/XITE_90s_Throwback.m3u8"
    ],
    "XITE Rock x Metal": [
        "https://d198ro05q94rc4.cloudfront.net/XITE_Rock_On.m3u8",
        "https://jmp2.uk/plu-623a1b5188ecdc0007c9ef5a.m3u8",
    ],
    "XITE Just Chill": [
        "https://dvnftgdlbnemm.cloudfront.net/XITE_Just_Chill.m3u8"
    ],
    "MTV Biggest Pop": [
        "https://jmp2.uk/plu-6047fabfce6e8e00070bcc9f.m3u8",
        "https://jmp2.uk/plu-5d14fd1a252d35decbc4080c.m3u8",
    ],
    "MTV Classic": [
        "https://jmp2.uk/plu-66a01dcb8561260008b0a41d.m3u8",
        "https://jmp2.uk/plu-654100b4bdf3cf0008aa49c7.m3u8",
        "https://jmp2.uk/plu-66a11a21a79dea0008aa90ca.m3u8",
    ],
    "MTV Spankin' New": [
        "https://jmp2.uk/plu-6541010f770cf1000866be98.m3u8",
        "https://jmp2.uk/plu-5d14fdb8ca91eedee1633117.m3u8",
    ],
    "MTV Rocks": [
        "https://jmp2.uk/plu-66a01e07d2d50d0008100d6a.m3u8",
        "https://jmp2.uk/plu-66a01b52a4ee27000808ea36.m3u8",
    ],
}
SEGMENT_CHECK_CHANNELS = {
    "TVN",
    "NTV",
    "TVN3",
    "Mega",
    "Meganoticias",
    "24 Horas",
    "La Red",
    "Canal 13",
    "CHV Noticias",
    "CHV Deportes",
    "France 24 Español",
    "DW Español",
    "Euronews Español",
    "NHK World Japan",
    "Al Jazeera English",
    "Arirang TV",
    "RedBull TV World",
    "RedBull TV Español",
    "XITE Hits Germany",
    "M1",
    "M2",
    "13C",
    "RWND",
    "BBC Earth FAST",
    "BBC News",
    "BBC Travel",
    "Bloomberg TV US",
    "Bloomberg Originals",
    "CBS News 24/7",
    "TRT World",
    "CNA",
    "Africanews English",
    "Qello Concerts by Stingray",
    "Stingray Classica",
    "Stingray DJAZZ",
    "XITE 80s Flashback",
    "XITE 90s Throwback",
    "MTV Classic",
    "MTV Biggest Pop",
    "MTV Spankin' New",
    "XITE Rock x Metal",
    "MTV Rocks",
    "XITE Just Chill",
    "Premier Sports 1",
    "Premier Sports 2",
    "Sky Sports Main Event",
    "Sky Sports+",
    "TNT Sports 3",
    "CNN",
    "RT France",
    "ESPN 3",
    "Eurosport 1",
    "RMC Sport 1",
    "RMC Sport 2",
    "MTV Hits",
    "M6 Music",
    "Trace Urban",
    "DAZN 2",
    "DAZN FAST+",
    "Sport TV 1",
    "Sport TV 2",
    "Eleven Sports 1",
    "Eleven Sports 2",
}
@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    url_line: int
    info_line: int = -1
    logo_url: str = ""
    group: str = ""
    tvg_id: str = ""
    display_name: str = ""


@dataclass(frozen=True)
class CheckResult:
    channel: str
    url: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class LogoResult:
    channel: str
    url: str
    ok: bool
    detail: str


def parse_channels(lines: list[str]) -> list[Channel]:
    channels: list[Channel] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXTINF:"):
            continue
        display_name = line.rsplit(",", 1)[-1].strip() or f"Canal en linea {index + 1}"
        name = DISPLAY_NAME_ALIASES.get(display_name, display_name)
        logo_match = re.search(r'\btvg-logo="([^"]+)"', line)
        group_match = re.search(r'\bgroup-title="([^"]+)"', line)
        id_match = re.search(r'\btvg-id="([^"]+)"', line)
        logo_url = logo_match.group(1) if logo_match else ""
        group = group_match.group(1) if group_match else ""
        tvg_id = id_match.group(1) if id_match else ""
        for url_line in range(index + 1, len(lines)):
            candidate = lines[url_line].strip()
            if not candidate:
                continue
            if candidate.startswith("#"):
                raise ValueError(f"{name}: falta la URL despues de #EXTINF")
            channels.append(
                Channel(
                    name,
                    candidate,
                    url_line,
                    index,
                    logo_url,
                    group,
                    tvg_id,
                    display_name,
                )
            )
            break
        else:
            raise ValueError(f"{name}: falta la URL al final del archivo")
    return channels


def pin_preferred_logos(lines: list[str]) -> bool:
    changed = False
    for channel in parse_channels(lines):
        preferred = PREFERRED_LOGOS.get(channel.name)
        if not preferred or channel.info_line < 0:
            continue
        original = lines[channel.info_line]
        updated = re.sub(
            r'(\btvg-logo=")[^"]+(\")',
            lambda match: f"{match.group(1)}{preferred}{match.group(2)}",
            original,
        )
        if updated != original:
            lines[channel.info_line] = updated
            changed = True
            print(f"  [OK] {channel.name}: logo preferido configurado")
    return changed


def pin_news_channel_order(lines: list[str]) -> bool:
    channels = {channel.name: channel for channel in parse_channels(lines)}
    if not all(name in channels for name in NEWS_CHANNEL_ORDER):
        return False
    slots = sorted(
        (channels[name].info_line, channels[name].url_line)
        for name in NEWS_CHANNEL_ORDER
    )
    current = [
        next(name for name in NEWS_CHANNEL_ORDER if channels[name].info_line == info_line)
        for info_line, _ in slots
    ]
    if tuple(current) == NEWS_CHANNEL_ORDER:
        return False
    records = {
        name: (lines[channels[name].info_line], lines[channels[name].url_line])
        for name in NEWS_CHANNEL_ORDER
    }
    for (info_line, url_line), name in zip(slots, NEWS_CHANNEL_ORDER):
        lines[info_line], lines[url_line] = records[name]
    print("  [OK] Noticias: orden 24 Horas, Meganoticias, CHV Noticias, T13")
    return True


def request_headers(channel: str) -> dict[str, str]:
    headers = {"User-Agent": PLAYER_USER_AGENT, "Accept": "*/*"}
    if channel in {"NTV", "TVN3", "TVN"}:
        headers["Referer"] = "https://live.tvn.cl/"
        headers["Origin"] = "https://live.tvn.cl"
    elif channel == "Mega":
        headers["Referer"] = MEGA_LIVE_PAGE
        headers["Origin"] = "https://www.mega.cl"
    elif channel == "Meganoticias":
        headers["Referer"] = MEGANOTICIAS_LIVE_PAGE
        headers["Origin"] = "https://www.meganoticias.cl"
    elif channel in {"CHV Noticias", "CHV Deportes"}:
        headers["Referer"] = "https://www.chilevision.cl/senal-online"
        headers["Origin"] = "https://www.chilevision.cl"
    elif channel == "Power Hit Radio":
        headers["Referer"] = "https://play.tv3.lt/"
        headers["Origin"] = "https://play.tv3.lt"
    return headers


def fetch_bytes(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = 25,
    context: ssl.SSLContext | None = None,
    limit: int = 262_144,
) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.status, response.read(limit), response.geturl()


def fetch_channel_bytes(
    url: str, headers: dict[str, str]
) -> tuple[int, bytes, str]:
    return fetch_bytes(url, headers)


def hls_attribute(line: str, name: str) -> str | None:
    match = re.search(
        rf"(?:^|[:,]){re.escape(name)}=(?:\"([^\"]*)\"|([^,]*))", line
    )
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2).strip()


def xmltv_datetime(value: str) -> datetime:
    match = re.match(r"^(\d{14})\s*([+-]\d{4})?", value.strip())
    if not match:
        raise ValueError(f"fecha XMLTV invalida: {value}")
    offset = match.group(2) or "+0000"
    return datetime.strptime(match.group(1) + " " + offset, "%Y%m%d%H%M%S %z")


def ensure_playlist_epg_url(lines: list[str]) -> bool:
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("la lista no tiene una cabecera #EXTM3U valida")
    header = re.sub(r'\s+(?:x-tvg-url|url-tvg)="[^"]*"', "", lines[0])
    expected = f'{header} x-tvg-url="{EPG_PUBLIC_URL}"'
    if lines[0] == expected:
        return False
    lines[0] = expected
    return True


def xmltv_format(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S +0000")


def xmltv_format_chile(value: datetime) -> str:
    """Format a timestamp in Santiago time for players that ignore offsets."""
    return value.astimezone(CHILE_TIMEZONE).strftime("%Y%m%d%H%M%S %z")


def localize_xmltv_programme(programme: ET.Element) -> ET.Element:
    localized = copy.deepcopy(programme)
    for attribute in ("start", "stop"):
        value = localized.get(attribute)
        if value:
            localized.set(attribute, xmltv_format_chile(xmltv_datetime(value)))
    return localized


def epg_status_from_xml(
    data: bytes,
    expected_ids: set[str],
    *,
    now: datetime,
    minimum_future: timedelta,
    allow_empty_ids: set[str] | None = None,
) -> dict:
    root = ET.fromstring(data)
    if root.tag != "tv":
        raise ValueError("la guia publicada no contiene una raiz XMLTV <tv>")
    channel_elements = root.findall("channel")
    channel_ids = {channel.get("id", "") for channel in channel_elements}
    missing = sorted(expected_ids - channel_ids)
    if missing:
        raise ValueError("faltan canales en la EPG: " + ", ".join(missing))

    counts = {channel_id: 0 for channel_id in expected_ids}
    last_by_channel: dict[str, datetime] = {}
    intervals_by_channel: dict[str, list[tuple[datetime, datetime]]] = {}
    first_start: datetime | None = None
    last_stop: datetime | None = None
    for programme in root.findall("programme"):
        channel_id = programme.get("channel", "")
        if channel_id not in expected_ids:
            continue
        start = xmltv_datetime(programme.get("start", ""))
        stop = xmltv_datetime(programme.get("stop", ""))
        counts[channel_id] += 1
        intervals_by_channel.setdefault(channel_id, []).append((start, stop))
        previous = last_by_channel.get(channel_id)
        last_by_channel[channel_id] = stop if previous is None or stop > previous else previous
        first_start = start if first_start is None or start < first_start else first_start
        last_stop = stop if last_stop is None or stop > last_stop else last_stop

    overlapping_channels = []
    for channel_id, intervals in intervals_by_channel.items():
        intervals.sort()
        previous_stop: datetime | None = None
        for start, stop in intervals:
            if previous_stop is not None and start < previous_stop:
                overlapping_channels.append(channel_id)
                break
            previous_stop = stop if previous_stop is None or stop > previous_stop else previous_stop
    if overlapping_channels:
        raise ValueError(
            "programas superpuestos en la EPG: " + ", ".join(sorted(overlapping_channels))
        )

    allowed_empty = set(allow_empty_ids or ()) & expected_ids
    empty = sorted(
        channel_id
        for channel_id, count in counts.items()
        if count == 0 and channel_id not in allowed_empty
    )
    if empty:
        raise ValueError("canales sin programas en la EPG: " + ", ".join(empty))
    expiring = sorted(
        channel_id
        for channel_id in expected_ids
        if channel_id not in allowed_empty
        and last_by_channel.get(channel_id, now) < now + minimum_future
    )
    if expiring:
        raise ValueError("programacion insuficiente para: " + ", ".join(expiring))
    if first_start is None or last_stop is None:
        raise ValueError("la EPG no contiene programas")

    generated_at_text = root.get("data-generated-at", "")
    generated_at = (
        datetime.fromisoformat(generated_at_text.replace("Z", "+00:00"))
        if generated_at_text
        else None
    )
    next_refresh_text = root.get("data-next-refresh-at", "")
    next_refresh: datetime | None = None
    if next_refresh_text:
        try:
            next_refresh = datetime.fromisoformat(
                next_refresh_text.replace("Z", "+00:00")
            )
            if next_refresh.tzinfo is None:
                next_refresh = next_refresh.replace(tzinfo=timezone.utc)
            next_refresh = next_refresh.astimezone(timezone.utc)
        except ValueError:
            next_refresh = None
    guide_types = {
        channel.get("id", ""): channel.get("data-guide", "real")
        for channel in channel_elements
        if channel.get("id", "") in expected_ids
    }
    return {
        "ok": True,
        "channels": len(expected_ids),
        "programmes": sum(counts.values()),
        "first_start_utc": first_start.astimezone(timezone.utc).isoformat(),
        "last_stop_utc": last_stop.astimezone(timezone.utc).isoformat(),
        "generated_at": generated_at.isoformat() if generated_at else None,
        "next_refresh_at": next_refresh.isoformat() if next_refresh else None,
        "guide_types": guide_types,
    }


def normalize_red_bull_schedule(schedule: list[dict]) -> list[dict]:
    """Return a chronological, non-overlapping linear guide."""
    ordered: list[dict] = []
    sortable: list[tuple[datetime, dict]] = []
    for item in schedule:
        try:
            start = datetime.fromisoformat(item["start_time"].replace("Z", "+00:00"))
            stop = datetime.fromisoformat(item["end_time"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if stop > start:
            sortable.append((start, item))

    # The API can briefly return duplicate or overlapping cards while its guide
    # rolls over. A linear XMLTV channel must expose one programme at a time.
    previous_stop: datetime | None = None
    for start, source_item in sorted(sortable, key=lambda pair: pair[0]):
        stop = datetime.fromisoformat(source_item["end_time"].replace("Z", "+00:00"))
        if previous_stop is not None and start < previous_stop:
            if stop <= previous_stop:
                continue
            item = dict(source_item)
            item["start_time"] = previous_stop.isoformat()
            start = previous_stop
        else:
            item = source_item
        ordered.append(item)
        previous_stop = (
            stop
            if previous_stop is None or stop > previous_stop
            else previous_stop
        )
    return ordered


def red_bull_page_schedule(now: datetime) -> list[dict]:
    """Read the Spanish World of Red Bull rail from the official TV guide page."""
    status, body, _ = fetch_bytes(
        RED_BULL_SPANISH_EPG_PAGE,
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "es-CL,es;q=0.9",
        },
        timeout=90,
        limit=30_000_000,
    )
    if status != 200:
        raise ValueError(f"pagina EPG Red Bull HTTP {status}")
    html = body.decode("utf-8", "replace")
    rails = None
    for script in re.findall(r"<script[^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL):
        if "channelRails" not in script:
            continue
        match = re.fullmatch(
            r"\s*self\.__next_f\.push\(\[1,(.*)\]\)\s*", script, re.DOTALL
        )
        if not match:
            continue
        try:
            decoded = json.loads(match.group(1))
            marker = '"channelRails":'
            marker_start = decoded.index(marker) + len(marker)
            rails, _ = json.JSONDecoder().raw_decode(decoded, marker_start)
            break
        except (IndexError, json.JSONDecodeError, TypeError, ValueError):
            continue
    if not isinstance(rails, list):
        raise ValueError("pagina EPG Red Bull no contiene channelRails")

    world_rail = next(
        (
            rail
            for rail in rails
            if isinstance(rail, dict)
            and str(rail.get("title", "")).strip().lower() == "world of red bull"
        ),
        None,
    )
    if not isinstance(world_rail, dict):
        raise ValueError("pagina EPG Red Bull no contiene la rail World of Red Bull")

    schedule: list[dict] = []
    for card in world_rail.get("cards", []):
        if not isinstance(card, dict):
            continue
        title = card.get("title")
        start = card.get("start_time")
        stop = card.get("end_time")
        if not title or not start or not stop:
            continue
        try:
            if datetime.fromisoformat(stop.replace("Z", "+00:00")) <= now - timedelta(
                hours=1
            ):
                continue
        except (TypeError, ValueError):
            continue
        schedule.append(
            {
                "start_time": start,
                "end_time": stop,
                "title": title,
                "subheading": card.get("subheading"),
                "short_description": card.get("short_description"),
                "long_description": card.get("long_description"),
                "lang": "es",
            }
        )
    schedule = normalize_red_bull_schedule(schedule)
    if len(schedule) < 5:
        raise ValueError("pagina EPG Red Bull entrego una parrilla demasiado corta")
    return schedule


def red_bull_api_schedule(locale: str) -> list[dict]:
    """Read the current Red Bull linear schedule using a short-lived API session."""
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "es-CL,es;q=0.9",
    }
    status, body, _ = fetch_bytes(
        f"{RED_BULL_SESSION_URL}&locale={locale}",
        headers,
        timeout=60,
        limit=1_048_576,
    )
    if status != 200:
        raise ValueError(f"sesion Red Bull HTTP {status}")
    session = json.loads(body)
    token = session.get("token")
    if not token:
        raise ValueError("Red Bull no entrego token de sesion")

    epg_headers = dict(headers)
    epg_headers["Authorization"] = token
    status, body, _ = fetch_bytes(
        RED_BULL_OFFICIAL_EPG_URL,
        epg_headers,
        timeout=60,
        limit=10_485_760,
    )
    if status != 200:
        raise ValueError(f"EPG Red Bull HTTP {status}")
    payload = json.loads(body)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("EPG Red Bull no contiene items")

    language = "es" if locale.startswith("es") else "en"
    schedule: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        title = item.get("title")
        start = item.get("start_time")
        stop = item.get("end_time")
        if not title or not start or not stop:
            continue
        key = (start, stop, title)
        if key in seen:
            continue
        seen.add(key)
        schedule.append(
            {
                "start_time": start,
                "end_time": stop,
                "title": title,
                "subheading": item.get("subheading"),
                "short_description": item.get("short_description"),
                "long_description": item.get("long_description"),
                "lang": language,
            }
        )
    schedule = normalize_red_bull_schedule(schedule)
    if len(schedule) < 5:
        raise ValueError("EPG Red Bull entrego una parrilla demasiado corta")
    return schedule


def red_bull_relay_schedule(now: datetime) -> list[dict]:
    """Use the GitHub-documented relay only when it has a current guide."""
    status, body, _ = fetch_bytes(
        RED_BULL_RELAY_EPG_URL,
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/xml,text/xml,*/*",
        },
        timeout=60,
        limit=10_485_760,
    )
    if status != 200:
        raise ValueError(f"relay Red Bull HTTP {status}")
    root = ET.fromstring(body)
    schedule: list[dict] = []
    for programme in root.findall("programme"):
        if programme.get("channel") != "10001":
            continue
        start_value = programme.get("start")
        stop_value = programme.get("stop")
        title_element = programme.find("title")
        if not start_value or not stop_value or title_element is None:
            continue
        start = xmltv_datetime(start_value)
        stop = xmltv_datetime(stop_value)
        if stop <= now - timedelta(hours=1):
            continue
        schedule.append(
            {
                "start_time": start.isoformat(),
                "end_time": stop.isoformat(),
                "title": (title_element.text or "Red Bull TV").strip(),
                "subheading": None,
                "short_description": None,
                "long_description": None,
                "lang": title_element.get("lang") or "en",
            }
        )
    schedule = normalize_red_bull_schedule(schedule)
    if len(schedule) < 5:
        raise ValueError("relay Red Bull entrego una parrilla demasiado corta")
    last_stop = datetime.fromisoformat(schedule[-1]["end_time"])
    if last_stop < now + timedelta(hours=24):
        raise ValueError("relay Red Bull no cubre las proximas 24 horas")
    return schedule


def fetch_red_bull_schedules(
    expected_ids: set[str], now: datetime
) -> tuple[dict[str, list[dict]], set[str], dict[str, str]]:
    schedules: dict[str, list[dict]] = {}
    source_names: set[str] = set()
    errors: dict[str, str] = {}
    for channel_id, locale in RED_BULL_CHANNEL_LOCALES.items():
        if channel_id not in expected_ids:
            continue
        if channel_id == RED_BULL_CHILE_ID:
            try:
                schedules[channel_id] = red_bull_page_schedule(now)
                source_names.add("red-bull-es-oficial-page")
                continue
            except Exception as page_error:
                try:
                    schedules[channel_id] = red_bull_api_schedule(locale)
                    source_names.add("red-bull-oficial-fallback")
                    continue
                except Exception as official_error:
                    errors[f"red_bull:{channel_id}"] = (
                        f"pagina: {page_error}; API: {official_error}"
                    )
                    continue
        try:
            schedules[channel_id] = red_bull_api_schedule(locale)
            source_names.add("red-bull-oficial")
        except Exception as official_error:
            if channel_id != RED_BULL_WORLD_ID:
                errors[f"red_bull:{channel_id}"] = str(official_error)
                continue
            try:
                schedules[channel_id] = red_bull_relay_schedule(now)
                source_names.add("red-bull-relay")
            except Exception as relay_error:
                errors[f"red_bull:{channel_id}"] = (
                    f"oficial: {official_error}; relay: {relay_error}"
                )
    return schedules, source_names, errors


MEGA_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def mega_jsonld_objects(value):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from mega_jsonld_objects(graph)
    elif isinstance(value, list):
        for item in value:
            yield from mega_jsonld_objects(item)


def mega_article_payloads(page_html: str) -> list[tuple[str, str]]:
    payloads: list[tuple[str, str]] = []
    blocks = re.findall(
        r'<script\b(?=[^>]*application/ld\+json)[^>]*>(.*?)</script\s*>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for block in blocks:
        try:
            # Mega publica saltos de linea literales dentro de articleBody.
            data = json.loads(html.unescape(block), strict=False)
        except json.JSONDecodeError:
            continue
        for item in mega_jsonld_objects(data):
            headline = item.get("headline") if isinstance(item, dict) else None
            body = item.get("articleBody") if isinstance(item, dict) else None
            if isinstance(headline, str) and isinstance(body, str):
                payloads.append((headline, body))
    return payloads


def mega_article_date(headline: str, year: int):
    match = re.search(
        r"\b(\d{1,2})\s+de\s+([a-z]+)", headline.casefold()
    )
    if not match:
        return None
    month = MEGA_MONTHS.get(match.group(2))
    if month is None:
        return None
    try:
        return datetime(year, month, int(match.group(1))).date()
    except ValueError:
        return None


def mega_schedule_items(article_body: str) -> list[tuple[object, str]]:
    text = html.unescape(article_body)
    text = re.sub(r"<br\s*/?>|</(?:p|li)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    items: list[tuple[object, str]] = []
    for raw_line in re.split(r"\r?\n", text):
        line = re.sub(r"\s+", " ", raw_line).strip(" \t-*\u2022")
        match = re.match(
            r"(.+?):\s*(\d{1,2}):(\d{2})\s*(?:horas?)?\.?$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        hour, minute = int(match.group(2)), int(match.group(3))
        if hour > 23 or minute > 59:
            continue
        title = re.sub(r"\s+", " ", match.group(1)).strip(" .")
        if title:
            items.append((datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time(), title))
    return items


def tvn_official_title(value: str) -> str:
    title = re.sub(r"\s+", " ", value).strip()
    if title.isupper():
        return title.title()
    return title


LA_RED_DAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def la_red_html_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def la_red_schedule_items(page_html: str) -> dict[int, list[tuple[object, str]]]:
    """Extract the official La Red weekly tabs keyed by weekday index."""
    day_pattern = re.compile(
        r'<div\b'
        r'(?=[^>]*\bid=["\'](?P<day>mon|tue|wed|thu|fri|sat|sun)["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\btab_content\b[^"\']*\bshows-list\b[^"\']*["\'])'
        r'[^>]*>',
        re.IGNORECASE,
    )
    item_pattern = re.compile(
        r'<div\b'
        r'(?=[^>]*\bclass=["\'][^"\']*\bitem\b[^"\']*["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\bparent\b[^"\']*["\'])'
        r'[^>]*>(.*?)'
        r'(?=<div\b'
        r'(?=[^>]*\bclass=["\'][^"\']*\bitem\b[^"\']*["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\bparent\b[^"\']*["\'])'
        r'[^>]*>|$)',
        re.IGNORECASE | re.DOTALL,
    )
    time_pattern = re.compile(
        r'<div\b[^>]*\bclass=["\'][^"\']*\bhour\b[^"\']*["\'][^>]*>'
        r'.*?<p\b[^>]*>(\d{1,2}):(\d{2})</p\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'<[^>]*\bclass=["\'][^"\']*\bprograma-name\b[^"\']*["\'][^>]*>'
        r'(.*?)</p\s*>',
        re.IGNORECASE | re.DOTALL,
    )

    day_markers = list(day_pattern.finditer(page_html))
    schedules: dict[int, list[tuple[object, str]]] = {}
    for index, marker in enumerate(day_markers):
        day_index = LA_RED_DAY_INDEX[marker.group("day").casefold()]
        body_end = (
            day_markers[index + 1].start()
            if index + 1 < len(day_markers)
            else len(page_html)
        )
        day_html = page_html[marker.end() : body_end]
        items: list[tuple[object, str]] = []
        for item_match in item_pattern.finditer(day_html):
            time_match = time_pattern.search(item_match.group(1))
            title_match = title_pattern.search(item_match.group(1))
            if not time_match or not title_match:
                continue
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            if hour > 23 or minute > 59:
                continue
            title = la_red_html_text(title_match.group(1))
            if title:
                items.append(
                    (
                        datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time(),
                        title,
                    )
                )
        if items:
            schedules[day_index] = items
    return schedules


def fetch_la_red_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == "0102" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": LA_RED_PROGRAMMING_PAGE,
    }
    try:
        status, body, _ = fetch_bytes(
            LA_RED_PROGRAMMING_PAGE,
            headers,
            timeout=60,
            limit=8_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")

        schedules = la_red_schedule_items(decode_web_text(body))
        if sum(len(items) for items in schedules.values()) < 5:
            raise ValueError("La Red no publico una parrilla oficial suficiente")

        chile_today = now.astimezone(CHILE_TIMEZONE).date()
        week_start = chile_today - timedelta(days=chile_today.weekday())
        starts: list[tuple[datetime, str]] = []
        for day_index, items in schedules.items():
            schedule_day = week_start + timedelta(days=day_index)
            previous_start: datetime | None = None
            for start_clock, title in items:
                start = datetime.combine(
                    schedule_day, start_clock, tzinfo=CHILE_TIMEZONE
                )
                if previous_start is not None and start <= previous_start:
                    start += timedelta(days=1)
                starts.append((start, title))
                previous_start = start

        unique_starts: dict[datetime, str] = {}
        for start, title in starts:
            unique_starts.setdefault(start, title)
        ordered = sorted(unique_starts.items())

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u La Red importer",
                "source-info-name": LA_RED_PROGRAMMING_PAGE,
            },
        )
        lower_limit = now - timedelta(hours=6)
        upper_limit = now + timedelta(days=8)
        programme_count = 0
        last_stop: datetime | None = None
        for index, (start, title) in enumerate(ordered):
            stop = (
                ordered[index + 1][0]
                if index + 1 < len(ordered)
                else start + timedelta(hours=2)
            )
            if stop <= start:
                continue
            if stop < lower_limit or start > upper_limit:
                continue
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": "0102",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                "Programacion oficial consultada en La Red."
            )
            programme_count += 1
            last_stop = stop if last_stop is None or stop > last_stop else last_stop

        future_limit = now + timedelta(hours=24)
        if programme_count < 5 or last_stop is None or last_stop < future_limit:
            raise ValueError(
                "La Red no publico una parrilla oficial con 24 horas futuras"
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def tvn_jsonp_items(data: bytes) -> list[dict]:
    text = decode_web_text(data).strip()
    match = re.search(
        r"jsonp\s*\(\s*(\[.*\])\s*\)\s*;?\s*$",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError("TVN no publico un JSONP valido")
    payload = json.loads(match.group(1))
    if not isinstance(payload, list):
        raise ValueError("la parrilla JSON de TVN no es una lista")
    return [item for item in payload if isinstance(item, dict)]


def fetch_tvn_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == "0104" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json,text/javascript,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": TVN_PROGRAMMING_PAGE,
    }
    # El CDN estatico de TVN mantiene vencido su certificado; el endpoint se
    # consulta solo como fuente oficial de parrilla y ya usa este mismo
    # contexto de compatibilidad para la pagina de TVN.
    insecure_context = ssl.create_default_context()
    insecure_context.check_hostname = False
    insecure_context.verify_mode = ssl.CERT_NONE
    try:
        chile_today = now.astimezone(CHILE_TIMEZONE).date()
        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u TVN importer",
                "source-info-name": TVN_PROGRAMMING_PAGE,
            },
        )
        seen: set[tuple[str, str, str]] = set()
        programme_count = 0
        source_errors: list[str] = []
        for offset in range(-1, 8):
            schedule_day = chile_today + timedelta(days=offset)
            url = (
                f"{TVN_PROGRAMMING_BASE_URL}/{schedule_day:%Y/%m/%d}"
                "/programacion.json"
            )
            try:
                status, body, _ = fetch_bytes(
                    url,
                    headers,
                    timeout=60,
                    context=insecure_context,
                    limit=2_000_000,
                )
                if status != 200:
                    raise ValueError(f"HTTP {status}")
                items = tvn_jsonp_items(body)
            except Exception as error:
                source_errors.append(f"{schedule_day}: {error}")
                continue

            for item in items:
                if item.get("senal") not in (5, "5"):
                    continue
                date_text = str(item.get("fecha", "")).strip()
                start_text = str(item.get("horaInicio", "")).strip()
                stop_text = str(item.get("horaTermino", "")).strip()
                title = tvn_official_title(str(item.get("programa", "")))
                if not (date_text and start_text and stop_text and title):
                    continue
                try:
                    start_date = datetime.strptime(
                        date_text, "%d/%m/%Y"
                    ).date()
                    start_clock = datetime.strptime(
                        start_text, "%H:%M:%S"
                    ).time()
                    stop_clock = datetime.strptime(
                        stop_text, "%H:%M:%S"
                    ).time()
                except ValueError:
                    continue

                start = datetime.combine(
                    start_date, start_clock, tzinfo=CHILE_TIMEZONE
                )
                stop_date = (
                    start_date + timedelta(days=1)
                    if stop_clock <= start_clock
                    else start_date
                )
                stop = datetime.combine(
                    stop_date, stop_clock, tzinfo=CHILE_TIMEZONE
                )
                if stop <= start:
                    continue
                if stop < now - timedelta(hours=6):
                    continue
                if start > now + timedelta(days=8):
                    continue
                key = (start.isoformat(), stop.isoformat(), title)
                if key in seen:
                    continue
                seen.add(key)
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": "0104",
                    },
                )
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                    "Programacion oficial consultada en TVN."
                )
                programme_count += 1

        if programme_count < 5:
            detail = "; ".join(source_errors[:2])
            suffix = f" ({detail})" if detail else ""
            raise ValueError(
                f"TVN publico una parrilla oficial demasiado corta{suffix}"
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_nhk_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the English NHK World schedule instead of domestic NHK XMLTV."""
    if not any(channel.tvg_id == "NHKWorldJapan.jp" for channel in channels):
        return None, None

    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": NHK_WORLD_LIVE_PAGE,
    }
    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u NHK World importer",
            "source-info-name": NHK_WORLD_LIVE_PAGE,
        },
    )
    records: list[dict[str, object]] = []
    source_errors: list[str] = []
    nhk_today = now.astimezone(NHK_TIMEZONE).date()

    for offset in range(-1, 10):
        schedule_day = nhk_today + timedelta(days=offset)
        url = f"{NHK_WORLD_EPG_BASE_URL}/{schedule_day:%Y%m%d}.json"
        try:
            status, body, _ = fetch_bytes(
                url,
                headers,
                timeout=60,
                limit=2_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            payload = json.loads(decode_web_text(body))
            items = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                raise ValueError("NHK no publico un campo data valido")
        except Exception as error:
            source_errors.append(f"{schedule_day}: {error}")
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            start_text = str(item.get("startTime", "")).strip()
            stop_text = str(item.get("endTime", "")).strip()
            if not start_text or not stop_text:
                continue
            try:
                start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
                stop = datetime.fromisoformat(stop_text.replace("Z", "+00:00"))
            except ValueError:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=NHK_TIMEZONE)
            if stop.tzinfo is None:
                stop = stop.replace(tzinfo=NHK_TIMEZONE)
            if stop <= start:
                continue

            is_extract_marker = item.get("extractProgram") in (1, "1", True)
            if is_extract_marker:
                # NHK World uses one-minute INFO markers between some shows.
                # Its official page extends the preceding show to the marker's
                # end and hides the marker itself.
                if records and stop > records[-1]["stop"]:
                    records[-1]["stop"] = stop
                continue
            if item.get("wstrm") not in (1, "1", True):
                continue

            title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
            if not title or title.casefold() == "info":
                continue
            episode_title = re.sub(
                r"\s+", " ", str(item.get("episodeTitle", ""))
            ).strip()
            description = re.sub(
                r"\s+", " ", str(item.get("description", ""))
            ).strip()
            records.append(
                {
                    "start": start,
                    "stop": stop,
                    "title": title,
                    "episode_title": episode_title,
                    "description": description,
                    "link": str(item.get("link", "")).strip(),
                }
            )

    seen: set[tuple[str, str, str]] = set()
    programme_count = 0
    lower_limit = now - timedelta(hours=6)
    upper_limit = now + timedelta(days=8)
    for record in sorted(records, key=lambda value: value["start"]):
        start = record["start"]
        stop = record["stop"]
        title = record["title"]
        if not isinstance(start, datetime) or not isinstance(stop, datetime):
            continue
        if not isinstance(title, str) or stop < lower_limit or start > upper_limit:
            continue
        key = (start.isoformat(), stop.isoformat(), title)
        if key in seen:
            continue
        seen.add(key)
        programme = ET.SubElement(
            root,
            "programme",
            {
                "start": xmltv_format(start),
                "stop": xmltv_format(stop),
                "channel": "NHKWorldJapan.jp",
            },
        )
        ET.SubElement(programme, "title", {"lang": "en"}).text = title
        episode_title = record["episode_title"]
        if isinstance(episode_title, str) and episode_title:
            ET.SubElement(programme, "sub-title", {"lang": "en"}).text = (
                episode_title
            )
        description = record["description"]
        if isinstance(description, str) and description:
            ET.SubElement(programme, "desc", {"lang": "en"}).text = description
        link = record["link"]
        if isinstance(link, str) and link:
            ET.SubElement(programme, "url").text = link
        programme_count += 1

    future_limit = now + timedelta(hours=24)
    has_future_schedule = any(
        isinstance(record["stop"], datetime) and record["stop"] >= future_limit
        for record in records
    )
    if programme_count < 5 or not has_future_schedule:
        detail = "; ".join(source_errors[:2])
        suffix = f" ({detail})" if detail else ""
        raise_error = (
            "NHK World publico una parrilla oficial demasiado corta"
            if programme_count < 5
            else "NHK World no publico 24 horas futuras"
        )
        return None, f"ValueError: {raise_error}{suffix}"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), None


def fetch_mega_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    if not any(channel.tvg_id == "0105" for channel in channels):
        return None, None
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        status, body, _ = fetch_bytes(
            MEGA_PROGRAMMING_PAGE, headers, timeout=60, limit=8_388_608
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        page_html = decode_web_text(body)
        article_urls: list[str] = []
        for raw_url in re.findall(
            r"https://www\.mega\.cl/programacion/[^\"'<>\s]+?\.html",
            page_html,
            flags=re.IGNORECASE,
        ):
            url = html.unescape(raw_url).replace("\\/", "/")
            if url not in article_urls:
                article_urls.append(url)

        payloads = mega_article_payloads(page_html)
        for article_url in article_urls:
            status, article_body, _ = fetch_bytes(
                article_url, headers, timeout=60, limit=8_388_608
            )
            if status == 200:
                payloads.extend(mega_article_payloads(decode_web_text(article_body)))

        today = now.astimezone(CHILE_TIMEZONE).date()
        valid_dates = {
            today + timedelta(days=offset) for offset in range(-1, 8)
        }
        schedules: dict[object, list[tuple[object, str]]] = {}
        for headline, article_body in payloads:
            schedule_day = mega_article_date(headline, today.year)
            if schedule_day not in valid_dates:
                continue
            items = mega_schedule_items(article_body)
            if len(items) >= 3 and schedule_day not in schedules:
                schedules[schedule_day] = items
        if len(schedules) < 2:
            raise ValueError("Mega no publico dos dias de parrilla oficial")

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u Mega importer",
                "source-info-name": MEGA_PROGRAMMING_PAGE,
            },
        )
        for schedule_day in sorted(schedules):
            starts: list[tuple[datetime, str]] = []
            previous_start: datetime | None = None
            for start_clock, title in schedules[schedule_day]:
                start = datetime.combine(
                    schedule_day, start_clock, tzinfo=CHILE_TIMEZONE
                )
                if previous_start is not None and start <= previous_start:
                    start += timedelta(days=1)
                starts.append((start, title))
                previous_start = start
            for index, (start, title) in enumerate(starts):
                stop = (
                    starts[index + 1][0]
                    if index + 1 < len(starts)
                    else start + timedelta(hours=2)
                )
                if stop <= start:
                    stop = start + timedelta(minutes=30)
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": "0105",
                    },
                )
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                    "Programacion oficial consultada en Mega."
                )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def decode_web_text(data: bytes) -> str:
    decoded = data.decode("utf-8", "replace")
    if "\ufffd" in decoded:
        return data.decode("cp1252", "replace")
    return decoded


CANAL13_WEEKDAY_INDEX = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}
CANAL13_MONTH_INDEX = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def canal13_official_payload(page_html: str) -> dict:
    """Extract the JSON object embedded by the official 13C guide page."""
    match = re.search(
        r"const\s+programacionJson\s*=\s*(\{.*?\})\s*;\s*"
        r"console\.log\(programacionJson(?:\.titulo)?\)",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError("Canal 13 no publico programacionJson para 13C")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict) or not isinstance(payload.get("dias"), dict):
        raise ValueError("el JSON oficial de 13C no contiene dias validos")
    return payload


def canal13_schedule_date(
    day_name: str, day_number: int, title: str, now: datetime
) -> object:
    """Resolve the date printed by 13.cl and tolerate a stale week label."""
    normalized_day = re.sub(r"\s+", "", day_name.casefold())
    weekday = CANAL13_WEEKDAY_INDEX.get(normalized_day)
    if weekday is None:
        raise ValueError(f"dia no reconocido en la guia 13C: {day_name}")
    title_match = re.search(
        r"\b([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(20\d{2})\b", title
    )
    if not title_match:
        raise ValueError("la guia oficial de 13C no contiene mes y ano")
    month_name = title_match.group(1).casefold()
    month = CANAL13_MONTH_INDEX.get(month_name)
    if month is None:
        raise ValueError(f"mes no reconocido en la guia 13C: {month_name}")
    year = int(title_match.group(2))
    try:
        candidate = datetime(year, month, day_number, tzinfo=CHILE_TIMEZONE).date()
    except ValueError as error:
        raise ValueError(f"fecha invalida en la guia oficial de 13C: {error}") from error
    if candidate.weekday() == weekday:
        return candidate

    # A stale cached title can carry the wrong month/year. Search a narrow
    # window while retaining the day number and weekday printed by the page.
    reference = now.astimezone(CHILE_TIMEZONE).date()
    for delta in range(-370, 371):
        alternative = reference + timedelta(days=delta)
        if alternative.day == day_number and alternative.weekday() == weekday:
            return alternative
    raise ValueError(f"no se pudo ubicar la fecha de {day_name} {day_number}")


def fetch_13c_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the real weekly 13C guide from Canal 13 before Zapping."""
    if not any(channel.tvg_id == "13C.cl@SD" for channel in channels):
        return None, None
    try:
        status, body, _ = fetch_bytes(
            CANAL13_13C_PROGRAMMING_PAGE,
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
                "Referer": "https://www.13.cl/c",
            },
            timeout=60,
            limit=10_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        payload = canal13_official_payload(decode_web_text(body))
        title = str(payload.get("titulo", "")).strip()
        raw_days = payload.get("dias")
        if not isinstance(raw_days, dict):
            raise ValueError("la guia oficial de 13C no contiene un objeto dias")

        records: list[tuple[datetime, str]] = []
        for day_name, date_objects in raw_days.items():
            if not isinstance(date_objects, dict):
                continue
            for date_text, schedule in date_objects.items():
                if not isinstance(schedule, dict):
                    continue
                day_match = re.search(r"(\d{1,2})", str(date_text))
                if not day_match:
                    continue
                schedule_date = canal13_schedule_date(
                    str(day_name), int(day_match.group(1)), title, now
                )
                parsed: list[tuple[object, str]] = []
                for clock_text, raw_title in schedule.items():
                    clock_match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(clock_text).strip())
                    if not clock_match:
                        continue
                    hour, minute = int(clock_match.group(1)), int(clock_match.group(2))
                    if hour > 23 or minute > 59:
                        continue
                    clean_title = re.sub(r"\s+", " ", str(raw_title)).strip()
                    if not clean_title:
                        continue
                    marker = ""
                    marker_match = re.search(r"\s+([RE])\s*$", clean_title, re.IGNORECASE)
                    if marker_match:
                        marker = " (Estreno)" if marker_match.group(1).upper() == "E" else " (R)"
                        clean_title = clean_title[: marker_match.start()].rstrip()
                    parsed.append(
                        (
                            datetime.strptime(
                                f"{hour:02d}:{minute:02d}", "%H:%M"
                            ).time(),
                            clean_title + marker,
                        )
                    )
                previous_start: datetime | None = None
                for start_clock, clean_title in parsed:
                    start = datetime.combine(
                        schedule_date, start_clock, tzinfo=CHILE_TIMEZONE
                    )
                    if previous_start is not None and start <= previous_start:
                        start += timedelta(days=1)
                    records.append((start, clean_title))
                    previous_start = start

        unique_records: dict[datetime, str] = {}
        for start, clean_title in records:
            unique_records.setdefault(start, clean_title)
        ordered = sorted(unique_records.items())
        lower_limit = now - timedelta(hours=6)
        upper_limit = now + timedelta(days=8)
        filtered = [
            (start, clean_title)
            for start, clean_title in ordered
            if start <= upper_limit and start + timedelta(minutes=1) >= lower_limit
        ]
        if len(filtered) < 5:
            raise ValueError("Canal 13 no publico una parrilla oficial vigente suficiente")

        root = ET.Element(
            "tv",
            {
                "generator-info-name": "lista-m3u Canal 13 13C importer",
                "source-info-name": CANAL13_13C_PROGRAMMING_PAGE,
            },
        )
        programme_count = 0
        for index, (start, clean_title) in enumerate(filtered):
            stop = (
                filtered[index + 1][0]
                if index + 1 < len(filtered)
                else start + timedelta(hours=2)
            )
            if stop <= start:
                continue
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": "13C.cl@SD",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = clean_title
            ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                "Programacion oficial consultada en Canal 13 para 13C."
            )
            programme_count += 1
        if programme_count < 5:
            raise ValueError("la guia oficial de 13C no contiene bloques utilizables")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def zapping_html_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def zapping_schedule_rows(page_html: str) -> list[tuple[datetime, str]]:
    """Extract absolute-start programmes from a public Zapping guide page."""
    today_marker = re.search(
        r'<div\b[^>]*class=["\'][^"\']*\btoday-schedule\b[^"\']*["\']',
        page_html,
        re.IGNORECASE,
    )
    if not today_marker:
        raise ValueError("la guia Zapping no contiene la parrilla del dia")

    rows: list[tuple[datetime, str]] = []
    current_html = page_html[: today_marker.start()]
    current_info = re.search(r'href=["\']info/(\d+)["\']', current_html, re.IGNORECASE)
    current_title = re.search(r"<h4\b[^>]*>(.*?)</h4\s*>", current_html, re.IGNORECASE | re.DOTALL)
    if current_info and current_title:
        rows.append(
            (
                datetime.fromtimestamp(int(current_info.group(1)), timezone.utc),
                zapping_html_text(current_title.group(1)),
            )
        )

    item_pattern = re.compile(
        r'<a\b'
        r'(?=[^>]*\bhref=["\']info/(\d+)["\'])'
        r'(?=[^>]*\bclass=["\'][^"\']*\bepg-item\b[^"\']*["\'])'
        r'[^>]*>(.*?)</a\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'class=["\'][^"\']*\bepg-schedule-title\b[^"\']*["\'][^>]*>(.*?)</p\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in item_pattern.finditer(page_html[today_marker.start() :]):
        title_match = title_pattern.search(match.group(2))
        if not title_match:
            continue
        title = zapping_html_text(title_match.group(1))
        if not title:
            continue
        start = datetime.fromtimestamp(int(match.group(1)), timezone.utc)
        rows.append((start, title))

    unique: dict[datetime, str] = {}
    for start, title in rows:
        unique.setdefault(start, title)
    return sorted(unique.items())


def fetch_zapping_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    targets = [
        (channel.tvg_id, ZAPPING_EPG_CHANNELS[channel.tvg_id])
        for channel in channels
        if channel.tvg_id in ZAPPING_EPG_CHANNELS
    ]
    if not targets:
        return None, {}

    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u Zapping guide importer",
            "source-info-name": ZAPPING_EPG_BASE_URL,
        },
    )
    errors: dict[str, str] = {}
    found_by_target = {target_id: 0 for target_id, _ in targets}
    for target_id, slug in targets:
        url = f"{ZAPPING_EPG_BASE_URL}/{slug}/"
        try:
            status, body, _ = fetch_bytes(
                url,
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
                timeout=60,
                limit=4_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            rows = zapping_schedule_rows(decode_web_text(body))
            if len(rows) < 3:
                raise ValueError("la guia Zapping contiene muy pocos bloques")

            for index, (start, title) in enumerate(rows):
                stop = (
                    rows[index + 1][0]
                    if index + 1 < len(rows)
                    else start + timedelta(hours=3)
                )
                if stop <= start:
                    continue
                if stop < now - timedelta(hours=6) or start > now + timedelta(days=4):
                    continue
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": target_id,
                    },
                )
                ET.SubElement(programme, "title", {"lang": "es"}).text = title
                ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                    "Programacion publica consultada en la guia de Zapping Chile."
                )
                found_by_target[target_id] += 1
        except Exception as error:
            errors[target_id] = f"{type(error).__name__}: {error}"

    for target_id, count in found_by_target.items():
        if count == 0:
            errors[target_id] = "la guia Zapping no publico bloques utilizables"

    # La fuente es opcional y se selecciona por canal. Una pagina que falle no
    # invalida los bloques validos de las otras paginas; build_epg usa esos
    # bloques y deja el fallback configurado para los canales sin cobertura.
    if not any(found_by_target.values()):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors


UKRAINIAN_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
UKRAINIAN_MUSIC_SCHEDULE_PAGES = {
    "M1.ua@SD": ("M1", "https://m1.tv/shedule/"),
    "M2.ua@SD": ("M2", "https://m2.tv/shedule/"),
}


def ukrainian_weekly_schedule(page_html: str) -> dict[int, list[tuple[object, str]]]:
    schedules: dict[int, list[tuple[object, str]]] = {}
    day_pattern = re.compile(
        r'<ul\b[^>]*\bid=["\']day_(monday|tuesday|wednesday|thursday|friday|saturday|sunday)["\'][^>]*>(.*?)</ul\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    item_pattern = re.compile(r"<li\b.*?</li\s*>", re.IGNORECASE | re.DOTALL)
    time_pattern = re.compile(
        r'<div\b[^>]*class=["\']time["\'][^>]*>\s*(\d{1,2}:\d{2})\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(
        r'<div\b[^>]*class=["\']title["\'][^>]*>.*?<span\b[^>]*>(.*?)</span\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    for day_name, day_html in day_pattern.findall(page_html):
        items: list[tuple[object, str]] = []
        for item_html in item_pattern.findall(day_html):
            time_match = time_pattern.search(item_html)
            title_match = title_pattern.search(item_html)
            if not time_match or not title_match:
                continue
            try:
                start_clock = datetime.strptime(
                    time_match.group(1), "%H:%M"
                ).time()
            except ValueError:
                continue
            title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1)))
            title = re.sub(r"\s+", " ", title).strip()
            if title:
                items.append((start_clock, title))
        if items:
            schedules[UKRAINIAN_WEEKDAYS[day_name.casefold()]] = sorted(
                items, key=lambda item: item[0]
            )
    return schedules


def fetch_ukrainian_music_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    targets = [
        (channel.tvg_id, channel_name, page_url)
        for channel in channels
        for channel_name, page_url in [
            UKRAINIAN_MUSIC_SCHEDULE_PAGES.get(channel.tvg_id, ("", ""))
        ]
        if channel_name and page_url
    ]
    if not targets:
        return None, {}

    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u Ukrainian music importer",
            "source-info-name": "M1 y M2 oficiales",
        },
    )
    errors: dict[str, str] = {}
    found_by_target = {target_id: 0 for target_id, _, _ in targets}
    now_ukraine = now.astimezone(UKRAINE_TIMEZONE)
    today = now_ukraine.date()

    for target_id, channel_name, page_url in targets:
        try:
            status, body, _ = fetch_bytes(
                page_url,
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
                timeout=60,
                limit=2_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            weekly = ukrainian_weekly_schedule(decode_web_text(body))
            if len(weekly) < 5:
                raise ValueError("la parrilla semanal no contiene suficientes dias")

            for offset in range(-1, 8):
                schedule_day = today + timedelta(days=offset)
                items = weekly.get(schedule_day.weekday(), [])
                if not items:
                    continue
                for index, (start_clock, title) in enumerate(items):
                    start = datetime.combine(
                        schedule_day, start_clock, tzinfo=UKRAINE_TIMEZONE
                    )
                    if index + 1 < len(items):
                        stop = datetime.combine(
                            schedule_day,
                            items[index + 1][0],
                            tzinfo=UKRAINE_TIMEZONE,
                        )
                        while stop <= start:
                            stop += timedelta(days=1)
                    else:
                        next_items = weekly.get((schedule_day.weekday() + 1) % 7, [])
                        if next_items:
                            stop = datetime.combine(
                                schedule_day + timedelta(days=1),
                                next_items[0][0],
                                tzinfo=UKRAINE_TIMEZONE,
                            )
                        else:
                            stop = start + timedelta(hours=6)
                    if stop <= start:
                        stop = start + timedelta(minutes=30)
                    if stop < now - timedelta(hours=6) or start > now + timedelta(days=5):
                        continue
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": target_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "uk"}).text = title
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                        f"Programacion semanal consultada en el sitio oficial de {channel_name}."
                    )
                    found_by_target[target_id] += 1
        except Exception as error:
            errors[target_id] = f"{type(error).__name__}: {error}"

    for target_id, count in found_by_target.items():
        if count == 0:
            errors[target_id] = "la fuente oficial no publico bloques utilizables"
    if not any(found_by_target.values()):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors


def tecnocentro_schedule_items(page_html: str) -> list[tuple[str, str, str]]:
    item_pattern = re.compile(
        r'<div class="schedule-item[^>]*>\s*'
        r'<div class="schedule-time">\s*'
        r'(?:<span[^>]*>)?([^<\s]+)(?:</span>)?\s*-\s*([^<]+?)\s*</div>\s*'
        r'<div class="schedule-title">\s*(.*?)\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )
    items: list[tuple[str, str, str]] = []
    for start_text, stop_text, raw_title in item_pattern.findall(page_html):
        title = html.unescape(re.sub(r"<[^>]+>", "", raw_title))
        title = re.sub(r"\s+", " ", title).strip()
        if title:
            items.append((start_text.strip(), stop_text.strip(), title))
    return items


def fetch_tecnocentro_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, dict[str, str]]:
    target_ids = {
        channel.tvg_id
        for channel in channels
        if channel.tvg_id and EPG_PROGRAMME_SOURCES.get(channel.tvg_id, ("", ""))[0]
        == "tecnocentro"
    }
    if not target_ids:
        return None, {}

    source_ids = {
        target_id: EPG_PROGRAMME_SOURCES[target_id][1]
        for target_id in target_ids
    }
    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u tecnocentro importer",
            "source-info-name": TECNOCENTRO_EPG_URL,
        },
    )
    errors: dict[str, str] = {}
    found_by_target = {target_id: 0 for target_id in target_ids}
    chile_today = now.astimezone(CHILE_TIMEZONE).date()
    seen: set[tuple[str, str, str, str]] = set()

    for offset in (0, 1):
        schedule_day = chile_today + timedelta(days=offset)
        for target_id, source_id in source_ids.items():
            url = (
                f"{TECNOCENTRO_EPG_URL}?view=schedule&channel={source_id}"
                f"&date={schedule_day.isoformat()}"
            )
            try:
                status, body, _ = fetch_bytes(
                    url,
                    {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/html,*/*"},
                    timeout=60,
                    limit=262_144,
                )
                if status != 200:
                    raise ValueError(f"HTTP {status}")
                items = tecnocentro_schedule_items(decode_web_text(body))
                parsed_items: list[tuple[object, object, str]] = []
                for start_text, stop_text, title in items:
                    try:
                        start_clock = datetime.strptime(start_text, "%H:%M").time()
                        stop_clock = datetime.strptime(stop_text, "%H:%M").time()
                    except ValueError:
                        continue
                    parsed_items.append((start_clock, stop_clock, title))
                if not parsed_items:
                    continue

                first_start_clock, first_stop_clock, _ = parsed_items[0]
                base_day = schedule_day
                if first_start_clock.hour >= 18 and first_stop_clock.hour <= 6:
                    base_day -= timedelta(days=1)
                previous_start: datetime | None = None
                for start_clock, stop_clock, title in parsed_items:
                    start = datetime.combine(
                        base_day, start_clock, tzinfo=CHILE_TIMEZONE
                    )
                    while previous_start is not None and start <= previous_start:
                        start += timedelta(days=1)
                    stop = datetime.combine(
                        start.date(), stop_clock, tzinfo=CHILE_TIMEZONE
                    )
                    while stop <= start:
                        stop += timedelta(days=1)
                    previous_start = start
                    is_requested_day = start.date() == schedule_day
                    is_current_previous_day = (
                        start.date() == schedule_day - timedelta(days=1) and stop > now
                    )
                    if not (is_requested_day or is_current_previous_day):
                        continue
                    if stop < now - timedelta(hours=6) or start > now + timedelta(days=5):
                        continue
                    key = (target_id, start.isoformat(), stop.isoformat(), title)
                    if key in seen:
                        continue
                    seen.add(key)
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": source_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "es"}).text = title
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = (
                        "Programacion diaria consultada en TecnoCentro."
                    )
                    found_by_target[target_id] += 1
            except Exception as error:
                errors[target_id] = f"{type(error).__name__}: {error}"

    for target_id, count in found_by_target.items():
        if count == 0:
            errors[target_id] = "TecnoCentro no publico bloques para este canal"

    if not any(found_by_target.values()):
        return None, errors
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), errors


def add_continuous_programmes(
    root: ET.Element,
    channel_id: str,
    channel_name: str,
    *,
    now: datetime,
    start_at: datetime | None = None,
    formatter: Callable[[datetime], str] = xmltv_format_chile,
) -> int:
    start = start_at or (
        now.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        - timedelta(days=1)
    )
    stop_limit = now.astimezone(timezone.utc) + timedelta(days=5)
    count = 0
    while start < stop_limit:
        stop = start + timedelta(hours=6)
        programme = ET.SubElement(
            root,
            "programme",
            {
                "start": formatter(start),
                "stop": formatter(stop),
                "channel": channel_id,
            },
        )
        title, description = CONTINUOUS_PROGRAMME_DETAILS.get(
            channel_name,
            (f"{channel_name} en vivo", "Programacion continua de la senal en vivo."),
        )
        ET.SubElement(programme, "title", {"lang": "es"}).text = title
        if description:
            ET.SubElement(programme, "desc", {"lang": "es"}).text = description
        count += 1
        start = stop
    return count


def build_epg(
    source_documents: dict[str, bytes],
    channels: list[Channel],
    red_bull_schedules: dict[str, list[dict]],
    *,
    now: datetime,
) -> tuple[bytes, dict]:
    expected_ids = {channel.tvg_id for channel in channels if channel.tvg_id}
    if len(expected_ids) != len(channels):
        raise ValueError("todos los canales necesitan un tvg-id unico")

    root = ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u updater",
            "source-info-name": (
                "EPGShare01, Zapping, TecnoCentro, fuentes oficiales y relay GitHub"
            ),
            "data-generated-at": now.astimezone(timezone.utc).isoformat(),
        },
    )
    channel_by_id = {channel.tvg_id: channel for channel in channels}
    guide_types: dict[str, str] = {}
    for channel in channels:
        element = ET.SubElement(root, "channel", {"id": channel.tvg_id})
        ET.SubElement(element, "display-name").text = channel.display_name or channel.name
        if channel.logo_url:
            ET.SubElement(element, "icon", {"src": channel.logo_url})

    source_roots: dict[str, ET.Element] = {}
    for source_name, source_xml in source_documents.items():
        source_root = ET.fromstring(source_xml)
        if source_root.tag != "tv":
            raise ValueError(f"la fuente EPG {source_name} no contiene una raiz <tv>")
        source_roots[source_name] = source_root

    programmes_by_target = {channel_id: 0 for channel_id in expected_ids}
    real_last_stop_by_target: dict[str, datetime] = {}
    source_lookup = {
        (source_name, source_id): target_id
        for target_id, (source_name, source_id) in EPG_PROGRAMME_SOURCES.items()
        if target_id in expected_ids
    }
    if ZAPPING_EPG_SOURCE in source_roots:
        zapping_target_ids = {
            programme.get("channel", "")
            for programme in source_roots[ZAPPING_EPG_SOURCE].findall("programme")
        }
        for target_id in sorted(zapping_target_ids & set(ZAPPING_EPG_CHANNELS)):
            for lookup_key, lookup_target in list(source_lookup.items()):
                if lookup_target == target_id:
                    source_lookup.pop(lookup_key, None)
            source_lookup[(ZAPPING_EPG_SOURCE, target_id)] = target_id
    if MEGA_OFFICIAL_EPG_SOURCE in source_roots and "0105" in expected_ids:
        source_lookup.pop(("cl", "Canal.Mega.(Chile).cl"), None)
        source_lookup[(MEGA_OFFICIAL_EPG_SOURCE, "0105")] = "0105"
    if TVN_OFFICIAL_EPG_SOURCE in source_roots and "0104" in expected_ids:
        source_lookup.pop(("cl", "Canal.TVN.(Chile).cl"), None)
        source_lookup[(TVN_OFFICIAL_EPG_SOURCE, "0104")] = "0104"
    if NHK_OFFICIAL_EPG_SOURCE in source_roots and "NHKWorldJapan.jp" in expected_ids:
        source_lookup.pop(("cl", "Canal.NHK.World.cl"), None)
        source_lookup[(NHK_OFFICIAL_EPG_SOURCE, "NHKWorldJapan.jp")] = (
            "NHKWorldJapan.jp"
        )
    if LA_RED_OFFICIAL_EPG_SOURCE in source_roots and "0102" in expected_ids:
        source_lookup.pop(("cl", "Canal.La.Red.(Chile).cl"), None)
        source_lookup.pop((ZAPPING_EPG_SOURCE, "0102"), None)
        source_lookup[(LA_RED_OFFICIAL_EPG_SOURCE, "0102")] = "0102"
    if (
        CANAL13_13C_OFFICIAL_EPG_SOURCE in source_roots
        and "13C.cl@SD" in expected_ids
    ):
        source_lookup.pop((ZAPPING_EPG_SOURCE, "13C.cl@SD"), None)
        source_lookup[(CANAL13_13C_OFFICIAL_EPG_SOURCE, "13C.cl@SD")] = (
            "13C.cl@SD"
        )
    for source_name, source_root in source_roots.items():
        seen_source_programmes: set[tuple[str, str, str, str]] = set()
        for programme in source_root.findall("programme"):
            target_id = source_lookup.get((source_name, programme.get("channel", "")))
            if target_id is None:
                continue
            if source_name == "pluto":
                # Pluto's public XML sometimes repeats the same card verbatim
                # at a boundary. Keep one copy so XMLTV remains non-overlapping.
                duplicate_key = (
                    programme.get("channel", ""),
                    programme.get("start", ""),
                    programme.get("stop", ""),
                    programme.findtext("title", ""),
                )
                if duplicate_key in seen_source_programmes:
                    continue
                seen_source_programmes.add(duplicate_key)
            copied = localize_xmltv_programme(programme)
            copied.set("channel", target_id)
            root.append(copied)
            programmes_by_target[target_id] += 1
            guide_types[target_id] = "parrilla real"
            try:
                stop = xmltv_datetime(copied.get("stop", ""))
            except ValueError:
                pass
            else:
                previous_stop = real_last_stop_by_target.get(target_id)
                if previous_stop is None or stop > previous_stop:
                    real_last_stop_by_target[target_id] = stop

    for red_bull_id, red_bull_cards in red_bull_schedules.items():
        if red_bull_id not in expected_ids:
            continue
        red_bull_last_stop: datetime | None = None
        for card in normalize_red_bull_schedule(red_bull_cards):
            start = datetime.fromisoformat(card["start_time"].replace("Z", "+00:00"))
            stop = datetime.fromisoformat(card["end_time"].replace("Z", "+00:00"))
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": red_bull_id,
                },
            )
            language = card.get("lang", "es")
            ET.SubElement(programme, "title", {"lang": language}).text = card[
                "title"
            ]
            subtitle = card.get("subheading")
            if subtitle:
                ET.SubElement(programme, "sub-title", {"lang": language}).text = (
                    subtitle
                )
            description = card.get("short_description") or card.get("long_description")
            if description:
                ET.SubElement(programme, "desc", {"lang": language}).text = description
            programmes_by_target[red_bull_id] += 1
            red_bull_last_stop = (
                stop
                if red_bull_last_stop is None or stop > red_bull_last_stop
                else red_bull_last_stop
            )
        if red_bull_last_stop is not None:
            real_last_stop_by_target[red_bull_id] = red_bull_last_stop
        if programmes_by_target[red_bull_id]:
            programmes_by_target[red_bull_id] += add_continuous_programmes(
                root,
                red_bull_id,
                channel_by_id[red_bull_id].name,
                now=now,
                start_at=red_bull_last_stop,
                formatter=xmltv_format_chile,
            )
            guide_types[red_bull_id] = "parrilla oficial Red Bull + continuidad"

    last_stop_by_channel: dict[str, datetime] = {}
    for programme in root.findall("programme"):
        channel_id = programme.get("channel", "")
        if channel_id not in expected_ids:
            continue
        stop = xmltv_datetime(programme.get("stop", ""))
        previous = last_stop_by_channel.get(channel_id)
        if previous is None or stop > previous:
            last_stop_by_channel[channel_id] = stop

    minimum_future = now + timedelta(hours=24)
    for channel_id, count in programmes_by_target.items():
        channel = channel_by_id[channel_id]
        if channel_id in NO_EPG_CHANNEL_IDS:
            guide_types[channel_id] = "sin guía"
            continue
        last_stop = last_stop_by_channel.get(channel_id)
        if count and last_stop is not None and last_stop >= minimum_future:
            continue
        added = add_continuous_programmes(
            root,
            channel_id,
            channel.name,
            now=now,
            start_at=last_stop if count and last_stop is not None else None,
        )
        programmes_by_target[channel_id] += added
        guide_types[channel_id] = (
            "parrilla real + continuidad" if count else "senal continua"
        )

    for channel in root.findall("channel"):
        channel.set("data-guide", guide_types.get(channel.get("id", ""), "senal continua"))

    generic_only = sorted(
        channel_id
        for channel_id in expected_ids
        if guide_types.get(channel_id) == "senal continua"
    )
    if generic_only:
        names = ", ".join(channel_by_id[channel_id].name for channel_id in generic_only)
        raise ValueError(
            "se rechazo una EPG generica para canales de produccion: " + names
        )

    real_stop_candidates = list(real_last_stop_by_target.values())
    if real_stop_candidates:
        next_refresh = min(real_stop_candidates) - EPG_REFRESH_LEAD
        root.set(
            "data-next-refresh-at",
            next_refresh.astimezone(timezone.utc).isoformat(),
        )

    ET.indent(root, space="  ")
    output = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    status = epg_status_from_xml(
        output,
        expected_ids,
        now=now,
        minimum_future=timedelta(hours=24),
        allow_empty_ids=NO_EPG_CHANNEL_IDS,
    )
    status["guide_types"] = guide_types
    status["real_last_stop_utc"] = {
        channel_id: stop.astimezone(timezone.utc).isoformat()
        for channel_id, stop in real_last_stop_by_target.items()
    }
    return output, status


def refresh_epg(channels: list[Channel], *, force: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    expected_ids = {channel.tvg_id for channel in channels if channel.tvg_id}
    existing_status = None
    if EPG_PATH.exists():
        try:
            existing_data = EPG_PATH.read_bytes()
            existing_root = ET.fromstring(existing_data)
            existing_channel_ids = {
                channel.get("id", "") for channel in existing_root.findall("channel")
            }
            if existing_channel_ids != expected_ids:
                raise ValueError("la guia publicada tiene canales fuera de la lista actual")
            existing_status = epg_status_from_xml(
                existing_data,
                expected_ids,
                now=now,
                minimum_future=timedelta(hours=24),
                allow_empty_ids=NO_EPG_CHANNEL_IDS,
            )
            generated_at = existing_status.get("generated_at")
            if generated_at and not force:
                age = now - datetime.fromisoformat(generated_at)
                if age < EPG_REFRESH_INTERVAL:
                    existing_status.update({"updated": False, "reused": True})
                    return existing_status
        except Exception:
            existing_status = None

    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/gzip,application/octet-stream,*/*",
    }
    source_documents: dict[str, bytes] = {}
    source_errors: dict[str, str] = {}
    for source_name, source_url in EPG_SOURCES.items():
        try:
            status, compressed, _ = fetch_bytes(
                source_url, headers, timeout=60, limit=10_485_760
            )
            if status != 200 or not compressed.startswith(b"\x1f\x8b"):
                raise ValueError(f"HTTP {status} sin contenido gzip")
            source_documents[source_name] = gzip.decompress(compressed)
        except Exception as error:
            source_errors[source_name] = str(error)

    tvn_data, tvn_error = fetch_tvn_official_epg(channels, now)
    if tvn_data:
        source_documents[TVN_OFFICIAL_EPG_SOURCE] = tvn_data
    if tvn_error:
        source_errors[TVN_OFFICIAL_EPG_SOURCE] = tvn_error

    la_red_data, la_red_error = fetch_la_red_official_epg(channels, now)
    if la_red_data:
        source_documents[LA_RED_OFFICIAL_EPG_SOURCE] = la_red_data
    if la_red_error:
        source_errors[LA_RED_OFFICIAL_EPG_SOURCE] = la_red_error

    mega_data, mega_error = fetch_mega_official_epg(channels, now)
    if mega_data:
        source_documents[MEGA_OFFICIAL_EPG_SOURCE] = mega_data
    if mega_error:
        source_errors[MEGA_OFFICIAL_EPG_SOURCE] = mega_error

    nhk_data, nhk_error = fetch_nhk_official_epg(channels, now)
    if nhk_data:
        source_documents[NHK_OFFICIAL_EPG_SOURCE] = nhk_data
    if nhk_error:
        source_errors[NHK_OFFICIAL_EPG_SOURCE] = nhk_error

    canal13_data, canal13_error = fetch_13c_official_epg(channels, now)
    if canal13_data:
        source_documents[CANAL13_13C_OFFICIAL_EPG_SOURCE] = canal13_data
    if canal13_error:
        source_errors[CANAL13_13C_OFFICIAL_EPG_SOURCE] = canal13_error

    red_bull_schedules, red_bull_source_names, red_bull_errors = (
        fetch_red_bull_schedules(expected_ids, now)
    )
    source_errors.update(red_bull_errors)

    blocking_source_errors = {
        source_name: error
        for source_name, error in source_errors.items()
        if source_name
        not in {
            LA_RED_OFFICIAL_EPG_SOURCE,
            MEGA_OFFICIAL_EPG_SOURCE,
            TVN_OFFICIAL_EPG_SOURCE,
            CANAL13_13C_OFFICIAL_EPG_SOURCE,
        }
    }
    if blocking_source_errors and existing_status is not None:
        existing_status.update(
            {
                "updated": False,
                "preserved": True,
                "warning": "se conservo la guia anterior por fallos de fuente",
                "source_errors": source_errors,
            }
        )
        return existing_status

    zapping_data, zapping_errors = fetch_zapping_epg(channels, now)
    source_errors.update(
        {
            f"{ZAPPING_EPG_SOURCE}:{target_id}": error
            for target_id, error in zapping_errors.items()
        }
    )
    if zapping_data:
        source_documents[ZAPPING_EPG_SOURCE] = zapping_data
    # Un fallo de Zapping es por canal y no debe abortar la actualizacion:
    # build_epg conserva EPGShare01/TecnoCentro como tercera opcion.

    tecnocentro_data, tecnocentro_errors = fetch_tecnocentro_epg(channels, now)
    if tecnocentro_data:
        source_documents["tecnocentro"] = tecnocentro_data
    source_errors.update(
        {f"tecnocentro:{target_id}": error for target_id, error in tecnocentro_errors.items()}
    )
    ukrainian_data, ukrainian_errors = fetch_ukrainian_music_epg(channels, now)
    if ukrainian_data:
        source_documents["ukrainian-official"] = ukrainian_data
    source_errors.update(
        {
            f"ukrainian-official:{target_id}": error
            for target_id, error in ukrainian_errors.items()
        }
    )
    if not source_documents:
        raise RuntimeError("ninguna fuente EPG respondio correctamente")

    output, epg_status = build_epg(
        source_documents, channels, red_bull_schedules, now=now
    )
    temporary = EPG_PATH.with_suffix(".xml.tmp")
    temporary.write_bytes(output)
    temporary.replace(EPG_PATH)
    epg_status.update(
        {
            "updated": True,
            "sources": list(source_documents) + sorted(red_bull_source_names),
            "source_errors": source_errors,
        }
    )
    return epg_status


def check_channel(
    channel: Channel, attempts: int = 2, *, allow_ci_geo_block: bool = False
) -> CheckResult:
    last_error = "respuesta desconocida"
    for attempt in range(attempts):
        try:
            status, body, final_url = fetch_channel_bytes(
                channel.url, request_headers(channel.name)
            )
            text = body.decode("utf-8", "replace").lstrip("\ufeff\r\n ")
            if status == 200 and text.startswith("#EXTM3U"):
                detail = "playlist HLS valida"
                if final_url != channel.url:
                    detail += " (con redireccion)"
                if channel.name in SEGMENT_CHECK_CHANNELS:
                    segment_ok, segment_detail = check_hls_first_segment(
                        channel.url,
                        request_headers(channel.name),
                        initial_body=body,
                        initial_final_url=final_url,
                    )
                    if not segment_ok:
                        if (
                            allow_ci_geo_block
                            and channel.name in CI_GEO_RESTRICTED_CHANNELS
                            and "segmento HTTP 403" in segment_detail
                        ):
                            return CheckResult(
                                channel.name,
                                channel.url,
                                True,
                                "reproduccion limitada fuera de Chile (segmento HTTP 403)",
                            )
                        last_error = segment_detail
                        if attempt + 1 < attempts:
                            time.sleep(1.5)
                            continue
                        return CheckResult(channel.name, channel.url, False, last_error)
                    detail += f"; {segment_detail}"
                return CheckResult(channel.name, channel.url, True, detail)
            last_error = f"HTTP {status}, contenido no reconocido"
        except urllib.error.HTTPError as error:
            geo_error_codes = {403}
            if channel.name in APP_HANDLED_CHANNELS:
                geo_error_codes.add(401)
            if (
                allow_ci_geo_block
                and channel.name in CI_GEO_RESTRICTED_CHANNELS
                and error.code in geo_error_codes
            ):
                detail = (
                    f"maestro reservado para la app; Actions no obtiene acceso "
                    f"(HTTP {error.code})"
                    if channel.name in APP_HANDLED_CHANNELS
                    else f"reproduccion limitada fuera de Chile (HTTP {error.code})"
                )
                return CheckResult(
                    channel.name,
                    channel.url,
                    True,
                    detail,
                )
            last_error = f"HTTP {error.code} {error.reason}"
        except Exception as error:  # Network and TLS failures need a compact report.
            if (
                allow_ci_geo_block
                and channel.name in APP_HANDLED_CHANNELS
                and "/live-stream-playlist/" in channel.url
                and isinstance(error, urllib.error.URLError)
            ):
                return CheckResult(
                    channel.name,
                    channel.url,
                    True,
                    "maestro conservado; Actions fuera de Chile no pudo probarlo",
                )
            last_error = f"{type(error).__name__}: {error}"
        if attempt + 1 < attempts:
            time.sleep(1.5)
    return CheckResult(channel.name, channel.url, False, last_error)


def check_hls_first_segment(
    url: str,
    headers: dict[str, str],
    *,
    initial_body: bytes | None = None,
    initial_final_url: str | None = None,
    depth: int = 0,
) -> tuple[bool, str]:
    """Confirm that an HLS master or media playlist delivers a live segment."""
    if depth > 3:
        return False, "playlist HLS con demasiados niveles"
    try:
        if initial_body is None:
            status, body, final_url = fetch_bytes(url, headers, limit=1_048_576)
        else:
            status, body, final_url = 200, initial_body, initial_final_url or url
        text = body.decode("utf-8", "replace").lstrip("\ufeff\r\n ")
        if status != 200 or not text.startswith("#EXTM3U"):
            return False, f"playlist HTTP {status}, contenido no reconocido"
        lines = [line.strip() for line in text.splitlines()]
        variants: list[tuple[int, int, str]] = []
        for index, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF:") or index + 1 >= len(lines):
                continue
            child = lines[index + 1]
            if not child or child.startswith("#"):
                continue
            resolution = hls_attribute(line, "RESOLUTION") or "0x0"
            width, height = (int(value) for value in resolution.split("x", 1))
            variants.append((height, width, urljoin(final_url, child)))
        if variants:
            _, _, child_url = max(variants)
            return check_hls_first_segment(child_url, headers, depth=depth + 1)
        segments = [line for line in lines if line and not line.startswith("#")]
        if not segments:
            return False, "playlist sin segmento multimedia"
        # El primer segmento de una playlist en vivo puede retirarse mientras
        # se comprueba. Probar también los más recientes evita falsos 404/502.
        candidates = list(dict.fromkeys([segments[0], *segments[-3:]]))
        last_detail = "segmento no disponible"
        for segment in candidates:
            segment_url = urljoin(final_url, segment)
            try:
                segment_status, segment_body, _ = fetch_bytes(
                    segment_url, headers, timeout=25, limit=64
                )
                if segment_status == 200 and segment_body:
                    return True, "segmento multimedia valido"
                last_detail = f"segmento HTTP {segment_status}"
            except urllib.error.HTTPError as error:
                last_detail = f"segmento HTTP {error.code} {error.reason}"
            except Exception as error:
                last_detail = f"segmento {type(error).__name__}: {error}"
        return False, last_detail
    except urllib.error.HTTPError as error:
        return False, f"segmento HTTP {error.code} {error.reason}"
    except Exception as error:
        return False, f"segmento {type(error).__name__}: {error}"


def check_logo(channel: Channel) -> LogoResult:
    if not channel.logo_url:
        if channel.group.startswith(TEST_GROUP_PREFIX):
            return LogoResult(
                channel.name,
                "",
                True,
                "entrada de prueba sin tvg-logo local; se omite sin marcar fallo",
            )
        return LogoResult(channel.name, "", False, "falta tvg-logo")
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "image/svg+xml,image/png,image/*;q=0.8,*/*;q=0.5",
    }
    try:
        local_path = None
        if channel.logo_url.startswith(LOCAL_LOGOS_PUBLIC_BASE):
            logo_name = Path(urlparse(channel.logo_url).path).name
            candidate_path = Path(__file__).with_name("logos") / logo_name
            if candidate_path.is_file():
                local_path = candidate_path
        if local_path is not None:
            status, body = 200, local_path.read_bytes()
            source_suffix = " (copia local)"
        else:
            status, body, _ = fetch_bytes(channel.logo_url, headers, limit=65_536)
            source_suffix = ""
        if status == 200 and body.startswith(b"\x89PNG\r\n\x1a\n"):
            if not png_has_transparency(body):
                return LogoResult(
                    channel.name,
                    channel.logo_url,
                    False,
                    f"PNG valido pero sin canal alfa transparente{source_suffix}",
                )
            return LogoResult(
                channel.name,
                channel.logo_url,
                True,
                f"PNG valido y transparente{source_suffix}",
            )
        if status == 200 and jpeg_is_valid(body):
            return LogoResult(
                channel.name,
                channel.logo_url,
                True,
                f"JPEG valido{source_suffix}",
            )
        if status == 200 and svg_is_valid(body):
            return LogoResult(
                channel.name,
                channel.logo_url,
                True,
                f"SVG valido y vectorial{source_suffix}",
            )
        return LogoResult(
            channel.name,
            channel.logo_url,
            False,
            f"HTTP {status}, no es PNG ni SVG valido",
        )
    except urllib.error.HTTPError as error:
        return LogoResult(channel.name, channel.logo_url, False, f"HTTP {error.code} {error.reason}")
    except Exception as error:
        return LogoResult(channel.name, channel.logo_url, False, f"{type(error).__name__}: {error}")


def png_has_transparency(body: bytes) -> bool:
    """Check the PNG color type or tRNS chunk without requiring Pillow."""
    if len(body) < 33 or not body.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    if body[12:16] != b"IHDR":
        return False
    color_type = body[25]
    if color_type in {4, 6}:
        return True
    if color_type != 3:
        return False
    offset = 8
    while offset + 12 <= len(body):
        length = int.from_bytes(body[offset : offset + 4], "big")
        chunk_type = body[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(body):
            break
        if chunk_type == b"tRNS":
            return True
        if chunk_type == b"IEND":
            break
        offset = end
    return False


def jpeg_is_valid(body: bytes) -> bool:
    return len(body) >= 3 and body[:3] == b"\xff\xd8\xff"


def svg_is_valid(body: bytes) -> bool:
    try:
        root = ET.fromstring(body)
    except (ET.ParseError, UnicodeDecodeError):
        return False
    return root.tag.rsplit("}", 1)[-1].lower() == "svg"


def verify_logos(channels: list[Channel]) -> list[LogoResult]:
    results: dict[str, LogoResult] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(channels))) as pool:
        futures = {pool.submit(check_logo, channel): channel for channel in channels}
        for future in as_completed(futures):
            result = future.result()
            results[result.channel] = result
            state = "OK" if result.ok else "FALLO"
            print(f"  [{state}] Logo {result.channel}: {result.detail}")
    return [results[channel.name] for channel in channels]


def extract_hls_urls(page_text: str) -> list[str]:
    matches = re.findall(
        r"https?:\\?/\\?/[^\s\"'<>]+?\.m3u8(?:\?[^\s\"'<>]*)?",
        page_text,
        flags=re.IGNORECASE,
    )
    urls: list[str] = []
    for match in matches:
        cleaned = html.unescape(match).replace("\\/", "/")
        cleaned = re.sub(r"\\+u0026", "&", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.rstrip("\\,);]")
        alternatives = [cleaned]
        if "#" in cleaned:
            alternatives.extend(
                part for part in cleaned.split("#") if part.startswith("http")
            )
        for alternative in alternatives:
            if alternative not in urls:
                urls.append(alternative)
    return urls


def discover_official_candidates(channel: Channel) -> list[str]:
    candidates: list[str] = []
    dynamic_factories = {
        "24 Horas": fresh_24horas_url,
    }
    factory = dynamic_factories.get(channel.name)
    if factory:
        try:
            candidates.append(factory())
        except Exception as error:
            print(f"  [AVISO] {channel.name}: no se pudo renovar el enlace oficial: {error}")
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    for page_url in OFFICIAL_STREAM_PAGES.get(channel.name, []):
        try:
            _, body, _ = fetch_bytes(page_url, headers, limit=2_097_152)
            for candidate in extract_hls_urls(body.decode("utf-8", "replace")):
                hint = OFFICIAL_CANDIDATE_HINTS.get(channel.name)
                if (hint is None or hint.search(candidate)) and candidate not in candidates:
                    candidates.append(candidate)
        except Exception as error:
            print(f"  [AVISO] {channel.name}: no se pudo leer {page_url}: {error}")
    # Solo despues de consultar las paginas oficiales se prueban los respaldos
    # conocidos. Pueden ser CDNs del proveedor o retransmisores comunitarios.
    candidates.extend(KNOWN_STREAM_FALLBACKS.get(channel.name, []))
    return [candidate for candidate in candidates if candidate != channel.url]


def repair_failed_channels(
    lines: list[str],
    channels: list[Channel],
    results: list[CheckResult],
    *,
    allow_ci_geo_block: bool,
) -> list[str]:
    channels_by_name = {channel.name: channel for channel in channels}
    repaired: list[str] = []
    for result in results:
        if result.ok:
            continue
        channel = channels_by_name[result.channel]
        if allow_ci_geo_block and channel.name in APP_HANDLED_CHANNELS:
            print(
                f"  [CONSERVADO] {channel.name}: se mantiene el maestro original; "
                "la autenticacion queda en la app"
            )
            continue
        print(f"Buscando reemplazo oficial para {channel.name}")
        for candidate_url in discover_official_candidates(channel):
            candidate = Channel(
                channel.name,
                candidate_url,
                channel.url_line,
                channel.info_line,
                channel.logo_url,
                channel.group,
            )
            candidate_result = check_channel(
                candidate, allow_ci_geo_block=allow_ci_geo_block
            )
            if candidate_result.ok:
                lines[channel.url_line] = candidate_url
                repaired.append(channel.name)
                print(f"  [REPARADO] {channel.name}: enlace alternativo verificado")
                break
        if channel.name not in repaired:
            print(f"  [SIN REEMPLAZO] {channel.name}: se conserva el enlace para revision manual")
    return repaired


def fresh_24horas_url() -> str:
    html = megamedia_page_html(TWENTYFOUR_LIVE_PAGE)
    stream_id_match = re.search(
        r'<a[^>]+class=["\'][^"\']*playertablink[^"\']*active[^"\']*["\']'
        r'[^>]+data-ms=["\']([a-zA-Z0-9]+)["\']',
        html,
        flags=re.IGNORECASE,
    )
    stream_id = stream_id_match.group(1) if stream_id_match else TWENTYFOUR_DEFAULT_ID
    return f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8"


def fresh_tvvoo_stream_urls(channel_name: str) -> list[str]:
    """Resolve current TvVoo HLS URLs for a channel without storing its token."""
    resolver_ids = TVVOO_STREAM_RESOLVER_IDS.get(channel_name)
    if not resolver_ids:
        raise ValueError(f"no hay resolver TvVoo para {channel_name}")
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json",
    }
    candidates: list[str] = []
    errors: list[str] = []
    for resolver_id in resolver_ids:
        endpoint = f"{TVVOO_STREAM_BASE_URL}/{resolver_id}.json"
        try:
            status, body, _ = fetch_bytes(endpoint, headers, timeout=30, limit=131_072)
            if status != 200:
                raise ValueError(f"HTTP {status}")
            payload = json.loads(body.decode("utf-8", "replace"))
            for stream in payload.get("streams", []):
                stream_url = str(stream.get("url", "")).strip()
                if not stream_url:
                    continue
                candidates.append(stream_url)
                parsed = urlparse(stream_url)
                # Algunos nodos HTTPS del proveedor estan entregando un
                # certificado vencido; el mismo JSON publica nodos HTTP que
                # siguen entregando el HLS. Se prueba HTTPS primero y HTTP
                # solo como compatibilidad del stream publico.
                if parsed.scheme.lower() == "https":
                    candidates.append(parsed._replace(scheme="http").geturl())
        except Exception as error:
            errors.append(f"{resolver_id}: {type(error).__name__}: {error}")
    unique = list(dict.fromkeys(candidates))
    if unique:
        return unique
    detail = "; ".join(errors) if errors else "respuesta sin streams"
    raise RuntimeError(f"TvVoo no entrego una URL para {channel_name}: {detail}")


def megamedia_page_html(page_url: str) -> str:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": page_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        _, body, _ = fetch_bytes(page_url, headers, limit=2_097_152)
    except urllib.error.URLError as error:
        reason = str(getattr(error, "reason", error)).lower()
        if "certificate verify failed" not in reason and "certificate has expired" not in reason:
            raise
        print(
            f"  {page_url}: certificado web vencido; usando excepcion TLS solo para "
            "leer su configuracion publica"
        )
        insecure_context = ssl.create_default_context()
        insecure_context.check_hostname = False
        insecure_context.verify_mode = ssl.CERT_NONE
        _, body, _ = fetch_bytes(
            page_url,
            headers,
            context=insecure_context,
            limit=2_097_152,
        )
    return body.decode("utf-8", "replace")


def refresh_dynamic_channel(
    lines: list[str],
    channel: Channel,
    fresh_url_factory: Callable[[], str | list[str]],
    *,
    running_in_ci: bool,
    always_refresh: bool = False,
) -> bool:
    current_result = check_channel(channel, allow_ci_geo_block=running_in_ci)
    state = "OK" if current_result.ok else "FALLO"
    print(f"  [{state}] {channel.name}: {current_result.detail}")
    use_dynamic_master = "/live-stream-gdai/" not in channel.url
    needs_refresh = (
        always_refresh
        or running_in_ci
        or not current_result.ok
        or not use_dynamic_master
    )
    if not needs_refresh:
        return False

    candidates: list[str] = []
    try:
        fresh_result = fresh_url_factory()
        if isinstance(fresh_result, str):
            candidates.append(fresh_result)
        else:
            candidates.extend(fresh_result)
    except Exception as error:
        print(f"  [AVISO] {channel.name}: no se pudo renovar el enlace oficial: {error}")
    candidates.extend(KNOWN_STREAM_FALLBACKS.get(channel.name, []))

    seen: set[str] = set()
    for candidate_url in candidates:
        if candidate_url == channel.url or candidate_url in seen:
            continue
        seen.add(candidate_url)
        candidate = Channel(
            channel.name,
            candidate_url,
            channel.url_line,
            channel.info_line,
            channel.logo_url,
            channel.group,
            channel.tvg_id,
        )
        candidate_result = check_channel(
            candidate, allow_ci_geo_block=running_in_ci
        )
        geo_blocked = (
            running_in_ci
            and candidate_url.startswith("https://mdstrm.com/live-stream-playlist/")
            and channel.name == "TVN"
            and not candidate_result.ok
            and any(f"HTTP {status}" in candidate_result.detail for status in (401, 403))
        )
        if candidate_result.ok or geo_blocked:
            lines[channel.url_line] = candidate_url
            if geo_blocked:
                print(
                    f"  [GEO] {channel.name}: maestro renovado; GitHub Actions no puede "
                    "reproducirlo fuera de Chile"
                )
            else:
                print(f"  [OK] {channel.name}: enlace renovado o respaldo verificado")
            return True
        print(f"  [AVISO] {channel.name}: candidato no usable: {candidate_result.detail}")

    if current_result.ok:
        print(f"  [AVISO] {channel.name}: se conserva el enlace actual")
    else:
        print(f"  [SIN RESPALDO] {channel.name}: se conserva el enlace fallido para revision")
    return False


def verify_all(channels: list[Channel], *, allow_ci_geo_block: bool = False) -> list[CheckResult]:
    results: dict[str, CheckResult] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(channels))) as pool:
        futures = {
            pool.submit(
                check_channel, channel, allow_ci_geo_block=allow_ci_geo_block
            ): channel
            for channel in channels
        }
        for future in as_completed(futures):
            result = future.result()
            results[result.channel] = result
            state = "OK" if result.ok else "FALLO"
            print(f"  [{state}] {result.channel}: {result.detail}")
    return [results[channel.name] for channel in channels]


def write_report(
    results: list[CheckResult],
    tvn_refreshed: bool,
    logo_results: list[LogoResult] | None = None,
    repaired_channels: list[str] | None = None,
    epg_status: dict | None = None,
    *,
    refreshed_channels: list[str] | None = None,
) -> None:
    logos = logo_results or []
    report = {
        "playlist": DEFAULT_PLAYLIST.name,
        "tvn_refreshed": tvn_refreshed,
        "refreshed_channels": refreshed_channels or [],
        "repaired_channels": repaired_channels or [],
        "all_ok": (
            all(result.ok for result in results)
            and all(result.ok for result in logos)
            and bool(epg_status and epg_status.get("ok"))
        ),
        "epg": epg_status or {},
        "channels": [asdict(result) for result in results],
        "logos": [asdict(result) for result in logos],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def verify_published_copy(
    url: str,
    path: Path,
    attempts: int = 4,
    *,
    expected_prefix: str = "#EXTM3U",
) -> bool:
    expected = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    separator = "&" if "?" in url else "?"
    for attempt in range(attempts):
        cache_busted = f"{url}{separator}verify={int(time.time())}-{attempt}"
        try:
            _, body, _ = fetch_bytes(
                cache_busted,
                {"User-Agent": PLAYER_USER_AGENT, "Cache-Control": "no-cache"},
                limit=10_485_760,
            )
            published = body.decode("utf-8-sig", "replace").replace("\r\n", "\n")
            if published == expected and published.startswith(expected_prefix):
                if expected_prefix == "#EXTM3U":
                    detail = f"{published.count('#EXTINF:')} canales"
                else:
                    detail = f"{published.count('<programme ')} programas"
                print(f"{path.name} publicado verificado: {detail} y contenido exacto")
                return True
            print(f"  [REINTENTO] El raw aun no coincide ({attempt + 1}/{attempts})")
        except Exception as error:
            print(f"  [REINTENTO] No se pudo leer el raw: {error}")
        if attempt + 1 < attempts:
            time.sleep(2.0)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--verify-published", metavar="URL")
    parser.add_argument("--verify-epg-published", metavar="URL")
    args = parser.parse_args()

    playlist = args.playlist.resolve()
    if args.verify_published:
        return 0 if verify_published_copy(args.verify_published, playlist) else 1
    if args.verify_epg_published:
        return (
            0
            if verify_published_copy(
                args.verify_epg_published, EPG_PATH, expected_prefix="<?xml"
            )
            else 1
        )

    lines = playlist.read_text(encoding="utf-8-sig").splitlines()
    epg_url_changed = ensure_playlist_epg_url(lines)
    if epg_url_changed:
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        if epg_url_changed:
            print("Cabecera M3U enlazada a la guia EPG publicada en GitHub")
    news_order_changed = pin_news_channel_order(lines)
    preferred_logo_changed = pin_preferred_logos(lines)
    if (
        news_order_changed
        or preferred_logo_changed
    ):
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("Cambios de lista y maestros originales guardados")
    channels = parse_channels(lines)
    if not channels:
        raise RuntimeError("la lista no contiene canales activos")

    print("Actualizando la guia de programacion de todos los canales")
    force_epg_refresh = os.environ.get("EPG_FORCE_REFRESH", "").lower() == "true"
    epg_status = refresh_epg(channels, force=force_epg_refresh)
    updated = "actualizada" if epg_status.get("updated") else "vigente"
    print(
        f"  [OK] EPG {updated}: {epg_status['channels']} canales y "
        f"{epg_status['programmes']} programas"
    )
    for channel in channels:
        guide_type = epg_status.get("guide_types", {}).get(channel.tvg_id, "sin datos")
        print(f"  [EPG] {channel.name}: {guide_type}")

    print(f"Revisando {len(channels)} canales de {playlist.name}")
    running_in_ci = os.environ.get("CI", "").lower() == "true"
    allow_geo_restricted = running_in_ci or (
        os.environ.get("M3U_ALLOW_GEO_RESTRICTED", "").lower() == "true"
    )
    refreshed_channels: list[str] = []
    refresh_changed = False
    dynamic_channels = {
        "24 Horas": (fresh_24horas_url, False),
        "Premier Sports 1": (
            lambda: fresh_tvvoo_stream_urls("Premier Sports 1"),
            True,
        ),
        "Premier Sports 2": (
            lambda: fresh_tvvoo_stream_urls("Premier Sports 2"),
            True,
        ),
    }
    for channel_name in TVVOO_STREAM_RESOLVER_IDS:
        dynamic_channels.setdefault(
            channel_name,
            (
                lambda channel_name=channel_name: fresh_tvvoo_stream_urls(
                    channel_name
                ),
                True,
            ),
        )
    for channel_name, (fresh_url_factory, always_refresh) in dynamic_channels.items():
        channel = next((item for item in channels if item.name == channel_name), None)
        if channel and refresh_dynamic_channel(
            lines,
            channel,
            fresh_url_factory,
            running_in_ci=allow_geo_restricted,
            always_refresh=always_refresh,
        ):
            refreshed_channels.append(channel_name)
            refresh_changed = True
    if refresh_changed:
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    tvn_refreshed = "TVN" in refreshed_channels

    print("Verificacion final de la lista completa")
    final_lines = playlist.read_text(encoding="utf-8-sig").splitlines()
    final_channels = parse_channels(final_lines)
    results = verify_all(final_channels, allow_ci_geo_block=allow_geo_restricted)
    repaired_channels = repair_failed_channels(
        final_lines,
        final_channels,
        results,
        allow_ci_geo_block=allow_geo_restricted,
    )
    if repaired_channels:
        playlist.write_text(
            "\n".join(final_lines) + "\n", encoding="utf-8", newline="\n"
        )
        final_lines = playlist.read_text(encoding="utf-8-sig").splitlines()
        final_channels = parse_channels(final_lines)
        print("Verificacion posterior a las reparaciones")
        results = verify_all(final_channels, allow_ci_geo_block=allow_geo_restricted)

    print("Verificacion de logos")
    logo_results = verify_logos(final_channels)
    write_report(
        results,
        tvn_refreshed,
        logo_results,
        repaired_channels,
        epg_status,
        refreshed_channels=refreshed_channels,
    )
    failed = [result.channel for result in results if not result.ok]
    failed_logos = [result.channel for result in logo_results if not result.ok]
    if failed or failed_logos:
        if failed:
            print("Canales con problemas: " + ", ".join(failed), file=sys.stderr)
        if failed_logos:
            print("Logos con problemas: " + ", ".join(failed_logos), file=sys.stderr)
        return 1
    print(f"Todos los canales funcionan ({len(results)}/{len(results)})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        REPORT_PATH.write_text(
            json.dumps(
                {"playlist": DEFAULT_PLAYLIST.name, "all_ok": False, "fatal_error": str(error)},
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
