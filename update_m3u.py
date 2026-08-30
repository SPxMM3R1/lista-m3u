#!/usr/bin/env python3
"""Verify the published playlist and refresh expiring live stream links."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import html
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_PLAYLIST = Path(__file__).with_name("m3u.m3u")
EXTERNAL_PLAYLIST = Path(__file__).with_name("m3u-externa.m3u")
# Alias oficiales de una sola letra para reproductores con límite de longitud.
# Son copias generadas de las salidas canónicas, no un acortador externo.
SHORT_DIRECT_PLAYLIST = Path(__file__).with_name("1.m3u")
SHORT_EXTERNAL_PLAYLIST = Path(__file__).with_name("2.m3u")
SHORT_PLAYLIST_ALIASES = (
    (DEFAULT_PLAYLIST, SHORT_DIRECT_PLAYLIST),
    (EXTERNAL_PLAYLIST, SHORT_EXTERNAL_PLAYLIST),
)
CHANNEL_CATALOG_PATH = Path(__file__).with_name("channel-catalog.m3u")
EPG_PATH = Path(__file__).with_name("epg.xml")
REPORT_PATH = Path(__file__).with_name("channel-status.json")
HEALTH_STATE_PATH = Path(__file__).with_name("channel-health-state.json")
RESOLVER_CATALOG_PATH = Path(__file__).with_name("resolver-catalog.json")
PUBLIC_RAW_BASE = "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main"
EPG_PUBLIC_URL = f"{PUBLIC_RAW_BASE}/epg.xml"
LOCAL_LOGOS_PUBLIC_BASE = f"{PUBLIC_RAW_BASE}/logos"
RESOLVER_SCHEMA_VERSION = 1
RESOLVER_CATALOG_VERSION = "2026.08.29.2"
ALLOWED_RESOLVER_ENGINES = {"tvn", "meganoticias", "tvvoo", "highfly"}
MAIN_PLAYLIST_RESOLVERS = frozenset({"direct", "tvn", "meganoticias"})
EXTERNAL_PLAYLIST_RESOLVERS = frozenset({"tvvoo", "highfly"})
# Estas dos senales dinamicas se publican expresamente en la lista principal;
# mantienen su resolutor para renovar la fuente justo antes de reproducir.
MAIN_PLAYLIST_CHANNEL_IDS = frozenset({"SkySportsF1.uk", "SkySportsTennis.uk"})
# Sondas directas solicitadas para probar en vivo fuentes publicas de Sky
# Sports. No son resolutores ni se consideran una fuente oficial: conservan
# su URL tal cual para que el usuario pueda comprobarlas manualmente. El
# actualizador las prueba y las reporta, pero no las retira de m3u.m3u por un
# fallo individual. Los demas enlaces directos siguen sujetos al filtro de
# salud normal.
DIRECT_PROBE_CHANNEL_IDS = frozenset({
    "SkySportsF1.uk@Direct",
    "SkySportF1.it@Direct",
    "SkySportsAction.uk@Direct",
    "SkySportsCricket.uk@Direct",
    "SkySportsFootball.ie@Direct",
    "SkySportsMainEvent.ie@Direct",
    "SkySportsNews.uk@Direct",
    "SkySportsNFL.uk@Direct",
    "SkySportAustria1.at@Direct",
    "SkySportBasket.it@Direct",
    "SkySportTopEvent.de@Direct",
})
DYNAMIC_RESOLVER_ENGINES = frozenset({"meganoticias", "tvvoo", "highfly"})
# Los enlaces resueltos de TvVoo/Highfly son efimeros o pueden cambiar de
# nodo. Esta ventana solo evita repetir una renovacion si se lanza otra corrida
# poco despues de una validacion correcta; no sustituye la renovacion normal de
# las ventanas de seis horas.
RESOLVER_VALIDATION_TTL = {
    "meganoticias": timedelta(minutes=20),
    "tvvoo": timedelta(minutes=30),
    "highfly": timedelta(minutes=30),
}
RESOLVER_ATTRIBUTE_NAMES = (
    "x-resolver",
    "x-resolver-endpoint",
    "x-resolver-ids",
    "x-resolver-id",
    "x-resolver-manifest",
    "x-resolver-refresh",
)
HIGHFLY_MANIFEST_URL = (
    "https://sports.highfly.dev/"
    "eyJvbmx5TGl2ZSI6dHJ1ZX0/manifest.json"
)
HIGHFLY_RESOLVER_CHANNELS = {
    "SkySportsF1.uk": "now-sky-sports-f1-free",
    "ESPN.us": "us-espn-hd",
    "SkySportsPremierLeague.uk": "now-sky-sports-premier-league",
    "SkySport1.nz": "nz-sky-sport-1",
    "SkySportsTennis.uk": "now-sky-sports-tennis",
}

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
    "DAZNFastPlus.de@TvVoo",
    # Canales recuperados con HLS verificable, pero sin una fuente XMLTV que
    # identifique exactamente la senal. Se publican sin inventar continuidad.
    "1763",
    "ReutersTV.us",
    "Eurosport2.uk@TvVoo",
    "DAZNLigue1Live1.fr@TvVoo",
    "DAZNLigue1Live2.fr@TvVoo",
    "DAZNLigue1Live3.fr@TvVoo",
    "DAZNLigue1Live4.fr@TvVoo",
    "DAZN6.pt@TvVoo",
    # DAZN 1 Francia ahora usa la parrilla oficial publica de Pickx.
    # EPGShare conserva la identidad MCM.fr, pero actualmente no publica
    # bloques vigentes para la señal. No se inventa continuidad.
    "MCM.fr@TvVoo",
}
# Estas señales nuevas se publican como pruebas por región. La fuente no
# entregó una asociación XMLTV exacta y no se inventa una parrilla genérica.
NO_EPG_CHANNEL_IDS.update({
    "Vavoo.uk.BBCTWO@TvVoo",
    "Vavoo.uk.BBCFOUR@TvVoo",
    "Vavoo.uk.BBCWORLDNEWS@TvVoo",
    "Vavoo.uk.SKYSPORTSF1@TvVoo",
    "Vavoo.uk.TNTSPORTS2@TvVoo",
    "Vavoo.uk.4MUSIC@TvVoo",
    "Vavoo.it.BLOOMBERGTV@TvVoo",
    "Vavoo.it.EUROSPORT1@TvVoo",
    "Vavoo.it.SKYSPORTF1@TvVoo",
    "Vavoo.it.SKYSPORTTENNIS@TvVoo",
    "Vavoo.fr.MEZZOLIVE@TvVoo",
    "Vavoo.fr.STINGRAYCLASSICA@TvVoo",
    "Vavoo.fr.TRACEAFRICA@TvVoo",
    "Vavoo.fr.RMCSPORT3@TvVoo",
    "Vavoo.de.RTDE@TvVoo",
    "Vavoo.de.XITE@TvVoo",
    "Vavoo.pt.SPORTTV3@TvVoo",
    "Vavoo.pt.ELEVENSPORT3@TvVoo",
    "Vavoo.pt.EUROSPORT1@TvVoo",
    "Vavoo.pt.MTVPORTUGAL@TvVoo",
    "Vavoo.pt.STINGRAYICONCERTS@TvVoo",
    "Vavoo.es.ESPN2@TvVoo",
    "Vavoo.es.DAZN4@TvVoo",
    "Vavoo.es.EUROSPORT1@TvVoo",
    "Vavoo.pl.BBCEARTH@TvVoo",
    "Vavoo.pl.CNN@TvVoo",
    "Vavoo.pl.EUROSPORT3@TvVoo",
    "Vavoo.nl.ESPN1@TvVoo",
    "Vavoo.nl.FOXSPORTS1@TvVoo",
    "Vavoo.nl.XITEROCK@TvVoo",
    "Vavoo.nl.STINGRAYDJAZZ@TvVoo",
    "Vavoo.tr.EUROSPORT1@TvVoo",
    "Vavoo.tr.TRTWORLD@TvVoo",
    "Vavoo.tr.BEINSPORTS1@TvVoo",
    "Vavoo.tr.NBATV@TvVoo",
    "Vavoo.bk.ARENASPORT1@TvVoo",
    "Vavoo.bk.EUROSPORT1@TvVoo",
    "Vavoo.ru.RTDOCUMENTARY@TvVoo",
    "Vavoo.ro.DIGISPORT1@TvVoo",
    "Vavoo.bg.MAXSPORT1@TvVoo",
    "Vavoo.bg.STINGRAYICONCERTS@TvVoo",
    "Vavoo.al.SUPERSPORT1@TvVoo",
    "Vavoo.ar.BEINSPORTS1@TvVoo",
})
# Estas señales sí tienen fuentes de programación preferidas, pero pueden
# quedar temporalmente sin bloques. En ese caso se publica "sin guía" en vez
# de inventar continuidad o bloquear toda la actualización. Se vuelven a
# consultar normalmente en cada ejecución.
OPTIONAL_EPG_CHANNEL_IDS = {
    "1437",  # TVN3: Zapping/TecnoCentro cuando entregan bloques exactos.
}
NHK_MASTER_URL = "https://masterpl.hls.nhkworld.jp/hls/w/live/smarttv.m3u8"
# EPGShare01 no entregó una parrilla actual para estas pruebas; se mantienen
# sin guía en vez de rellenarlas con continuidad genérica.
NO_EPG_CHANNEL_IDS.difference_update({
    "Vavoo.uk.BBCTWO@TvVoo",
    "Vavoo.uk.BBCFOUR@TvVoo",
    "Vavoo.uk.TNTSPORTS2@TvVoo",
    "Vavoo.it.BLOOMBERGTV@TvVoo",
    "Vavoo.it.EUROSPORT1@TvVoo",
    "Vavoo.it.SKYSPORTF1@TvVoo",
    "Vavoo.it.SKYSPORTTENNIS@TvVoo",
    "Vavoo.it.SKYSPORTGOLF@TvVoo",
    "Vavoo.fr.MEZZOLIVE@TvVoo",
    "Vavoo.fr.RMCSPORT3@TvVoo",
    "Vavoo.pt.SPORTTV3@TvVoo",
    "Vavoo.pt.ELEVENSPORT3@TvVoo",
    "Vavoo.pt.EUROSPORT1@TvVoo",
    "Vavoo.pt.MTVPORTUGAL@TvVoo",
    "Vavoo.pt.STINGRAYICONCERTS@TvVoo",
    "Vavoo.es.DAZN4@TvVoo",
    "Vavoo.es.EUROSPORT1@TvVoo",
    "Vavoo.pl.BBCEARTH@TvVoo",
    "Vavoo.pl.CNN@TvVoo",
    "Vavoo.pl.MTVPOLSKA@TvVoo",
    "Vavoo.nl.ESPN1@TvVoo",
    "Vavoo.nl.STINGRAYDJAZZ@TvVoo",
    "Vavoo.tr.EUROSPORT1@TvVoo",
})
EPG_ALLOWED_EMPTY_IDS = NO_EPG_CHANNEL_IDS | OPTIONAL_EPG_CHANNEL_IDS
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
    "it1": "https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz",
    # PlutoTV es la fuente de parrilla real para los canales lineales Pluto
    # usados por MTV. No se generan bloques de continuidad para esos IDs.
    "pluto": "https://i.mjh.nz/PlutoTV/all.xml.gz",
}
CANAL13_MAIN_EPG_SOURCE = "canal13-abierto-oficial"
CANAL13_MAIN_EPG_URL = (
    "https://www.13.cl/sites/default/files/tools/epg-canal13.json"
)
CANAL13_13GO_EPG_SOURCE = "canal13-13go-oficial"
CANAL13_13GO_EPG_URLS = {
    "13Cultura.cl@DPS": "https://cdn.rudo.video/assets/canal-13/playlists/13cultura/epg.json",
    "13Kids.cl": "https://cdn.rudo.video/assets/canal-13/playlists/13kids/epg.json",
}
SKY_OFFICIAL_EPG_SOURCE = "sky-oficial"
SKY_OFFICIAL_EPG_SCHEDULE_URL = "https://awk.epgsky.com/hawk/linear/schedule"
SKY_OFFICIAL_EPG_CHANNELS = {
    "SkySportsMix.uk@TvVoo": "4091",
    "SkySportsNews.uk@TvVoo": "1340",
}
AUTENTIC_HISTORY_EPG_SOURCE = "autentic-history-oficial"
AUTENTIC_HISTORY_PAGE = "https://watch.whaletvplus.com/"
AUTENTIC_HISTORY_CHANNEL_ID = "931186243466302968"
PICKX_EPG_SOURCE = "pickx-dazn-oficial"
PICKX_EPG_PAGE = "https://www.pickx.be/nl/televisie/tv-gids"
PICKX_EPG_API_BASE = "https://px-epg.azureedge.net/airings"
PICKX_EPG_CHANNELS = {}
EPG_PROGRAMME_SOURCES = {
    "0104": ("cl", "Canal.TVN.(Chile).cl"),
    "0105": ("cl", "Canal.Mega.(Chile).cl"),
    "0106": ("cl", "Canal.Chilevisi\u00f3n.(CHV).cl"),
    "0107": ("cl", "Canal.13.de.Chile.cl"),
    "0201": ("cl", "Canal.24.Horas.(Chile).cl"),
    "DW.de": ("es", "Deutsche.Welle.es"),
    "France24.fr": ("fr", "France.24.Espanol.fr"),
    "EuronewsSpanish.fr": ("es", "Euronews.es"),
    "AlJazeera.qa": ("es", "Al.Jazeera.English.es"),
    "TVChile.cl": ("cl", "TV.Chile.cl"),
    "ArirangTV.kr": ("pl", "Arirang.TV.pl"),
    "XITEHits.nl@Germany": ("plex1", "plex.tv.XITE.Hits.plex"),
    "DWEnglish.de": ("lv", "Deutsche.Welle.English.HD.lv"),
    "France24.fr@English": ("fr", "France.24.Anglais.fr"),
    "ESPN.us": ("us2", "ESPN.HD.us2"),
    "RewindTV.cl@SD": ("us2", "Rewind.TV.us2"),
    "TyCSports.ar": ("ar1", "Canal.TyC.Sports.ar"),
    "SkySport1.nz": ("nz1", "Sky.Sport.1.nz"),
    "SkySportsF1.uk": ("uk1", "SkySp.F1.HD.uk"),
    "SkySportsPremierLeague.uk": ("uk1", "SkySp.PL.HD.uk"),
    "SkySportsTennis.uk": ("uk1", "SkySp.Tennis.HD.uk"),
    "SkySportsMix.uk@TvVoo": (SKY_OFFICIAL_EPG_SOURCE, "4091"),
    "SkySportsNews.uk@TvVoo": (SKY_OFFICIAL_EPG_SOURCE, "1340"),
    "PremierSports1.ie": ("uk1", "Premier.Sports.1.HD.uk"),
    "PremierSports2.ie": ("uk1", "Premier.Sports.2.HD.uk"),
    "RealWild.us": ("plex1", "plex.tv.Real.Wild.plex"),
    "XITENuevoLatino.us": ("plex1", "plex.tv.XITE.Nuevo.Latino.plex"),
    "XITESiempreLatino.us": ("plex1", "plex.tv.XITE.Siempre.Latino.plex"),
    "MTVClassic.us": ("pluto", "66a01dcb8561260008b0a41d"),
    "MTVBiggestPop.us": ("pluto", "6047fabfce6e8e00070bcc9f"),
    "MTVSpankinNew.us": ("pluto", "6541010f770cf1000866be98"),
    "MTVFlowLatino.us": ("pluto", "62b218fc511d4b00070ddc0c"),
    "SkySportsMainEvent.uk@TvVoo": ("uk1", "SkySpMainEvHD.uk"),
    "SkySportsArena.uk@TvVoo": ("uk1", "SkySp+.uk"),
    "TNTSports3.uk@TvVoo": ("uk1", "TNT.Sports.3.HD.uk"),
    "CNN.us@TvVoo": ("uk1", "CNN.HD.uk"),
    "Eurosport1.fr@TvVoo": ("fr", "Eurosport.1.fr"),
    "MTVHits.fr@TvVoo": ("nz1", "MTV.Hits.nz"),
    "M6Music.fr@TvVoo": ("fr", "M6.Music.fr"),
    "TraceUrban.fr@TvVoo": ("fr", "Trace.Urban.fr"),
    "SportTV1.pt@TvVoo": ("pt1", "SPORT.TV1.HD.pt"),
    "SportTV2.pt@TvVoo": ("pt1", "SPORT.TV2.HD.pt"),
    "SkySportsFootball.uk@TvVoo": ("uk1", "Sky.Sports.Football.HD.uk"),
    "SkySportsNFL.uk@TvVoo": ("uk1", "Sky.Sports.NFL.uk"),
    "Eurosport2.es@TvVoo": ("es", "Eurosport.2.es"),
    "DAZN2.es@TvVoo": ("es", "DAZN.2.es"),
    "Eurosport2.de@TvVoo": ("de", "Eurosport.2.de"),
    "DAZN3.es@TvVoo": ("es", "DAZN.3.es"),
    "DAZNLaliga1.es@TvVoo": ("es", "DAZN.LaLiga.es"),
    "DAZNLaliga2.es@TvVoo": ("es", "DAZN.LaLiga.2.es"),
    "DAZN1.pt@TvVoo": ("pt1", "DAZN.1.pt"),
    "DAZN2.pt@TvVoo": ("pt1", "DAZN.2.pt"),
    "DAZN3.pt@TvVoo": ("pt1", "DAZN.3.pt"),
    "DAZN4.pt@TvVoo": ("pt1", "DAZN.4.pt"),
    "DAZN5.pt@TvVoo": ("pt1", "DAZN.5.pt"),
    "DAZN1.it@TvVoo": ("it1", "DAZN.1.it.it"),
    "Eurosport2.it@TvVoo": ("it1", "Eurosport.2.Italia.it"),
    "SkySport24.it@TvVoo": ("it1", "Sky.Sport.24.it"),
    "SkySportCalcio.it@TvVoo": ("it1", "Sky.Sport.Calcio.it"),
    "SkySportMax.it@TvVoo": ("it1", "Sky.Sport.Max.it"),
    "SkySportMotoGP.it@TvVoo": ("it1", "Sky.Sport.MotoGP.it"),
    "SkySportNBA.it@TvVoo": ("it1", "Sky.Sport.NBA.it"),
    "SkySportUno.it@TvVoo": ("it1", "Sky.Sport.Uno.it"),
    "TNTSports1.uk@TvVoo": ("uk1", "TNT.Sports.1.HD.uk"),
    "NRJHits.fr@TvVoo": ("fr", "NRJ.Hits.fr"),
    "MCM.fr@TvVoo": ("fr", "MCM.fr"),
    "DAZNF1.es@TvVoo": ("es", "DAZN.F1.es"),
    "SportTV4.pt@TvVoo": ("pt1", "SPORT.TV4.HD.pt"),
    "SportTV5.pt@TvVoo": ("pt1", "SPORT.TV5.HD.pt"),
    "SkySportF1.de@TvVoo": ("de", "Sky.Sport.F1.de"),
    "SkySportGolf.de@TvVoo": ("de", "Sky.Sport.Golf.de"),
    "SkySportTennis.de@TvVoo": ("de", "Sky.Sport.Tennis.de"),
    "SkySportPremierLeague.de@TvVoo": (
        "de",
        "Sky.Sport.Premier.League.de",
    ),
    "Eurosport1.de@TvVoo": ("de", "Eurosport.1.de"),
    "13Cultura.cl@DPS": (CANAL13_13GO_EPG_SOURCE, "13cultura"),
    "13Kids.cl": (CANAL13_13GO_EPG_SOURCE, "13kids"),
    "AutenticHistory.de": (
        AUTENTIC_HISTORY_EPG_SOURCE,
        AUTENTIC_HISTORY_CHANNEL_ID,
    ),
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

# EPGShare01 entrega parrilla real para estas señales nuevas. Se asocia por
# el ID exacto de la fuente y no por coincidencia amplia del nombre visible.
EPG_PROGRAMME_SOURCES.update({
    "Vavoo.uk.BBCTWO@TvVoo": ("uk1", "BBC.Two.HD.uk"),
    "Vavoo.uk.BBCFOUR@TvVoo": ("uk1", "BBC.Four.HD.uk"),
    "Vavoo.uk.TNTSPORTS2@TvVoo": ("uk1", "TNT.Sports.2.HD.uk"),
    "Vavoo.it.BLOOMBERGTV@TvVoo": ("it1", "Bloomberg.it"),
    "Vavoo.it.EUROSPORT1@TvVoo": ("it1", "Eurosport.Italia.it"),
    "Vavoo.it.SKYSPORTF1@TvVoo": ("it1", "Sky.Sport.F1.it"),
    "Vavoo.it.SKYSPORTTENNIS@TvVoo": ("it1", "Sky.Sport.Tennis.it"),
    "Vavoo.de.SKYSPORT1@TvVoo": ("de", "Sky.Sport.1.de"),
    "Vavoo.fr.MEZZOLIVE@TvVoo": ("fr", "Mezzo.Live.HD.fr"),
    "Vavoo.fr.RMCSPORT3@TvVoo": ("fr", "RMC.Sport.Live.3.fr"),
    "Vavoo.pt.SPORTTV3@TvVoo": ("pt1", "SPORT.TV3.HD.pt"),
    "Vavoo.pt.ELEVENSPORT3@TvVoo": ("pl", "Eleven.Sports.3.HD.pl"),
    "Vavoo.pt.EUROSPORT1@TvVoo": ("pt1", "Eurosport.1.HD.pt"),
    "Vavoo.pt.MTVPORTUGAL@TvVoo": ("pt1", "MTV.Portugal.HD.pt"),
    "Vavoo.pt.STINGRAYICONCERTS@TvVoo": ("pt1", "Stingray.iConcerts.HD.pt"),
    "Vavoo.es.DAZN4@TvVoo": ("es", "DAZN.4.es"),
    "Vavoo.es.EUROSPORT1@TvVoo": ("es", "Eurosport.1.es"),
    "Vavoo.pl.BBCEARTH@TvVoo": ("pl", "BBC.Earth.HD.pl"),
    "Vavoo.pl.CNN@TvVoo": ("pl", "CNN.pl"),
    "Vavoo.nl.ESPN1@TvVoo": ("nl", "ESPN.nl"),
    "Vavoo.nl.STINGRAYDJAZZ@TvVoo": ("nl", "Stingray.DJAZZ.nl"),
    "Vavoo.tr.EUROSPORT1@TvVoo": ("tr1", "EUROSPORT.1.HD.tr"),
})
# Zapping publica una guia HTML con marcas Unix absolutas para el programa
# actual, hoy y manana. Se usa solo para senales chilenas donde la fuente
# agregada estaba desplazada o no entregaba una parrilla util. TVN, Mega,
# Canal 13 y La Red conservan sus adaptadores oficiales especificos; T13 usa
# Zapping y TecnoCentro porque no hay una parrilla oficial diaria de esa senal.
ZAPPING_EPG_SOURCE = "zapping-guia-publica"
ZAPPING_EPG_BASE_URL = "https://guia.zappingtv.com"
ZAPPING_NOWPLAYING_URL = "https://charly.zappingtv.com/v3/webplayer/nowplaying"
# `charly` rechaza algunos rangos de GitHub antes de llegar a la aplicacion.
# Estos frontales regionales publicos sirven el mismo API. curl --connect-to
# cambia solo el destino TCP: conserva la URL, Host y SNI de `charly`, por lo
# que TLS sigue validandose normalmente y no se publica ningun token.
ZAPPING_NOWPLAYING_CONNECT_HOSTS = (
    "br-apig.zappingtv.com",
    "ec-apig.zappingtv.com",
)
ZAPPING_EPG_CHANNELS = {
    "0104": "tvn",
    "0105": "mega",
    "0106": "chv",
    "0107": "canal13",
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
# La guia se actualiza junto con la validacion de canales cada 6 horas. Se
# conserva la reutilizacion de una guia valida si una ejecucion falla.
# El coordinador y el cron tienen cuatro ventanas diarias; tres horas es solo
# el margen informativo para una guia que termina pronto, no una quinta ventana.
EPG_REFRESH_INTERVAL = timedelta(hours=6)
HEALTH_FAILURE_THRESHOLD = 1
PUBLISHED_EPG_FALLBACK_SOURCE = "epg-publicada-conservada"
# El coordinador puede adelantar la siguiente ejecucion cuando una fuente real
# termina antes de las 6 horas. Los bloques de continuidad no cuentan para
# este calculo: solo sirven para que la guia no quede vacia mientras llega el
# siguiente refresco.
# Las fuentes opcionales no se completan con continuidad generica.
EPG_REFRESH_LEAD = timedelta(hours=3)
TVN_PROGRAMMING_PAGE = "https://www.tvn.cl/programacion"
TVN_PROGRAMMING_BASE_URL = "https://estaticos.tvn.cl/epg/tvn"
TVN_OFFICIAL_EPG_SOURCE = "tvn-oficial"
TVN3_OFFICIAL_PAGE = "https://www.tvn.cl/tvn3"
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
MEGANOTICIAS_DEFAULT_STREAM_ID = "561430ae330428c223687e1e"
MEGANOTICIAS_OFFICIAL_MASTER_URL = (
    "https://mdstrm.com/live-stream-playlist/"
    f"{MEGANOTICIAS_DEFAULT_STREAM_ID}.m3u8"
)
CANAL13_13C_PROGRAMMING_PAGE = "https://www.13.cl/c/programacion"
CANAL13_13C_OFFICIAL_EPG_SOURCE = "canal13-13c-oficial"
TVVOO_STREAM_BASE_URL = "https://tvvoo.hayd.uk/stream/tv"
# El relay publico de Highfly puede responder con un certificado vencido aun
# cuando el mismo HLS entrega playlist y segmentos. La excepcion queda
# limitada a este host y solo se activa ante el error explicito de expiracion.
EXPIRED_CERT_FALLBACK_HOSTS = {"leaf.highfly.dev", "sports.highfly.dev"}
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
    # TvVoo devuelve la senal como ARENA; la EPG UK1 la identifica como Sky+.
    "Sky Sports Arena": (
        "vavoo_SKY%20SPORTS%20ARENA%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20ARENA%20HD%7Cgroup%3Auk",
    ),
    "TNT Sports 3": (
        "vavoo_TNT%20SPORTS%203%7Cgroup%3Auk",
        "vavoo_TNT%20SPORTS%203%20HD%7Cgroup%3Auk",
    ),
    "CNN": ("vavoo_CNN%7Cgroup%3Auk",),
    "Eurosport 1": (
        "vavoo_EUROSPORT%201%7Cgroup%3Afr",
        "vavoo_EUROSPORT%201%20FHD%7Cgroup%3Afr",
        "vavoo_EUROSPORT%201%20HD%7Cgroup%3Afr",
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
    "DAZN FAST+": ("vavoo_DAZN%20FAST%2B%7Cgroup%3Ade",),
    "Sport TV 1": (
        "vavoo_SPORT%20TV%201%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%201%20HD%7Cgroup%3Apt",
    ),
    "Sport TV 2": (
        "vavoo_SPORT%20TV%202%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%202%20HD%7Cgroup%3Apt",
    ),
    "Sky Sports Football": (
        "vavoo_SKY%20SPORTS%20FOOTBALL%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20FOOTBALL%20HD%7Cgroup%3Auk",
    ),
    "Sky Sports NFL": (
        "vavoo_SKY%20SPORTS%20NFL%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20NFL%20HD%7Cgroup%3Auk",
    ),
    "Sky Sports Mix": (
        "vavoo_SKY%20SPORTS%20MIX%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20MIX%20FHD%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20MIX%20HD%7Cgroup%3Auk",
    ),
    "Sky Sports News": (
        "vavoo_SKY%20SPORTS%20NEWS%7Cgroup%3Auk",
        "vavoo_SKY%20SPORTS%20NEWS%20HD%7Cgroup%3Auk",
    ),
    "Eurosport 2 UK": (
        "vavoo_EUROSPORT%202%7Cgroup%3Auk",
        "vavoo_EUROSPORT%202%20HD%7Cgroup%3Auk",
    ),
    "Eurosport 2 España": (
        "vavoo_EUROSPORT%202%7Cgroup%3Aes",
        "vavoo_EUROSPORT%202%20HD%7Cgroup%3Aes",
        "vavoo_EUROSPORT%202%20FHD%7Cgroup%3Aes",
    ),
    "DAZN Ligue 1 Live 1": (
        "vavoo_DAZN%20LIGUE%201%20LIVE%201%20FHD%7Cgroup%3Afr",
    ),
    "DAZN Ligue 1 Live 2": (
        "vavoo_DAZN%20LIGUE%201%20LIVE%202%20HD%7Cgroup%3Afr",
    ),
    "DAZN Ligue 1 Live 3": (
        "vavoo_DAZN%20LIGUE%201%20LIVE%203%20HD%7Cgroup%3Afr",
    ),
    "DAZN Ligue 1 Live 4": (
        "vavoo_DAZN%20LIGUE%201%20LIVE%204%20HD%7Cgroup%3Afr",
    ),
    "Eurosport 2 Germany": (
        "vavoo_EUROSPORT%202%7Cgroup%3Ade",
        "vavoo_EUROSPORT%202%20FHD%7Cgroup%3Ade",
        "vavoo_EUROSPORT%202%20HD%7Cgroup%3Ade",
    ),
    "DAZN 3 España": ("vavoo_DAZN%203%7Cgroup%3Aes",),
    "DAZN 2 España": (
        "vavoo_DAZN%202%7Cgroup%3Aes",
        "vavoo_DAZN%202%20HD%7Cgroup%3Aes",
        "vavoo_DAZN%202%20FHD%7Cgroup%3Aes",
    ),
    "DAZN LaLiga 1": ("vavoo_DAZN%20LALIGA%201%7Cgroup%3Aes",),
    "DAZN LaLiga 2": ("vavoo_DAZN%20LALIGA%202%7Cgroup%3Aes",),
    "DAZN 1 Portugal": ("vavoo_DAZN%201%7Cgroup%3Apt",),
    "DAZN 2 Portugal": ("vavoo_DAZN%202%7Cgroup%3Apt",),
    "DAZN 3 Portugal": ("vavoo_DAZN%203%7Cgroup%3Apt",),
    "DAZN 4 Portugal": ("vavoo_DAZN%204%7Cgroup%3Apt",),
    "DAZN 5 Portugal": ("vavoo_DAZN%205%7Cgroup%3Apt",),
    "DAZN 6 Portugal": ("vavoo_DAZN%206%7Cgroup%3Apt",),
    "DAZN 1 Italia": ("vavoo_DAZN%201%7Cgroup%3Ait",),
    "Eurosport 2 Italia": ("vavoo_EUROSPORT%202%7Cgroup%3Ait",),
    "Sky Sport 24 Italia": ("vavoo_SKY%20SPORT%2024%7Cgroup%3Ait",),
    "Sky Sport Calcio Italia": (
        "vavoo_SKY%20SPORT%20CALCIO%7Cgroup%3Ait",
    ),
    "Sky Sport Max Italia": ("vavoo_SKY%20SPORT%20MAX%7Cgroup%3Ait",),
    "Sky Sport MotoGP Italia": (
        "vavoo_SKY%20SPORT%20MOTO%20GP%7Cgroup%3Ait",
    ),
    "Sky Sport NBA Italia": ("vavoo_SKY%20SPORT%20NBA%7Cgroup%3Ait",),
    "Sky Sport Uno Italia": ("vavoo_SKY%20SPORT%20UNO%7Cgroup%3Ait",),
    "TNT Sports 1": (
        "vavoo_TNT%20SPORTS%201%7Cgroup%3Auk",
        "vavoo_TNT%20SPORTS%201%20HD%7Cgroup%3Auk",
        "vavoo_TNT%20SPORTS%201%20%28BACKUP%29%7Cgroup%3Auk",
    ),
    "NRJ Hits": (
        "vavoo_NRJ%20HITS%7Cgroup%3Afr",
        "vavoo_NRJ%20HITS%20HD%7Cgroup%3Afr",
        "vavoo_NRJ%20HITS%20SD%7Cgroup%3Afr",
    ),
    "MCM": (
        "vavoo_MCM%7Cgroup%3Afr",
        "vavoo_MCM%20HD%7Cgroup%3Afr",
        "vavoo_MCM%20SD%7Cgroup%3Afr",
    ),
    "DAZN F1 España": (
        "vavoo_DAZN%20F1%7Cgroup%3Aes",
        "vavoo_DAZN%20F1%20HD%7Cgroup%3Aes",
        "vavoo_DAZN%20F1%20FHD%7Cgroup%3Aes",
    ),
    "Sport TV 4": (
        "vavoo_SPORT%20TV%204%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%204%20HD%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%204%20%28BACKUP%29%7Cgroup%3Apt",
    ),
    "Sport TV 5": (
        "vavoo_SPORT%20TV%205%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%205%20HD%7Cgroup%3Apt",
        "vavoo_SPORT%20TV%205%20%28BACKUP%29%7Cgroup%3Apt",
    ),
    "Sky Sport F1 Germany": (
        "vavoo_SKY%20SPORT%20F1%7Cgroup%3Ade",
        "vavoo_SKY%20SPORT%20F1%20HD%2B%7Cgroup%3Ade",
        "vavoo_SKY%20SPORT%20F1%20HD%20%28H265%29%7Cgroup%3Ade",
    ),
    "Sky Sport Golf Germany": (
        "vavoo_SKY%20SPORT%20GOLF%7Cgroup%3Ade",
        "vavoo_SKY%20SPORT%20GOLF%20HD%7Cgroup%3Ade",
    ),
    "Sky Sport Tennis Germany": (
        "vavoo_SKY%20SPORT%20TENNIS%7Cgroup%3Ade",
        "vavoo_SKY%20SPORT%20TENNIS%20HD%7Cgroup%3Ade",
    ),
    "Sky Sport Premier League Germany": (
        "vavoo_SKY%20SPORT%20PREMIER%20LEAGUE%7Cgroup%3Ade",
        "vavoo_SKY%20SPORT%20PREMIER%20LEAGUE%20HD%7Cgroup%3Ade",
    ),
    "Eurosport 1 Germany": (
        "vavoo_EUROSPORT%201%7Cgroup%3Ade",
        "vavoo_EUROSPORT%201%20HD%7Cgroup%3Ade",
        "vavoo_EUROSPORT%201%20FHD%7Cgroup%3Ade",
    ),
}

# Tanda adicional descubierta en los catálogos TvVoo por país/región.
# El nombre visible identifica la región; HD/FHD quedan agrupados como aliases.
TVVOO_STREAM_RESOLVER_IDS.update({
    "BBC Two Reino Unido": ("vavoo_BBC%20TWO%7Cgroup%3Auk",),
    "BBC Four Reino Unido": ("vavoo_BBC%20FOUR%7Cgroup%3Auk",),
    "BBC World News Reino Unido": ("vavoo_BBC%20WORLD%20NEWS%7Cgroup%3Auk",),
    "Sky Sports F1 Reino Unido": ("vavoo_SKY%20SPORTS%20F1%20FHD%7Cgroup%3Auk", "vavoo_SKY%20SPORTS%20F1%20HD%7Cgroup%3Auk", "vavoo_SKY%20SPORTS%20F1%7Cgroup%3Auk",),
    "TNT Sports 2 Reino Unido": ("vavoo_TNT%20SPORTS%202%20HD%7Cgroup%3Auk", "vavoo_TNT%20SPORTS%202%7Cgroup%3Auk",),
    "4Music Reino Unido": ("vavoo_4MUSIC%7Cgroup%3Auk",),
    "Bloomberg TV Italia": ("vavoo_BLOOMBERG%20TV%7Cgroup%3Ait", "vavoo_BLOOMBERG%20TV%204K%7Cgroup%3Ait",),
    "Eurosport 1 Italia": ("vavoo_EUROSPORT%201%7Cgroup%3Ait",),
    "Sky Sport F1 Italia": ("vavoo_SKY%20SPORT%20F1%7Cgroup%3Ait",),
    "Sky Sport Tennis Italia": ("vavoo_SKY%20SPORT%20TENNIS%7Cgroup%3Ait",),
    "Mezzo Live Francia": ("vavoo_MEZZO%20LIVE%20HD%7Cgroup%3Afr", "vavoo_MEZZO%20LIVE%7Cgroup%3Afr", "vavoo_MEZZO%20LIVE%20SD%7Cgroup%3Afr",),
    "Stingray Classica Francia": ("vavoo_STINGRAY%20CLASSICA%7Cgroup%3Afr",),
    "Trace Africa Francia": ("vavoo_TRACE%20AFRICA%7Cgroup%3Afr",),
    "RMC Sport 3 Francia": ("vavoo_RMC%20SPORT%203%20FHD%7Cgroup%3Afr", "vavoo_RMC%20SPORT%203%20HD%7Cgroup%3Afr", "vavoo_RMC%20SPORT%203%7Cgroup%3Afr",),
    "RT DE Alemania": ("vavoo_RT%20DE%7Cgroup%3Ade",),
    "Sky Sport 1 Alemania": ("vavoo_SKY%20SPORT%201%20HD%7Cgroup%3Ade", "vavoo_SKY%20SPORT%201%20HD%2B%7Cgroup%3Ade", "vavoo_SKY%20SPORT%201%7Cgroup%3Ade", "vavoo_SKY%20SPORT%201%20HEVC%7Cgroup%3Ade",),
    "XITE Alemania": ("vavoo_XITE%20HD%7Cgroup%3Ade", "vavoo_XITE%7Cgroup%3Ade",),
    "Sport TV 3 Portugal": ("vavoo_SPORT%20TV%203%20HD%7Cgroup%3Apt", "vavoo_SPORT%20TV%203%7Cgroup%3Apt",),
    "Eleven Sports 3 Portugal": ("vavoo_ELEVEN%20SPORT%203%7Cgroup%3Apt",),
    "Eurosport 1 Portugal": ("vavoo_EUROSPORT%201%20HD%7Cgroup%3Apt", "vavoo_EUROSPORT%201%7Cgroup%3Apt",),
    "MTV Portugal Portugal": ("vavoo_MTV%20PORTUGAL%7Cgroup%3Apt",),
    "Stingray iConcerts Portugal": ("vavoo_STINGRAY%20ICONCERTS%7Cgroup%3Apt",),
    "ESPN 2 España": ("vavoo_ESPN%202%7Cgroup%3Aes",),
    "DAZN 4 España": ("vavoo_DAZN%204%7Cgroup%3Aes",),
    "Eurosport 1 España": ("vavoo_EUROSPORT%201%20HD%7Cgroup%3Aes", "vavoo_EUROSPORT%201%7Cgroup%3Aes",),
    "BBC Earth Polonia": ("vavoo_BBC%20EARTH%20HD%7Cgroup%3Apl", "vavoo_BBC%20EARTH%7Cgroup%3Apl",),
    "CNN Polonia": ("vavoo_CNN%7Cgroup%3Apl",),
    "Eurosport 3 Polonia": ("vavoo_EUROSPORT%203%7Cgroup%3Apl",),
    "ESPN 1 Países Bajos": ("vavoo_ESPN%201%7Cgroup%3Anl",),
    "Fox Sports 1 Países Bajos": ("vavoo_FOX%20SPORTS%201%7Cgroup%3Anl",),
    "XITE Rock Países Bajos": ("vavoo_XITE%20ROCK%7Cgroup%3Anl",),
    "Stingray DJAZZ Países Bajos": ("vavoo_STINGRAY%20DJAZZ%7Cgroup%3Anl",),
    "TRT World Turquía": ("vavoo_TRT%20WORLD%7Cgroup%3Atr", "vavoo_TRT%20WORLD%20HEVC%7Cgroup%3Atr",),
    "Eurosport 1 Turquía": ("vavoo_EUROSPORT%201%7Cgroup%3Atr",),
    "beIN Sports 1 Turquía": ("vavoo_BEIN%20SPORTS%201%20HD%7Cgroup%3Atr", "vavoo_BEIN%20SPORTS%201%7Cgroup%3Atr", "vavoo_BEIN%20SPORTS%201%20H265%7Cgroup%3Atr",),
    "NBA TV Turquía": ("vavoo_NBA%20TV%20FHD%7Cgroup%3Atr", "vavoo_NBA%20TV%20HD%7Cgroup%3Atr", "vavoo_NBA%20TV%7Cgroup%3Atr",),
    "Arena Sport 1 Balcanes": ("vavoo_ARENA%20SPORT%201%20HD%7Cgroup%3Abk", "vavoo_ARENA%20SPORT%201%7Cgroup%3Abk",),
    "Eurosport 1 Balcanes": ("vavoo_EUROSPORT%201%7Cgroup%3Abk",),
    "RT Documentary Rusia": ("vavoo_RT%20DOCUMENTARY%7Cgroup%3Aru",),
    "Digi Sport 1 Rumanía": ("vavoo_DIGI%20SPORT%201%20HD%7Cgroup%3Aro", "vavoo_DIGI%20SPORT%201%7Cgroup%3Aro",),
    "Max Sport 1 Bulgaria": ("vavoo_MAX%20SPORT%201%7Cgroup%3Abg",),
    "Stingray iConcerts Bulgaria": ("vavoo_STINGRAY%20ICONCERTS%7Cgroup%3Abg",),
    "SuperSport 1 Albania": ("vavoo_SUPERSPORT%201%7Cgroup%3Aal",),
    "beIN Sports 1 MENA": ("vavoo_BEIN%20SPORTS%201%20HD%7Cgroup%3Aar", "vavoo_BEIN%20SPORTS%201%7Cgroup%3Aar", "vavoo_BEIN%20SPORTS%201%20SD%7Cgroup%3Aar",),
})


def build_resolver_catalog() -> dict:
    """Build the declarative catalogue consumed by VibeM3U.

    Only stable identifiers and allow-listed HTTPS endpoints belong here. The
    short-lived HLS responses returned by TvVoo/Highfly stay in the playlist as
    compatibility fallbacks and are never copied into this catalogue.
    """
    return {
        "schemaVersion": RESOLVER_SCHEMA_VERSION,
        "catalogVersion": RESOLVER_CATALOG_VERSION,
        "providers": [
            {
                "id": "tvn",
                "name": "TVN",
                "engine": "tvn",
                "enabledByDefault": True,
                "cacheTtlSeconds": 0,
                "match": {"tvgIds": ["0104"]},
                "config": {
                    "pageUrl": "https://live.tvn.cl/",
                    "pageReferer": "https://www.tvn.cl/",
                    "playlistTemplate": (
                        "https://mdstrm.com/live-stream-playlist/"
                        "{streamId}.m3u8"
                    ),
                    "playbackOrigin": "https://live.tvn.cl",
                    "defaultStreamId": "57a498c4d7b86d600e5461cb",
                },
            },
            {
                "id": "meganoticias",
                "name": "Meganoticias dinamico",
                "engine": "meganoticias",
                "enabledByDefault": True,
                "cacheTtlSeconds": 0,
                "match": {
                    "tvgIds": ["Meganoticias.cl", "MeganoticiasAhora.cl"]
                },
                "config": {
                    "pageUrl": MEGANOTICIAS_LIVE_PAGE,
                    "apiUrl": "https://api.mega.cl/api/v1/mdstrm",
                    "playlistTemplate": (
                        "https://mdstrm.com/live-stream-playlist/"
                        "{streamId}.m3u8"
                    ),
                    "playbackOrigin": "https://www.meganoticias.cl",
                },
            },
            {
                "id": "tvvoo",
                "name": "TvVoo",
                "engine": "tvvoo",
                "enabledByDefault": True,
                "cacheTtlSeconds": 900,
                "match": {
                    "tvgIds": [
                        "PremierSports1.ie",
                        "PremierSports2.ie",
                    ],
                    "tvgIdSuffixes": ["@TvVoo"],
                },
                "config": {
                    "endpointBase": TVVOO_STREAM_BASE_URL,
                    "maxAliases": 8,
                    "maxCandidates": 16,
                    "streamsPath": "streams",
                    "urlField": "url",
                    "allowHttpFallback": True,
                },
                "compatibilityAliases": {
                    name: list(aliases)
                    for name, aliases in TVVOO_STREAM_RESOLVER_IDS.items()
                },
            },
            {
                "id": "highfly",
                "name": "Highfly",
                "engine": "highfly",
                "enabledByDefault": True,
                "cacheTtlSeconds": 300,
                "match": {
                    "tvgIds": list(HIGHFLY_RESOLVER_CHANNELS),
                    "hosts": ["leaf.highfly.dev"],
                },
                "config": {
                    "directTemplate": (
                        "https://leaf.highfly.dev/m3u/{id}/live.m3u8"
                    ),
                    "manifestUrl": HIGHFLY_MANIFEST_URL,
                    "allowHttpFallback": True,
                },
            },
        ],
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
APP_HANDLED_CHANNELS = {"TVN", "Meganoticias"}
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
    "13 Go": f"{LOCAL_LOGOS_PUBLIC_BASE}/13go-mosca.png",
    "13 Cultura": f"{LOCAL_LOGOS_PUBLIC_BASE}/13cultura.svg",
    "13C": f"{LOCAL_LOGOS_PUBLIC_BASE}/13c.png",
    "RWND": f"{LOCAL_LOGOS_PUBLIC_BASE}/rewind-v2.png",
    "BBC Earth FAST": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc-earth-2023-i.svg",
    "BBC Earth Polonia": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc-earth-2023-i.svg",
    "BBC News": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc-news-transparent.png",
    "BBC Travel": f"{LOCAL_LOGOS_PUBLIC_BASE}/bbc.svg",
    "Bloomberg TV US": f"{LOCAL_LOGOS_PUBLIC_BASE}/bloomberg.svg",
    "Bloomberg Originals": f"{LOCAL_LOGOS_PUBLIC_BASE}/bloomberg.svg",
    "CBS News 24/7": f"{LOCAL_LOGOS_PUBLIC_BASE}/cbs-news.svg",
    "TRT World": f"{LOCAL_LOGOS_PUBLIC_BASE}/trt-world.svg",
    "CNA": f"{LOCAL_LOGOS_PUBLIC_BASE}/cna.svg",
    "Africanews English": f"{LOCAL_LOGOS_PUBLIC_BASE}/africanews.svg",
    "Qello Concerts by Stingray": f"{LOCAL_LOGOS_PUBLIC_BASE}/stingray-concerts.png",
    "Stingray Classica": f"{LOCAL_LOGOS_PUBLIC_BASE}/stingray-classica-official.svg",
    "Stingray Classica Francia": f"{LOCAL_LOGOS_PUBLIC_BASE}/stingray-classica-official.svg",
    "Stingray DJAZZ": f"{LOCAL_LOGOS_PUBLIC_BASE}/stingray-djazz.svg",
    "XITE 80s Flashback": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "XITE 90s Throwback": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "MTV Classic": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-classic.svg",
    "MTV Biggest Pop": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-biggest-pop.svg",
    "MTV Spankin' New": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-spankin-new.svg",
    "MTV Flow Latino": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-flow-latino.svg",
    "XITE Rock x Metal": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "MTV Rocks": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-rocks.svg",
    "XITE Just Chill": f"{LOCAL_LOGOS_PUBLIC_BASE}/xite.svg",
    "Sky Sports F1": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-f1-mosca-logopedia.webp",
    "Sky Sports F1 UK (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-f1-mosca-logopedia.webp",
    "Sky Sports F1 Italia (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-f1-mosca-logopedia.webp",
    "Sky Sports Action UK (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports Cricket UK (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports Football Irlanda (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports Main Event Irlanda (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-main-event.png",
    "Sky Sports News UK (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports NFL UK (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport Austria 1 (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport Basket Italia (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport Top Event Alemania (Directo)": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "ESPN": f"{LOCAL_LOGOS_PUBLIC_BASE}/espn.svg",
    "Sky Sports Premier League": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-premier-league.png",
    "Premier Sports 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/premier-sports-1.png",
    "Premier Sports 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/premier-sports-2.png",
    "Sky Sport 1 NZ": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sport-1-nz.png",
    "Sky Sports Tennis": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-tennis.png",
    "Reuters": f"{LOCAL_LOGOS_PUBLIC_BASE}/reuters.png",
    "Real Wild": f"{LOCAL_LOGOS_PUBLIC_BASE}/real-wild.png",
    "TyC Sports": f"{LOCAL_LOGOS_PUBLIC_BASE}/tyc-sports.png",
    "Sky Sports Main Event": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports-main-event.png",
    "Sky Sports Arena": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "TNT Sports 3": f"{LOCAL_LOGOS_PUBLIC_BASE}/tnt-sports-3.png",
    "CNN": f"{LOCAL_LOGOS_PUBLIC_BASE}/cnn.png",
    "Eurosport 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport-1.png",
    "MTV Hits": f"{LOCAL_LOGOS_PUBLIC_BASE}/mtv-hits.png",
    "M6 Music": f"{LOCAL_LOGOS_PUBLIC_BASE}/m6-music.png",
    "Trace Urban": f"{LOCAL_LOGOS_PUBLIC_BASE}/trace-urban.png",
    "DAZN FAST+": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn-fast.png",
    "Sport TV 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/sport-tv-1.png",
    "Sport TV 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/sport-tv-2.png",
    "Sky Sports Football": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports Mix": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports News": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sports NFL": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport 24 Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport Calcio Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport Max Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport MotoGP Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport NBA Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Sky Sport Uno Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sports.svg",
    "Eurosport 2 UK": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport.svg",
    "Eurosport 2 España": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport.svg",
    "Eurosport 2 Germany": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport.svg",
    "Eurosport 2 Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport.svg",
    "DAZN Ligue 1 Live 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN Ligue 1 Live 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN Ligue 1 Live 3": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN Ligue 1 Live 4": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 3 España": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 2 España": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN LaLiga 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN LaLiga 2": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 1 Portugal": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 2 Portugal": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 3 Portugal": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 4 Portugal": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 5 Portugal": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 6 Portugal": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "DAZN 1 Italia": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn.svg",
    "TNT Sports 1": f"{LOCAL_LOGOS_PUBLIC_BASE}/tnt-sports-1.png",
    "NRJ Hits": f"{LOCAL_LOGOS_PUBLIC_BASE}/nrj-hits.png",
    "MCM": f"{LOCAL_LOGOS_PUBLIC_BASE}/mcm.png",
    "DAZN F1 España": f"{LOCAL_LOGOS_PUBLIC_BASE}/dazn-f1.png",
    "Sport TV 4": f"{LOCAL_LOGOS_PUBLIC_BASE}/sport-tv-4.png",
    "Sport TV 5": f"{LOCAL_LOGOS_PUBLIC_BASE}/sport-tv-5.png",
    "Sky Sport F1 Germany": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sport-f1-de.png",
    "Sky Sport Golf Germany": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sport-golf-de.png",
    "Sky Sport Tennis Germany": f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sport-tennis-de.png",
    "Sky Sport Premier League Germany": (
        f"{LOCAL_LOGOS_PUBLIC_BASE}/sky-sport-premier-league-de.png"
    ),
    "Eurosport 1 Germany": f"{LOCAL_LOGOS_PUBLIC_BASE}/eurosport-1-de.png",
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
    "13 Go": (
        "Diego y Glot",
        "Continuidad de Diego y Glot para cubrir toda la ventana visible de 13 Go.",
    ),
    "Autentic History": (
        "Live",
        "",
    ),
    "Sky Sports Mix": (
        "Sky Sports Mix en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "Sky Sports News": (
        "Sky Sports News en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "Eurosport 2 UK": (
        "Eurosport 2 UK en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "DAZN Ligue 1 Live 1": (
        "DAZN Ligue 1 Live 1 en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "DAZN Ligue 1 Live 2": (
        "DAZN Ligue 1 Live 2 en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "DAZN Ligue 1 Live 3": (
        "DAZN Ligue 1 Live 3 en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "DAZN Ligue 1 Live 4": (
        "DAZN Ligue 1 Live 4 en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
    "DAZN 6 Portugal": (
        "DAZN 6 Portugal en vivo",
        "Senal deportiva continua; TvVoo no publica una parrilla XMLTV estable para esta senal.",
    ),
}
FORCED_EPG_TITLES = {
    "13Kids.cl": "Diego y Glot",
}
NEWS_CHANNEL_ORDER = ("24 Horas", "Meganoticias", "CHV Noticias", "T13")
CONTENT_CATEGORY_ORDER = (
    "Nacionales",
    "Noticias nacionales",
    "Noticias internacionales",
    "Deportes",
    "Música",
    "Misceláneos",
)
CONTENT_CATEGORY_INDEX = {
    category: index for index, category in enumerate(CONTENT_CATEGORY_ORDER)
}

# Estas cinco senales siguen siendo "Miscelaneos" por contenido, pero el
# usuario las quiere inmediatamente despues de NTV y en un orden estable.
# Se separa el orden visual de la categoria para no falsear su group-title.
POST_NATIONAL_NEWS_CHANNEL_IDS = {
    "45",  # NTV
    "1437",  # TVN3
    "13C.cl@SD",
    "13Cultura.cl@DPS",
    "RewindTV.cl@SD",
}
POST_NATIONAL_NEWS_CHANNEL_ORDER = (
    "45",
    "1437",
    "13C.cl@SD",
    "13Cultura.cl@DPS",
    "RewindTV.cl@SD",
)
POST_NATIONAL_NEWS_CHANNEL_INDEX = {
    channel_id: index
    for index, channel_id in enumerate(POST_NATIONAL_NEWS_CHANNEL_ORDER)
}
DW_CHANNEL_ORDER = ("DW.de", "DWEnglish.de")
DW_CHANNEL_IDS = frozenset(DW_CHANNEL_ORDER)
POST_NATIONAL_NEWS_SECTION = "Despues de noticias nacionales"
ORDER_SECTION_ORDER = (
    "Nacionales",
    "Noticias nacionales",
    POST_NATIONAL_NEWS_SECTION,
    "Noticias internacionales",
    "Deportes",
    "Música",
    "Misceláneos",
)
ORDER_SECTION_INDEX = {
    section: index for index, section in enumerate(ORDER_SECTION_ORDER)
}
ORDER_SECTION_GROUPS = {
    "Nacionales": "Nacionales",
    "Noticias nacionales": "Noticias nacionales",
    POST_NATIONAL_NEWS_SECTION: "Misceláneos",
    "Noticias internacionales": "Noticias internacionales",
    "Deportes": "Deportes",
    "Música": "Música",
    "Misceláneos": "Misceláneos",
}

# La clasificación se hace por ``tvg-id`` o por reglas acotadas de contenido,
# nunca por el estado de salud. Un canal retirado temporalmente debe conservar
# su posición en ``channel-catalog.m3u`` para volver al mismo lugar cuando se
# recupere.
NATIONAL_CHANNEL_IDS = {
    "0104",  # TVN
    "0105",  # Mega
    "0106",  # CHV
    "0107",  # Canal 13
    "0102",  # La Red
    "13Kids.cl",
}
NATIONAL_NEWS_CHANNEL_IDS = {
    "0201",  # 24 Horas
    "Meganoticias.cl",
    "1153",  # CHV Noticias
    "0124",  # T13
}
INTERNATIONAL_NEWS_CHANNEL_IDS = {
    "TVChile.cl",
    "DW.de",
    "France24.fr",
    "France24.fr@English",
    "ReutersTV.us",
    "CNN.us@TvVoo",
    "EuronewsSpanish.fr",
    "NHKWorldJapan.jp",
    "AlJazeera.qa",
    "DWEnglish.de",
    "BBCNews.uk",
    "Vavoo.uk.BBCWORLDNEWS@TvVoo",
    "Vavoo.it.BLOOMBERGTV@TvVoo",
    "Vavoo.pl.CNN@TvVoo",
    "Vavoo.de.RTDE@TvVoo",
    "Vavoo.tr.TRTWORLD@TvVoo",
}
MUSIC_CHANNEL_IDS = {
    "XITEHits.nl@Germany",
    "XITENuevoLatino.us",
    "XITESiempreLatino.us",
    "XITE80sFlashback.us",
    "XITE90sThrowback.us",
    "XITERockxMetal.nl",
    "XITEJustChill.nl",
    "M1.ua@SD",
    "M2.ua@SD",
    "QelloConcertsbyStingray.ca",
    "StingrayClassica.ca",
    "MTVClassic.us",
    "MTVBiggestPop.us",
    "MTVSpankinNew.us",
    "MTVFlowLatino.us",
    "MTVHits.fr@TvVoo",
    "M6Music.fr@TvVoo",
    "TraceUrban.fr@TvVoo",
    "NRJHits.fr@TvVoo",
    "MCM.fr@TvVoo",
    "Vavoo.uk.4MUSIC@TvVoo",
    "Vavoo.fr.MEZZOLIVE@TvVoo",
    "Vavoo.fr.STINGRAYCLASSICA@TvVoo",
    "Vavoo.pt.MTVPORTUGAL@TvVoo",
    "Vavoo.pt.STINGRAYICONCERTS@TvVoo",
    "Vavoo.nl.XITEROCK@TvVoo",
    "Vavoo.nl.STINGRAYDJAZZ@TvVoo",
    "Vavoo.bg.STINGRAYICONCERTS@TvVoo",
}
SPORTS_NAME_PATTERN = re.compile(
    r"(?:\bsport(?:s)?\b|\beurosport\b|\bespn\b|\bdazn\b|\bf1\b|\bmotogp\b|"
    r"\bformula\s*1\b|\bsky\s+sport|\bsky\s+sports|\btyc\s+sports\b|"
    r"\bnba\b|\bsupersport\b)",
    re.IGNORECASE,
)
MUSIC_NAME_PATTERN = re.compile(
    r"(?:\bxite\b|\bmtv\b|\bmusic\b|\bmusica\b|\bqello\b|\bstingray\b|"
    r"\btrace\b|\bnrj\b|\bmcm\b|\bmezzo\b|\b4music\b|"
    r"\bconcerts?\b|\biconcerts\b)",
    re.IGNORECASE,
)
INTERNATIONAL_NEWS_NAME_PATTERN = re.compile(
    r"(?:\bbbc\s+(?:news|world\s+news)\b|\bcnn\b|\bdw(?:\s|$)|\bfrance\s*24\b|"
    r"\breuters\b|\beuronews\b|\bnhk\b|\bal\s+jazeera\b|\bbloomberg\b|"
    r"\brt\s+de\b|\btrt\s+world\b)",
    re.IGNORECASE,
)
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
    # El master oficial exige un access_token de corta duración. Se publica
    # solo como respaldo estable para clientes externos; VibeM3U lo renueva
    # desde la página oficial justo antes de reproducir.
    "Meganoticias": [MEGANOTICIAS_OFFICIAL_MASTER_URL],
    "La Red": [LA_RED_MASTER_URL],
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
    "CHV Deportes",
    "Mega",
    "Meganoticias",
    "24 Horas",
    "La Red",
    "Canal 13",
    "CHV Noticias",
    "13 Cultura",
    "13 Go",
    "Autentic History",
    "France 24 Español",
    "Reuters",
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
    "Sky Sports Arena",
    "Sky Sports F1",
    "Sky Sports Tennis",
    "Sky Sports F1 UK (Directo)",
    "Sky Sports F1 Italia (Directo)",
    "Sky Sports Action UK (Directo)",
    "Sky Sports Cricket UK (Directo)",
    "Sky Sports Football Irlanda (Directo)",
    "Sky Sports Main Event Irlanda (Directo)",
    "Sky Sports News UK (Directo)",
    "Sky Sports NFL UK (Directo)",
    "Sky Sport Austria 1 (Directo)",
    "Sky Sport Basket Italia (Directo)",
    "Sky Sport Top Event Alemania (Directo)",
    "TNT Sports 3",
    "CNN",
    "Eurosport 1",
    "MTV Hits",
    "M6 Music",
    "Trace Urban",
    "DAZN FAST+",
    "Sport TV 1",
    "Sport TV 2",
    "Sky Sports Football",
    "Sky Sports NFL",
    "Sky Sports Mix",
    "Sky Sports News",
    "Eurosport 2 UK",
    "Eurosport 2 España",
    "DAZN Ligue 1 Live 1",
    "DAZN Ligue 1 Live 2",
    "DAZN Ligue 1 Live 3",
    "DAZN Ligue 1 Live 4",
    "Eurosport 2 Germany",
    "DAZN 3 España",
    "DAZN 2 España",
    "DAZN LaLiga 1",
    "DAZN LaLiga 2",
    "DAZN 1 Portugal",
    "DAZN 2 Portugal",
    "DAZN 3 Portugal",
    "DAZN 4 Portugal",
    "DAZN 5 Portugal",
    "DAZN 6 Portugal",
    "DAZN 1 Italia",
    "Eurosport 2 Italia",
    "Sky Sport 24 Italia",
    "Sky Sport Calcio Italia",
    "Sky Sport Max Italia",
    "Sky Sport MotoGP Italia",
    "Sky Sport NBA Italia",
    "Sky Sport Uno Italia",
    "TNT Sports 1",
    "NRJ Hits",
    "MCM",
    "DAZN F1 España",
    "Sport TV 4",
    "Sport TV 5",
    "Sky Sport F1 Germany",
    "Sky Sport Golf Germany",
    "Sky Sport Tennis Germany",
    "Sky Sport Premier League Germany",
    "Eurosport 1 Germany",
}

# Las nuevas pruebas deben pasar master, variante y primer segmento en cada
# ejecución antes de que el updater las considere publicables.
SEGMENT_CHECK_CHANNELS.update({
    "SuperSport 1 Albania",
    "beIN Sports 1 MENA",
    "Max Sport 1 Bulgaria",
    "Stingray iConcerts Bulgaria",
    "Arena Sport 1 Balcanes",
    "Eurosport 1 Balcanes",
    "RT DE Alemania",
    "Sky Sport 1 Alemania",
    "XITE Alemania",
    "DAZN 4 España",
    "ESPN 2 España",
    "Eurosport 1 España",
    "Mezzo Live Francia",
    "RMC Sport 3 Francia",
    "Stingray Classica Francia",
    "Trace Africa Francia",
    "Bloomberg TV Italia",
    "Eurosport 1 Italia",
    "Sky Sport F1 Italia",
    "Sky Sport Tennis Italia",
    "ESPN 1 Países Bajos",
    "Fox Sports 1 Países Bajos",
    "Stingray DJAZZ Países Bajos",
    "XITE Rock Países Bajos",
    "BBC Earth Polonia",
    "CNN Polonia",
    "Eurosport 3 Polonia",
    "Eleven Sports 3 Portugal",
    "Eurosport 1 Portugal",
    "MTV Portugal Portugal",
    "Sport TV 3 Portugal",
    "Stingray iConcerts Portugal",
    "Digi Sport 1 Rumanía",
    "RT Documentary Rusia",
    "beIN Sports 1 Turquía",
    "Eurosport 1 Turquía",
    "NBA TV Turquía",
    "TRT World Turquía",
    "4Music Reino Unido",
    "BBC Four Reino Unido",
    "BBC Two Reino Unido",
    "BBC World News Reino Unido",
    "Sky Sports F1 Reino Unido",
    "TNT Sports 2 Reino Unido",
})
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
class DynamicRefreshOutcome:
    """Resultado en memoria de una renovacion de fuente dinamica.

    ``resolved_url`` y ``check_result`` no se escriben en los informes: solo
    sirven para aplicar de forma serial los cambios producidos por los
    workers y evitar una segunda validacion del mismo candidato.
    """

    channel: str
    resolver: str
    accepted: bool
    changed: bool
    skipped: bool
    detail: str
    resolved_url: str | None = None
    check_result: CheckResult | None = None


@dataclass(frozen=True)
class LogoResult:
    channel: str
    url: str
    ok: bool
    detail: str


# Politicas conservadoras por proveedor. Los limites mas cortos evitan que un
# CDN caido monopolice el runner, pero se mantienen dos intentos para no
# confundir una perdida puntual con una senal retirada.
@dataclass(frozen=True)
class ChannelCheckPolicy:
    attempts: int
    playlist_timeout: int
    segment_timeout: int
    resolver_timeout: int
    retry_delay: float
    workers: int


CHANNEL_CHECK_POLICIES = {
    "direct": ChannelCheckPolicy(
        attempts=2,
        playlist_timeout=20,
        segment_timeout=14,
        resolver_timeout=20,
        retry_delay=0.75,
        workers=8,
    ),
    "tvn": ChannelCheckPolicy(
        attempts=2,
        playlist_timeout=22,
        segment_timeout=16,
        resolver_timeout=22,
        retry_delay=0.75,
        workers=4,
    ),
    "meganoticias": ChannelCheckPolicy(
        attempts=2,
        playlist_timeout=22,
        segment_timeout=16,
        resolver_timeout=22,
        retry_delay=0.75,
        workers=3,
    ),
    "tvvoo": ChannelCheckPolicy(
        attempts=2,
        playlist_timeout=18,
        segment_timeout=12,
        resolver_timeout=22,
        retry_delay=0.5,
        workers=6,
    ),
    "highfly": ChannelCheckPolicy(
        attempts=2,
        playlist_timeout=20,
        segment_timeout=14,
        resolver_timeout=20,
        retry_delay=0.5,
        workers=4,
    ),
}


def channel_check_policy(channel: Channel) -> ChannelCheckPolicy:
    """Choose timeouts/retries from the explicit resolver classification."""
    return CHANNEL_CHECK_POLICIES.get(
        resolver_engine_for(channel), CHANNEL_CHECK_POLICIES["direct"]
    )


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


def content_category_for(channel: Channel) -> str:
    """Return the stable thematic bucket used by both published playlists.

    The explicit ID sets cover the current catalogue. The narrow name/group
    rules let future additions be placed sensibly without using a broad,
    error-prone substring match for resolver selection.
    """
    if channel.tvg_id in NATIONAL_CHANNEL_IDS:
        return "Nacionales"
    if channel.tvg_id in NATIONAL_NEWS_CHANNEL_IDS:
        return "Noticias nacionales"
    if (
        channel.tvg_id in INTERNATIONAL_NEWS_CHANNEL_IDS
        or INTERNATIONAL_NEWS_NAME_PATTERN.search(channel.name)
    ):
        return "Noticias internacionales"
    if (
        channel.tvg_id == "1763"
        or "deporte" in channel.group.lower()
        or SPORTS_NAME_PATTERN.search(channel.name)
    ):
        return "Deportes"
    if (
        channel.tvg_id in MUSIC_CHANNEL_IDS
        or "musica" in channel.group.lower()
        or "música" in channel.group.lower()
        or MUSIC_NAME_PATTERN.search(channel.name)
    ):
        return "Música"
    return "Misceláneos"


def with_content_category(line: str, category: str) -> str:
    """Set the visible group without changing any other EXTINF metadata."""
    metadata, separator, display_name = line.rpartition(",")
    if not separator or not metadata.startswith("#EXTINF:"):
        raise ValueError(f"linea #EXTINF invalida: {line[:120]}")
    group_attribute = f'group-title="{category}"'
    if re.search(r'\bgroup-title="[^"]*"', metadata):
        metadata = re.sub(
            r'\bgroup-title="[^"]*"', group_attribute, metadata, count=1
        )
    else:
        metadata = f"{metadata} {group_attribute}"
    return f"{metadata},{display_name}"


def order_section_for(channel: Channel) -> str:
    if channel.tvg_id in POST_NATIONAL_NEWS_CHANNEL_IDS:
        return POST_NATIONAL_NEWS_SECTION
    return content_category_for(channel)


def within_section_order_key(
    channel: Channel,
    original_index: int,
    section: str,
    channels: list[Channel],
) -> tuple[int, int]:
    """Keep requested channel families together without changing categories."""
    if section == POST_NATIONAL_NEWS_SECTION:
        return (0, POST_NATIONAL_NEWS_CHANNEL_INDEX[channel.tvg_id])

    if section == "Noticias internacionales":
        dw_positions = [
            index
            for index, item in enumerate(channels)
            if item.tvg_id in DW_CHANNEL_IDS
        ]
        if len(dw_positions) == len(DW_CHANNEL_ORDER):
            dw_anchor = min(dw_positions)
            if channel.tvg_id in DW_CHANNEL_IDS:
                return (dw_anchor, DW_CHANNEL_ORDER.index(channel.tvg_id))
            # Reserve two adjacent positions at the first DW occurrence. This
            # keeps DW Español immediately followed by DW English even when an
            # older catalogue had another international channel between them.
            if original_index > dw_anchor:
                return (original_index + 1, 2)

    return (original_index, 2)


def order_channels_by_content(lines: list[str]) -> bool:
    """Order the complete catalogue and normalize its six public groups.

    Only channel records are moved. The first ``#EXTM3U`` header is retained;
    explanatory section comments from older layouts are intentionally removed
    so a failed channel cannot leave a misleading heading in the public copy.
    ``filter_playlist_to_working_channels`` later removes failed records from
    this already ordered sequence, preserving their future catalogue position.
    """
    channels = parse_channels(lines)
    if not channels:
        return False

    first_info_line = min(channel.info_line for channel in channels)
    header = [
        line for line in lines[:first_info_line] if line.startswith("#EXTM3U")
    ]
    if not header:
        header = ["#EXTM3U"]

    records = []
    for original_index, channel in enumerate(channels):
        category = content_category_for(channel)
        section = order_section_for(channel)
        records.append(
            (
                ORDER_SECTION_INDEX[section],
                within_section_order_key(
                    channel, original_index, section, channels
                ),
                original_index,
                section,
                category,
                with_content_category(lines[channel.info_line], category),
                lines[channel.url_line],
            )
        )
    records.sort(key=lambda item: (item[0], item[1]))

    ordered_lines = list(header)
    current_section = None
    category_counts = {category: 0 for category in CONTENT_CATEGORY_ORDER}
    for _, _, _, section, category, info_line, url_line in records:
        if section != current_section:
            if ordered_lines and ordered_lines[-1] != "":
                ordered_lines.append("")
            ordered_lines.append(f"# {section}")
            current_section = section
        ordered_lines.extend((info_line, url_line))
        category_counts[category] += 1
    while ordered_lines and ordered_lines[-1] == "":
        ordered_lines.pop()

    changed = ordered_lines != lines
    if changed:
        lines[:] = ordered_lines
        counts = ", ".join(
            f"{category}={category_counts[category]}"
            for category in CONTENT_CATEGORY_ORDER
        )
        print(f"  [OK] Orden tematico aplicado: {counts}")
    return changed


def filter_playlist_to_working_channels(
    lines: list[str], channels: list[Channel], working_names: set[str]
) -> list[str]:
    """Build the public playlist while retaining every candidate elsewhere.

    ``channel-catalog.m3u`` remains the canonical inventory. Only the EXTINF
    and URL lines of a failed ordinary candidate are omitted here. Explicit
    direct probes are passed in ``working_names`` by ``main`` so they remain
    visible for manual testing. Empty thematic separators are removed from
    the public copy, while the catalogue keeps every candidate in its original
    position for the next retry.
    """
    omitted_indexes: set[int] = set()
    for channel in channels:
        if channel.name not in working_names:
            omitted_indexes.update((channel.info_line, channel.url_line))
    working_groups = {
        channel.group
        for channel in channels
        if channel.name in working_names
    }
    category_headers = {
        f"# {section}": category for section, category in ORDER_SECTION_GROUPS.items()
    }
    filtered_lines = [
        line
        for index, line in enumerate(lines)
        if index not in omitted_indexes
        and (
            line not in category_headers
            or category_headers[line] in working_groups
        )
    ]
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()
    return filtered_lines


def resolver_attributes_for(channel: Channel) -> dict[str, str]:
    if channel.tvg_id == "0104":
        return {"x-resolver": "tvn", "x-resolver-refresh": "on_play"}
    if channel.tvg_id in {"Meganoticias.cl", "MeganoticiasAhora.cl"}:
        return {
            "x-resolver": "meganoticias",
            "x-resolver-refresh": "on_play",
        }
    resolver_ids = TVVOO_STREAM_RESOLVER_IDS.get(channel.name)
    if resolver_ids:
        return {
            "x-resolver": "tvvoo",
            "x-resolver-endpoint": TVVOO_STREAM_BASE_URL,
            "x-resolver-ids": ";".join(resolver_ids),
            "x-resolver-refresh": "on_play",
        }
    highfly_slug = HIGHFLY_RESOLVER_CHANNELS.get(channel.tvg_id)
    if highfly_slug:
        return {
            "x-resolver": "highfly",
            "x-resolver-id": highfly_slug,
            "x-resolver-manifest": HIGHFLY_MANIFEST_URL,
            "x-resolver-refresh": "on_play",
        }
    return {}


def resolver_engine_for(channel: Channel) -> str:
    """Return the executable resolver family assigned to ``channel``."""
    return resolver_attributes_for(channel).get("x-resolver", "direct")


def playlist_key_for(channel: Channel) -> str:
    """Return the public list that owns a channel.

    Direct sources and the Chilean resolvers stay in the principal list. The
    renewable catalogue providers are isolated in the external list so a
    Vavoo/TvVoo outage cannot make the official list unavailable.
    """
    if channel.tvg_id in MAIN_PLAYLIST_CHANNEL_IDS:
        return "main"
    engine = resolver_engine_for(channel)
    if engine in EXTERNAL_PLAYLIST_RESOLVERS:
        return "external"
    if engine in MAIN_PLAYLIST_RESOLVERS:
        return "main"
    # Unknown/future providers stay in the principal fallback until an
    # explicit executable resolver and list policy are added.
    return "main"


def is_direct_probe(channel: Channel) -> bool:
    """Return whether a direct channel is intentionally kept for live testing."""
    return (
        resolver_engine_for(channel) == "direct"
        and channel.tvg_id in DIRECT_PROBE_CHANNEL_IDS
    )


def with_resolver_attributes(line: str, attributes: dict[str, str]) -> str:
    metadata, separator, display_name = line.rpartition(",")
    if not separator or not metadata.startswith("#EXTINF:"):
        raise ValueError(f"linea #EXTINF invalida: {line[:120]}")
    for name in RESOLVER_ATTRIBUTE_NAMES:
        metadata = re.sub(
            rf"\s+{re.escape(name)}=(?:\"[^\"]*\"|[^\s,]+)",
            "",
            metadata,
        )
    if attributes:
        encoded = " ".join(f'{name}="{value}"' for name, value in attributes.items())
        metadata = f"{metadata} {encoded}"
    return f"{metadata},{display_name}"


def pin_resolver_metadata(lines: list[str]) -> bool:
    changed = False
    for channel in parse_channels(lines):
        if channel.info_line < 0:
            continue
        original = lines[channel.info_line]
        attributes = resolver_attributes_for(channel)
        updated = with_resolver_attributes(original, attributes)
        if updated != original:
            lines[channel.info_line] = updated
            changed = True
            resolver = attributes.get("x-resolver", "directo")
            print(f"  [OK] {channel.name}: metadatos de resolutor {resolver}")
    return changed


def resolver_catalog_text(catalog: dict) -> str:
    return json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"


def catalog_version_key(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d{4}(?:\.\d+){3}", value):
        raise ValueError(f"catalogVersion invalida: {value}")
    return tuple(int(part) for part in value.split("."))


def write_resolver_catalog(path: Path = RESOLVER_CATALOG_PATH) -> bool:
    expected = build_resolver_catalog()
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"{path.name} existente no es JSON valido: {error}") from error
        current_version = str(current.get("catalogVersion", ""))
        if catalog_version_key(current_version) > catalog_version_key(
            RESOLVER_CATALOG_VERSION
        ):
            raise ValueError(
                f"{path.name} tiene una version futura ({current_version})"
            )
        if current_version == RESOLVER_CATALOG_VERSION and current != expected:
            raise ValueError(
                "el contenido del catalogo cambio sin aumentar catalogVersion"
            )
        if current == expected:
            return False
    path.write_text(resolver_catalog_text(expected), encoding="utf-8", newline="\n")
    print(f"  [OK] {path.name}: catalogo {RESOLVER_CATALOG_VERSION} generado")
    return True


def iter_catalog_urls(value: object):
    if isinstance(value, dict):
        for nested in value.values():
            yield from iter_catalog_urls(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_catalog_urls(nested)
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        yield value


def validate_resolver_catalog(path: Path = RESOLVER_CATALOG_PATH) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
        catalog = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name} no es JSON valido: {error}") from error
    if len(raw.encode("utf-8")) > 262_144:
        raise ValueError(f"{path.name} supera el limite de 256 KiB de VibeM3U")
    if catalog.get("schemaVersion") != RESOLVER_SCHEMA_VERSION:
        raise ValueError("resolver-catalog.json debe usar schemaVersion 1")
    catalog_version_key(str(catalog.get("catalogVersion", "")))
    providers = catalog.get("providers")
    if not isinstance(providers, list):
        raise ValueError("resolver-catalog.json no contiene providers validos")
    ids = [provider.get("id") for provider in providers if isinstance(provider, dict)]
    engines = {
        provider.get("engine") for provider in providers if isinstance(provider, dict)
    }
    if len(ids) != len(set(ids)):
        raise ValueError("resolver-catalog.json contiene proveedores duplicados")
    if set(ids) != ALLOWED_RESOLVER_ENGINES or engines != ALLOWED_RESOLVER_ENGINES:
        raise ValueError("el catalogo debe contener solamente los cinco motores permitidos")
    forbidden = ("serverkey", "/sunshine/", "access_token=", "token=", "streams[].url")
    lowered = raw.lower()
    if any(marker in lowered for marker in forbidden):
        raise ValueError("el catalogo contiene una clave, token o URL de sesion")
    allowed_hosts = {
        "live.tvn.cl",
        "www.tvn.cl",
        "mdstrm.com",
        "www.meganoticias.cl",
        "api.mega.cl",
        "www.24horas.cl",
        "tvvoo.hayd.uk",
        "leaf.highfly.dev",
        "sports.highfly.dev",
        "raw.githubusercontent.com",
    }
    for url in iter_catalog_urls(catalog):
        parsed = urlparse(url.replace("{streamId}", "stream").replace("{id}", "id"))
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in allowed_hosts:
            raise ValueError(f"endpoint no permitido en catalogo: {url}")
        if parsed.hostname == "raw.githubusercontent.com" and not parsed.path.startswith(
            "/SPxMM3R1/lista-m3u/"
        ):
            raise ValueError(f"ruta GitHub Raw no permitida: {url}")
    by_id = {provider["id"]: provider for provider in providers}
    aliases = by_id["tvvoo"].get("compatibilityAliases")
    expected_aliases = {
        name: list(values) for name, values in TVVOO_STREAM_RESOLVER_IDS.items()
    }
    if aliases != expected_aliases:
        raise ValueError("los aliases TvVoo no coinciden con la fuente del actualizador")
    highfly_manifest = by_id["highfly"].get("config", {}).get("manifestUrl")
    if highfly_manifest != HIGHFLY_MANIFEST_URL or "/configure" in highfly_manifest:
        raise ValueError("Highfly debe apuntar al manifest.json final configurado")
    return catalog


def validate_playlist_resolvers(lines: list[str]) -> dict[str, int]:
    channels = parse_channels(lines)
    identities: set[tuple[str, str]] = set()
    counts = {engine: 0 for engine in sorted(ALLOWED_RESOLVER_ENGINES)}
    for channel in channels:
        identity = (channel.tvg_id, channel.name)
        if identity in identities:
            raise ValueError(
                f"entrada de canal duplicada: {channel.name} ({channel.tvg_id})"
            )
        identities.add(identity)
        line = lines[channel.info_line]
        attrs = {
            name: match.group(1)
            for name in RESOLVER_ATTRIBUTE_NAMES
            if (match := re.search(rf'\b{re.escape(name)}="([^"]*)"', line))
        }
        expected = resolver_attributes_for(channel)
        if attrs != expected:
            raise ValueError(
                f"{channel.name}: metadatos de resolutor distintos al contrato"
            )
        engine = attrs.get("x-resolver")
        if not engine:
            continue
        if engine not in ALLOWED_RESOLVER_ENGINES:
            raise ValueError(f"{channel.name}: resolutor no permitido {engine}")
        if not channel.tvg_id:
            raise ValueError(f"{channel.name}: canal dinamico sin tvg-id estable")
        counts[engine] += 1
        serialized = " ".join(attrs.values()).lower()
        if any(marker in serialized for marker in ("/sunshine/", "serverkey", "token=")):
            raise ValueError(f"{channel.name}: atributos contienen datos temporales")
        if engine == "tvvoo":
            aliases = attrs.get("x-resolver-ids", "").split(";")
            if not aliases or any(not alias for alias in aliases):
                raise ValueError(f"{channel.name}: TvVoo sin aliases estables")
            if tuple(aliases) != TVVOO_STREAM_RESOLVER_IDS[channel.name]:
                raise ValueError(f"{channel.name}: aliases TvVoo fuera de orden")
        elif engine == "highfly":
            if not attrs.get("x-resolver-id") or not attrs.get("x-resolver-manifest"):
                raise ValueError(f"{channel.name}: Highfly incompleto")
            if "/configure" in attrs["x-resolver-manifest"]:
                raise ValueError(f"{channel.name}: Highfly apunta a HTML configure")
    production_meganoticias = [
        channel for channel in channels if channel.tvg_id == "Meganoticias.cl"
    ]
    if len(production_meganoticias) != 1:
        raise ValueError("Meganoticias.cl debe conservar exactamente una entrada")
    production_attributes = resolver_attributes_for(production_meganoticias[0])
    if production_attributes.get("x-resolver") != "meganoticias":
        raise ValueError("Meganoticias.cl debe usar el resolutor oficial")
    for channel in channels:
        if channel.url.startswith("https://jmp2.uk/plu-") and resolver_attributes_for(channel):
            raise ValueError(f"{channel.name}: Pluto no debe usar x-resolver")
    expected_tvvoo = set(TVVOO_STREAM_RESOLVER_IDS)
    actual_tvvoo = {
        channel.name
        for channel in channels
        if resolver_attributes_for(channel).get("x-resolver") == "tvvoo"
    }
    missing_tvvoo = sorted(expected_tvvoo - actual_tvvoo)
    if missing_tvvoo:
        raise ValueError("faltan canales TvVoo del mapa: " + ", ".join(missing_tvvoo))
    missing_highfly = sorted(
        set(HIGHFLY_RESOLVER_CHANNELS)
        - {
            channel.tvg_id
            for channel in channels
            if resolver_attributes_for(channel).get("x-resolver") == "highfly"
        }
    )
    if missing_highfly:
        raise ValueError("faltan canales Highfly: " + ", ".join(missing_highfly))
    return counts


def validate_resolver_contract(lines: list[str]) -> dict[str, int]:
    validate_resolver_catalog()
    counts = validate_playlist_resolvers(lines)
    print(
        "Contrato de resolutores valido: "
        + ", ".join(f"{engine}={count}" for engine, count in counts.items())
    )
    return counts


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
    data: bytes | None = None,
) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, headers=headers, data=data)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.status, response.read(limit), response.geturl()
    except urllib.error.URLError as error:
        hostname = (urlparse(url).hostname or "").lower()
        reason = str(getattr(error, "reason", error)).lower()
        if (
            context is None
            and hostname in EXPIRED_CERT_FALLBACK_HOSTS
            and "certificate has expired" in reason
        ):
            expired_cert_context = ssl.create_default_context()
            expired_cert_context.check_hostname = False
            expired_cert_context.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(
                request, timeout=timeout, context=expired_cert_context
            ) as response:
                return response.status, response.read(limit), response.geturl()
        raise


def fetch_channel_bytes(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = 25,
) -> tuple[int, bytes, str]:
    return fetch_bytes(url, headers, timeout=timeout)


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
    invalid_duration_channels: set[str] = set()
    first_start: datetime | None = None
    last_stop: datetime | None = None
    for programme in root.findall("programme"):
        channel_id = programme.get("channel", "")
        if channel_id not in expected_ids:
            continue
        start = xmltv_datetime(programme.get("start", ""))
        stop = xmltv_datetime(programme.get("stop", ""))
        if stop <= start:
            invalid_duration_channels.add(channel_id)
            continue
        counts[channel_id] += 1
        intervals_by_channel.setdefault(channel_id, []).append((start, stop))
        previous = last_by_channel.get(channel_id)
        last_by_channel[channel_id] = stop if previous is None or stop > previous else previous
        first_start = start if first_start is None or start < first_start else first_start
        last_stop = stop if last_stop is None or stop > last_stop else last_stop

    if invalid_duration_channels:
        raise ValueError(
            "programas con duracion nula o negativa en la EPG: "
            + ", ".join(sorted(invalid_duration_channels))
        )

    overlapping_channels = []
    for channel_id, intervals in intervals_by_channel.items():
        intervals.sort()
        previous_stop: datetime | None = None
        for start, stop in intervals:
            if previous_stop is not None and start < previous_stop:
                overlapping_channels.append(channel_id)
                break
            previous_stop = stop if previous_stop is None or stop > previous_stop else previous_stop
    validation_warnings: list[str] = []
    if overlapping_channels:
        validation_warnings.append(
            "programas superpuestos en: " + ", ".join(sorted(overlapping_channels))
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
    guide_sources = {
        channel.get("id", ""): channel.get("data-guide-source", "")
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
        "guide_sources": guide_sources,
        "warnings": validation_warnings,
    }


def validate_main_playlist_epg(
    channels: list[Channel],
    *,
    data: bytes | None = None,
    now: datetime | None = None,
) -> dict:
    """Validate the hard EPG gate for the principal public playlist.

    The independent EPG job still builds coverage for the complete catalogue.
    This narrower audit is intentionally run by the channel job as a safety
    gate before replacing ``m3u.m3u``. Technical continuity blocks count as
    coverage so a transient source outage cannot erase a channel's XMLTV ID;
    their explicit ``data-guide`` marker remains visible to the app/report and
    they are never presented as an official programme source.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    principal_channels = [
        channel for channel in channels if playlist_key_for(channel) == "main"
    ]
    missing_id_channels = [channel.name for channel in principal_channels if not channel.tvg_id]
    principal_ids = [channel.tvg_id for channel in principal_channels if channel.tvg_id]
    duplicate_ids = sorted(
        tvg_id
        for tvg_id in set(principal_ids)
        if principal_ids.count(tvg_id) > 1
    )
    expected_ids = set(principal_ids)
    base = {
        "scope": DEFAULT_PLAYLIST.name,
        "required_channels": len(principal_channels),
        "required_ids": sorted(expected_ids),
        "minimum_future_hours": 24,
    }
    if missing_id_channels:
        return {
            **base,
            "ok": False,
            "error": "canales principales sin tvg-id: " + ", ".join(missing_id_channels),
            "channels": 0,
            "programmes": 0,
            "technical_guides": [],
        }
    if duplicate_ids:
        return {
            **base,
            "ok": False,
            "error": "tvg-id duplicados en la lista principal: " + ", ".join(duplicate_ids),
            "channels": 0,
            "programmes": 0,
            "technical_guides": [],
        }
    if not expected_ids:
        return {
            **base,
            "ok": False,
            "error": "la lista principal no contiene canales con tvg-id",
            "channels": 0,
            "programmes": 0,
            "technical_guides": [],
        }
    if data is None:
        try:
            data = EPG_PATH.read_bytes()
        except OSError as error:
            return {
                **base,
                "ok": False,
                "error": f"no se pudo leer {EPG_PATH.name}: {error}",
                "channels": 0,
                "programmes": 0,
                "technical_guides": [],
            }
    try:
        status = epg_status_from_xml(
            data,
            expected_ids,
            now=current,
            minimum_future=timedelta(hours=24),
            allow_empty_ids=set(),
        )
    except (ET.ParseError, ValueError) as error:
        return {
            **base,
            "ok": False,
            "error": str(error),
            "channels": 0,
            "programmes": 0,
            "technical_guides": [],
        }
    technical_guides = sorted(
        channel_id
        for channel_id, guide_type in (status.get("guide_types") or {}).items()
        if "continuidad tecnica" in str(guide_type).lower()
    )
    status.update(base)
    status["technical_guides"] = technical_guides
    status["coverage_percent"] = 100 if status.get("ok") else 0
    return status


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
        try:
            status, body, _ = fetch_bytes(
                LA_RED_PROGRAMMING_PAGE,
                headers,
                timeout=60,
                limit=8_000_000,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
        except Exception as primary_error:
            # Algunos runners reciben un bloqueo transitorio con urllib. Se
            # reintenta la misma pagina oficial con curl, sin cookies, login,
            # tokens ni relajacion TLS. No se cambia la fuente por Zapping.
            try:
                completed = subprocess.run(
                    [
                        "curl",
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--location",
                        "--max-time",
                        "60",
                        "--user-agent",
                        BROWSER_USER_AGENT,
                        "--header",
                        "Accept: text/html,application/xhtml+xml,*/*;q=0.8",
                        "--header",
                        "Accept-Language: es-CL,es;q=0.9,en;q=0.8",
                        "--header",
                        f"Referer: {LA_RED_PROGRAMMING_PAGE}",
                        LA_RED_PROGRAMMING_PAGE,
                    ],
                    check=True,
                    capture_output=True,
                    timeout=65,
                )
                body = completed.stdout
            except Exception as curl_error:
                raise RuntimeError(
                    f"urllib: {type(primary_error).__name__}: {primary_error}; "
                    f"curl oficial: {type(curl_error).__name__}: {curl_error}"
                ) from curl_error

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
    # El JSON oficial puede entregar una tarjeta tardia encima de otra en
    # los cambios de bloque. Conservamos el programa que comienza despues,
    # recortamos solo el borde del anterior y descartamos tarjetas totalmente
    # contenidas; asi la fuente sigue siendo oficial y XMLTV no se solapa.
    ordered_records: list[dict[str, object]] = []
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
        if ordered_records:
            previous = ordered_records[-1]
            previous_start = previous["start"]
            previous_stop = previous["stop"]
            if isinstance(previous_start, datetime) and isinstance(previous_stop, datetime):
                if start < previous_stop:
                    if stop <= previous_stop:
                        continue
                    previous["stop"] = start
                    if start <= previous_start:
                        ordered_records.pop()
        if stop <= start:
            continue
        ordered_records.append(record)

    for record in ordered_records:
        start = record["start"]
        stop = record["stop"]
        title = record["title"]
        if not isinstance(start, datetime) or not isinstance(stop, datetime):
            continue
        if not isinstance(title, str) or stop < lower_limit or start > upper_limit:
            continue
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


def external_epg_datetime(value: object) -> datetime:
    """Parse the ISO timestamps used by the public non-XMLTV sources."""
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def epg_root(source_name: str) -> ET.Element:
    return ET.Element(
        "tv",
        {
            "generator-info-name": "lista-m3u updater",
            "source-info-name": source_name,
        },
    )


def fetch_canal13_main_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the public structured guide used by Canal 13's official player."""
    if not any(channel.tvg_id == "0107" for channel in channels):
        return None, None
    try:
        status, body, _ = fetch_bytes(
            CANAL13_MAIN_EPG_URL,
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
                "Referer": "https://www.13.cl/",
            },
            timeout=45,
            limit=4_000_000,
        )
        if status != 200:
            raise ValueError(f"HTTP {status}")
        payload = json.loads(decode_web_text(body))
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise ValueError("el JSON oficial de Canal 13 no contiene events")

        lower_limit = now - timedelta(hours=6)
        upper_limit = now + timedelta(days=5)
        records: list[dict[str, object]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            try:
                start = external_epg_datetime(event["beginTime"])
                stop = external_epg_datetime(event["endTime"])
            except (KeyError, TypeError, ValueError):
                continue
            if stop <= start or stop <= lower_limit or start >= upper_limit:
                continue
            generic_title = re.sub(
                r"\s+",
                " ",
                html.unescape(str(event.get("title", ""))).strip(),
            )
            episode_title = re.sub(
                r"\s+",
                " ",
                html.unescape(str(event.get("episodeTitle", ""))).strip(),
            )
            title = episode_title or generic_title
            if not title:
                continue
            records.append(
                {
                    "start": start,
                    "stop": stop,
                    "title": title,
                    "synopsis": re.sub(
                        r"\s+",
                        " ",
                        html.unescape(str(event.get("synopsis", ""))).strip(),
                    ),
                    "genre": re.sub(
                        r"\s+",
                        " ",
                        html.unescape(str(event.get("genre", ""))).strip(),
                    ),
                }
            )

        normalized: list[dict[str, object]] = []
        seen: set[tuple[datetime, datetime, str]] = set()
        for record in sorted(records, key=lambda item: item["start"]):
            start = record["start"]
            stop = record["stop"]
            title = record["title"]
            if not isinstance(start, datetime) or not isinstance(stop, datetime):
                continue
            if not isinstance(title, str):
                continue
            key = (start, stop, title)
            if key in seen:
                continue
            seen.add(key)
            if normalized:
                previous = normalized[-1]
                previous_start = previous["start"]
                previous_stop = previous["stop"]
                if (
                    isinstance(previous_start, datetime)
                    and isinstance(previous_stop, datetime)
                    and start < previous_stop
                ):
                    if stop <= previous_stop:
                        continue
                    previous["stop"] = start
                    if start <= previous_start:
                        normalized.pop()
            if stop > start:
                normalized.append(record)

        if len(normalized) < 5:
            raise ValueError("Canal 13 publico una parrilla oficial demasiado corta")
        last_stop = max(
            record["stop"]
            for record in normalized
            if isinstance(record["stop"], datetime)
        )
        if not isinstance(last_stop, datetime) or last_stop < now + timedelta(hours=24):
            raise ValueError("Canal 13 no publico 24 horas futuras")

        root = epg_root("Canal 13 EPG JSON oficial")
        for record in normalized:
            start = record["start"]
            stop = record["stop"]
            title = record["title"]
            if not isinstance(start, datetime) or not isinstance(stop, datetime):
                continue
            if not isinstance(title, str):
                continue
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": xmltv_format_chile(start),
                    "stop": xmltv_format_chile(stop),
                    "channel": "0107",
                },
            )
            ET.SubElement(programme, "title", {"lang": "es"}).text = title
            synopsis = record["synopsis"]
            if isinstance(synopsis, str) and synopsis:
                ET.SubElement(programme, "desc", {"lang": "es"}).text = synopsis
            genre = record["genre"]
            if isinstance(genre, str) and genre:
                ET.SubElement(programme, "category", {"lang": "es"}).text = genre
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_13go_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the public JSON EPG used by the 13Go streams for 13Cultura/13Kids."""
    targets = {
        channel.tvg_id: CANAL13_13GO_EPG_URLS[channel.tvg_id]
        for channel in channels
        if channel.tvg_id in CANAL13_13GO_EPG_URLS
    }
    if not targets:
        return None, None
    try:
        root = epg_root("Canal 13 13Go EPG JSON oficial")
        minimum_start = now - timedelta(hours=6)
        maximum_stop = now + timedelta(days=5)
        counts = {channel_id: 0 for channel_id in targets}
        for channel_id, url in targets.items():
            status, body, _ = fetch_bytes(
                url,
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": "https://old.13go.cl/",
                },
                timeout=45,
                limit=4_000_000,
            )
            if status != 200:
                raise ValueError(f"{channel_id}: HTTP {status}")
            payload = json.loads(decode_web_text(body))
            events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(events, list):
                raise ValueError(f"{channel_id}: el JSON no contiene events")
            source_id = "13cultura" if channel_id == "13Cultura.cl@DPS" else "13kids"
            for event in events:
                if not isinstance(event, dict):
                    continue
                try:
                    start = external_epg_datetime(event["beginTime"])
                    stop = external_epg_datetime(event["endTime"])
                except (KeyError, TypeError, ValueError):
                    continue
                if stop <= minimum_start or start >= maximum_stop or stop <= start:
                    continue
                title = re.sub(r"\s+", " ", str(event.get("title", "")).strip())
                if not title:
                    continue
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
                episode_title = str(event.get("episodeTitle", "")).strip()
                if episode_title and episode_title.casefold() != title.casefold():
                    ET.SubElement(programme, "sub-title", {"lang": "es"}).text = (
                        episode_title
                    )
                synopsis = re.sub(
                    r"\s+", " ", str(event.get("synopsis", "")).strip()
                )
                if synopsis:
                    ET.SubElement(programme, "desc", {"lang": "es"}).text = synopsis
                genre = str(event.get("genre", "")).strip()
                if genre:
                    ET.SubElement(programme, "category", {"lang": "es"}).text = genre
                counts[channel_id] += 1
        missing = [channel_id for channel_id, count in counts.items() if count == 0]
        if missing:
            raise ValueError("13Go sin eventos vigentes: " + ", ".join(missing))
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_sky_official_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the public Sky linear schedule for the four TvVoo Sky channels."""
    targets = {
        channel.tvg_id: SKY_OFFICIAL_EPG_CHANNELS[channel.tvg_id]
        for channel in channels
        if channel.tvg_id in SKY_OFFICIAL_EPG_CHANNELS
    }
    if not targets:
        return None, None
    try:
        root = epg_root("Sky Sports EPG oficial")
        counts = {channel_id: 0 for channel_id in targets}
        seen: set[tuple[str, str, int]] = set()
        start_limit = now - timedelta(hours=6)
        stop_limit = now + timedelta(days=5)
        query_sids = ",".join(sorted(set(targets.values())))
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json,*/*",
            "X-SkyOTT-Territory": "GB",
            "Referer": "https://www.skysports.com/watch/tv-guide",
        }
        for day_offset in range(3):
            schedule_date = (now + timedelta(days=day_offset)).astimezone(timezone.utc).date()
            url = (
                f"{SKY_OFFICIAL_EPG_SCHEDULE_URL}/"
                f"{schedule_date:%Y%m%d}/{query_sids}"
            )
            status, body, _ = fetch_bytes(
                url, headers, timeout=45, limit=8_000_000
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            payload = json.loads(decode_web_text(body))
            schedules = payload.get("schedule") if isinstance(payload, dict) else None
            if not isinstance(schedules, list):
                raise ValueError("Sky no devolvio schedule")
            for schedule in schedules:
                if not isinstance(schedule, dict):
                    continue
                source_id = str(schedule.get("sid", ""))
                target_id = next(
                    (
                        channel_id
                        for channel_id, sid in targets.items()
                        if sid == source_id
                    ),
                    None,
                )
                if target_id is None:
                    continue
                events = schedule.get("events")
                if not isinstance(events, list):
                    continue
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    try:
                        start = datetime.fromtimestamp(
                            int(event["st"]), timezone.utc
                        )
                        stop = start + timedelta(seconds=int(event["d"]))
                    except (KeyError, TypeError, ValueError, OverflowError):
                        continue
                    if stop <= start_limit or start >= stop_limit or stop <= start:
                        continue
                    event_key = (source_id, str(event.get("eid", "")), int(event["st"]))
                    if event_key in seen:
                        continue
                    seen.add(event_key)
                    title = re.sub(r"\s+", " ", str(event.get("t", "")).strip())
                    if not title:
                        continue
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": source_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "en"}).text = title
                    description = re.sub(
                        r"\s+", " ", str(event.get("sy", "")).strip()
                    )
                    if description:
                        ET.SubElement(programme, "desc", {"lang": "en"}).text = description
                    season = event.get("seasonnumber")
                    episode = event.get("episodenumber")
                    if season is not None or episode is not None:
                        episode_element = ET.SubElement(programme, "episode-num", {"system": "onscreen"})
                        episode_element.text = (
                            f"S{int(season):02d}E{int(episode):02d}"
                            if season is not None and episode is not None
                            else str(season if season is not None else episode)
                        )
                    counts[target_id] += 1
        missing = [channel_id for channel_id, count in counts.items() if count == 0]
        if missing:
            raise ValueError("Sky sin eventos vigentes: " + ", ".join(missing))
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_autentic_history_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Resolve Whale TV+'s public frontend token in memory and import its EPG."""
    if not any(channel.tvg_id == "AutenticHistory.de" for channel in channels):
        return None, None
    try:
        page_headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        }
        status, page_body, page_url = fetch_bytes(
            AUTENTIC_HISTORY_PAGE, page_headers, timeout=45, limit=8_000_000
        )
        if status != 200:
            raise ValueError(f"Whale TV+ HTTP {status}")
        page_html = decode_web_text(page_body)
        script_urls = []
        for script_url in re.findall(
            r"<script[^>]+src=[\"']([^\"']+)[\"']", page_html, re.IGNORECASE
        ):
            absolute = urljoin(page_url or AUTENTIC_HISTORY_PAGE, script_url)
            if absolute not in script_urls:
                script_urls.append(absolute)
        api_token = None
        token_patterns = (
            r"apiToken.{0,160}?[\"']([0-9a-f]{32})[\"']",
            r"apiToken.{0,160}?([0-9a-f]{32})",
        )
        for script_url in script_urls:
            try:
                script_status, script_body, _ = fetch_bytes(
                    script_url,
                    {"User-Agent": BROWSER_USER_AGENT, "Accept": "*/*"},
                    timeout=45,
                    limit=12_000_000,
                )
            except Exception:
                continue
            if script_status != 200:
                continue
            script_text = decode_web_text(script_body)
            for pattern in token_patterns:
                match = re.search(pattern, script_text, re.IGNORECASE | re.DOTALL)
                if match:
                    api_token = match.group(1)
                    break
            if api_token:
                break
        if not api_token:
            raise ValueError("Whale TV+ no publico apiToken en sus scripts")
        api_base = "https://rlaxx.zeasn.tv/livetv/api"
        common_headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json,*/*",
            "Origin": "https://watch.whaletvplus.com",
            "Referer": AUTENTIC_HISTORY_PAGE,
        }
        auth_url = f"{api_base}/v1/auth/access?{urlencode({'uuid': '1', 'apiToken': api_token, 'langCode': 'en'})}"
        auth_status, auth_body, _ = fetch_bytes(
            auth_url, common_headers, timeout=45, limit=2_000_000
        )
        if auth_status != 200:
            raise ValueError(f"Whale TV+ auth HTTP {auth_status}")
        auth_payload = json.loads(decode_web_text(auth_body))
        auth_data = auth_payload.get("data") if isinstance(auth_payload, dict) else None
        session_token = auth_data.get("token") if isinstance(auth_data, dict) else None
        if not session_token:
            raise ValueError("Whale TV+ no devolvio token de sesion")
        start_ms = int((now - timedelta(hours=6)).timestamp() * 1000)
        end_ms = int((now + timedelta(days=5)).timestamp() * 1000)
        epg_url = (
            f"{api_base}/device/browser/v1/epg?"
            + urlencode(
                {
                    "channelIds": AUTENTIC_HISTORY_CHANNEL_ID,
                    "startTime": start_ms,
                    "endTime": end_ms,
                }
            )
        )
        epg_headers = dict(common_headers)
        epg_headers["token"] = str(session_token)
        epg_status, epg_body, _ = fetch_bytes(
            epg_url, epg_headers, timeout=45, limit=8_000_000
        )
        if epg_status != 200:
            raise ValueError(f"Whale TV+ EPG HTTP {epg_status}")
        epg_payload = json.loads(decode_web_text(epg_body))
        groups = epg_payload.get("data") if isinstance(epg_payload, dict) else None
        if not isinstance(groups, list):
            raise ValueError("Whale TV+ no devolvio grupos EPG")
        root = epg_root("Whale TV+ EPG publico de Autentic History")
        count = 0
        for group in groups:
            if not isinstance(group, dict):
                continue
            for item in group.get("ptList", []):
                if not isinstance(item, dict):
                    continue
                try:
                    start = datetime.fromtimestamp(int(item["prgStm"]) / 1000, timezone.utc)
                    stop = datetime.fromtimestamp(int(item["prgEtm"]) / 1000, timezone.utc)
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue
                if stop <= start or stop <= now - timedelta(hours=6) or start >= now + timedelta(days=5):
                    continue
                title = re.sub(r"\s+", " ", str(item.get("prgTitle", "")).strip())
                if not title:
                    continue
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": xmltv_format_chile(start),
                        "stop": xmltv_format_chile(stop),
                        "channel": AUTENTIC_HISTORY_CHANNEL_ID,
                    },
                )
                ET.SubElement(programme, "title", {"lang": "en"}).text = title
                count += 1
        if count == 0:
            raise ValueError("Whale TV+ no devolvio programas vigentes")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def fetch_pickx_dazn_epg(
    channels: list[Channel], now: datetime
) -> tuple[bytes | None, str | None]:
    """Import the optional Pickx guide when a channel is configured."""
    targets = {
        channel.tvg_id: PICKX_EPG_CHANNELS[channel.tvg_id]
        for channel in channels
        if channel.tvg_id in PICKX_EPG_CHANNELS
    }
    if not targets:
        return None, None
    try:
        page_status, page_body, _ = fetch_bytes(
            PICKX_EPG_PAGE,
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
            timeout=45,
            limit=12_000_000,
        )
        if page_status != 200:
            raise ValueError(f"Pickx HTTP {page_status}")
        page_html = decode_web_text(page_body)
        hash_match = re.search(r"\"hashes\"\s*:\s*\[\s*\"([^\"]+)\"", page_html)
        if not hash_match:
            raise ValueError("Pickx no publico la version EPG")
        version_status, version_body, _ = fetch_bytes(
            "https://www.pickx.be/api/s-" + hash_match.group(1),
            {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json,*/*"},
            timeout=45,
            limit=1_000_000,
        )
        if version_status != 200:
            raise ValueError(f"Pickx version HTTP {version_status}")
        version_payload = json.loads(decode_web_text(version_body))
        version = version_payload.get("version") if isinstance(version_payload, dict) else None
        if not version:
            raise ValueError("Pickx devolvio una version EPG vacia")
        root = epg_root("Pickx EPG publico de DAZN 1 Francia")
        counts = {channel_id: 0 for channel_id in targets}
        seen_rows: set[tuple[str, str, str]] = set()
        start_limit = now - timedelta(hours=6)
        stop_limit = now + timedelta(days=5)
        for day_offset in range(3):
            schedule_date = (now + timedelta(days=day_offset)).astimezone(timezone.utc).date()
            for channel_id, provider_channel_id in targets.items():
                url = (
                    f"{PICKX_EPG_API_BASE}/{version}/{schedule_date:%Y-%m-%d}/"
                    f"channel/{provider_channel_id}?timezone=Europe%2FBrussels"
                )
                status, body, _ = fetch_bytes(
                    url,
                    {
                        "User-Agent": BROWSER_USER_AGENT,
                        "Accept": "application/json,*/*",
                        "Origin": "https://www.pickx.be",
                        "Referer": PICKX_EPG_PAGE,
                    },
                    timeout=45,
                    limit=8_000_000,
                )
                if status != 200:
                    raise ValueError(f"Pickx {provider_channel_id} HTTP {status}")
                rows = json.loads(decode_web_text(body))
                if not isinstance(rows, list):
                    raise ValueError("Pickx no devolvio una lista de emisiones")
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    try:
                        start = external_epg_datetime(row["programScheduleStart"])
                        stop = external_epg_datetime(row["programScheduleEnd"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if stop <= start_limit or start >= stop_limit or stop <= start:
                        continue
                    program = row.get("program") if isinstance(row.get("program"), dict) else {}
                    title = re.sub(r"\s+", " ", str(program.get("title", "")).strip())
                    if not title:
                        continue
                    row_key = (
                        start.isoformat(),
                        stop.isoformat(),
                        title,
                    )
                    if row_key in seen_rows:
                        continue
                    seen_rows.add(row_key)
                    programme = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": xmltv_format_chile(start),
                            "stop": xmltv_format_chile(stop),
                            "channel": provider_channel_id,
                        },
                    )
                    ET.SubElement(programme, "title", {"lang": "fr"}).text = title
                    episode_title = str(program.get("episodeTitle", "")).strip()
                    if episode_title:
                        ET.SubElement(programme, "sub-title", {"lang": "fr"}).text = episode_title
                    description = re.sub(r"\s+", " ", str(program.get("description", "")).strip())
                    if description:
                        ET.SubElement(programme, "desc", {"lang": "fr"}).text = description
                    category = str(program.get("category", "")).strip()
                    if category:
                        ET.SubElement(programme, "category", {"lang": "fr"}).text = category
                    counts[channel_id] += 1
        missing = [channel_id for channel_id, count in counts.items() if count == 0]
        if missing:
            raise ValueError("Pickx sin emisiones vigentes: " + ", ".join(missing))
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


def fetch_zapping_nowplaying_bytes() -> bytes:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json,*/*",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    primary_error: Exception | None = None
    try:
        status, body, _ = fetch_bytes(
            ZAPPING_NOWPLAYING_URL,
            headers,
            timeout=60,
            limit=4_000_000,
            data=b"data=",
        )
        if status == 200:
            return body
        primary_error = ValueError(f"HTTP {status}")
    except Exception as error:
        primary_error = error

    # El runner ya incluye curl. Los argumentos son fijos, no usan shell y
    # prueban frontales regionales equivalentes sin relajar la verificacion TLS.
    curl_errors: list[str] = []
    for connect_host in ZAPPING_NOWPLAYING_CONNECT_HOSTS:
        try:
            completed = subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--max-time",
                    "30",
                    "--connect-to",
                    f"charly.zappingtv.com:443:{connect_host}:443",
                    "--header",
                    "Content-Type: application/x-www-form-urlencoded",
                    "--data",
                    "data=",
                    ZAPPING_NOWPLAYING_URL,
                ],
                check=True,
                capture_output=True,
                timeout=35,
            )
            if not completed.stdout:
                raise ValueError("nowplaying respondio sin contenido")
            if len(completed.stdout) > 4_000_000:
                raise ValueError("nowplaying excede el limite de 4 MB")
            return completed.stdout
        except Exception as curl_error:
            curl_errors.append(
                f"{connect_host}: {type(curl_error).__name__}: {curl_error}"
            )
    raise RuntimeError(
        f"urllib: {type(primary_error).__name__}: {primary_error}; "
        "curl regional: " + " | ".join(curl_errors)
    )


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

    # El HTML de la guia contiene hoy y manana, pero bloquea por pais a los
    # runners de GitHub. El endpoint publico nowplaying no requiere sesion y
    # entrega pasado inmediato, programa actual y proximos con inicio/fin
    # absolutos. Se consulta una sola vez y se usa solo si falla la pagina
    # completa de un canal.
    nowplaying_blocks: dict[str, list[tuple[datetime, datetime, str]]] = {}
    nowplaying_error: str | None = None
    try:
        body = fetch_zapping_nowplaying_bytes()
        payload = json.loads(body.decode("utf-8"))
        schedule = payload.get("data", {}).get("schedule", {})
        if not isinstance(schedule, dict):
            raise ValueError("nowplaying no contiene un mapa schedule")
        for target_id, alias in targets:
            entry = schedule.get(alias)
            if not isinstance(entry, dict):
                continue
            cards: list[dict] = []
            for key in ("past", "now", "next"):
                value = entry.get(key)
                if isinstance(value, list):
                    cards.extend(card for card in value if isinstance(card, dict))
                elif isinstance(value, dict):
                    cards.append(value)
            unique_cards: dict[tuple[datetime, datetime], str] = {}
            for card in cards:
                try:
                    start = datetime.fromtimestamp(int(card["start_time"]), timezone.utc)
                    stop = datetime.fromtimestamp(int(card["end_time"]), timezone.utc)
                except (KeyError, TypeError, ValueError, OSError):
                    continue
                title = str(card.get("title") or card.get("program_title") or "").strip()
                if not title or stop <= start:
                    continue
                if stop < now - timedelta(hours=6) or start > now + timedelta(days=4):
                    continue
                unique_cards[(start, stop)] = title
            blocks = [
                (start, stop, title)
                for (start, stop), title in sorted(unique_cards.items())
            ]
            if blocks:
                nowplaying_blocks[target_id] = blocks
    except Exception as error:
        nowplaying_error = f"{type(error).__name__}: {error}"

    def fetch_target(
        target_id: str, slug: str
    ) -> tuple[str, list[tuple[datetime, datetime, str]], str | None]:
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

            blocks: list[tuple[datetime, datetime, str]] = []
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
                blocks.append((start, stop, title))
            if not blocks:
                raise ValueError("la guia Zapping no publico bloques utilizables")
            return target_id, blocks, None
        except Exception as error:
            fallback = nowplaying_blocks.get(target_id, [])
            if fallback:
                return target_id, fallback, None
            details = f"{type(error).__name__}: {error}"
            if nowplaying_error:
                details += f"; nowplaying: {nowplaying_error}"
            return target_id, [], details

    # Cada pagina es una fuente independiente. La concurrencia reduce la
    # duracion del unico run de Actions sin mezclar resultados ni permitir que
    # un fallo de otro canal descarte la parrilla valida de TVN3.
    results: dict[str, list[tuple[datetime, datetime, str]]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(targets))) as pool:
        futures = {
            pool.submit(fetch_target, target_id, slug): target_id
            for target_id, slug in targets
        }
        for future in as_completed(futures):
            target_id, blocks, error = future.result()
            if blocks:
                results[target_id] = blocks
            if error:
                errors[target_id] = error

    for target_id, _ in targets:
        for start, stop, title in results.get(target_id, []):
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
            description = (
                "Parrilla publica de Zapping Chile y Simply.TV para TVN3, "
                "senal oficial de TVN."
                if target_id == "1437"
                else "Programacion publica consultada en la guia de Zapping Chile."
            )
            ET.SubElement(programme, "desc", {"lang": "es"}).text = description

    # La fuente es opcional y se selecciona por canal. Una pagina que falle no
    # invalida los bloques validos de las otras paginas; build_epg usa esos
    # bloques y deja el fallback configurado para los canales sin cobertura.
    if not results:
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
    technical: bool = False,
    formatter: Callable[[datetime], str] = xmltv_format_chile,
) -> int:
    day_aligned_technical = technical and start_at is None
    if day_aligned_technical:
        start = now.astimezone(CHILE_TIMEZONE).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
    else:
        start = start_at or (
            now.astimezone(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            - timedelta(days=1)
        )
    stop_limit = now.astimezone(timezone.utc) + timedelta(days=5)
    count = 0
    while start < stop_limit:
        stop = (
            start + timedelta(days=1) - timedelta(minutes=1)
            if day_aligned_technical
            else start + timedelta(hours=6)
        )
        programme = ET.SubElement(
            root,
            "programme",
            {
                "start": formatter(start),
                "stop": formatter(stop),
                "channel": channel_id,
            },
        )
        if technical:
            title = "Live"
            description = ""
        else:
            title, description = CONTINUOUS_PROGRAMME_DETAILS.get(
                channel_name,
                (f"{channel_name} en vivo", "Programacion continua de la senal en vivo."),
            )
        ET.SubElement(programme, "title", {"lang": "es"}).text = title
        if description:
            ET.SubElement(programme, "desc", {"lang": "es"}).text = description
        count += 1
        start = start + timedelta(days=1) if day_aligned_technical else stop
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
        if channel.tvg_id == "1437":
            ET.SubElement(element, "url").text = TVN3_OFFICIAL_PAGE

    source_roots: dict[str, ET.Element] = {}
    for source_name, source_xml in source_documents.items():
        source_root = ET.fromstring(source_xml)
        if source_root.tag != "tv":
            raise ValueError(f"la fuente EPG {source_name} no contiene una raiz <tv>")
        source_roots[source_name] = source_root

    programmes_by_target = {channel_id: 0 for channel_id in expected_ids}
    real_last_stop_by_target: dict[str, datetime] = {}
    guide_sources: dict[str, str] = {}
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
    if CANAL13_MAIN_EPG_SOURCE in source_roots and "0107" in expected_ids:
        for lookup_key, lookup_target in list(source_lookup.items()):
            if lookup_target == "0107":
                source_lookup.pop(lookup_key, None)
        source_lookup[(CANAL13_MAIN_EPG_SOURCE, "0107")] = "0107"
    if MEGA_OFFICIAL_EPG_SOURCE in source_roots and "0105" in expected_ids:
        for lookup_key, lookup_target in list(source_lookup.items()):
            if lookup_target == "0105":
                source_lookup.pop(lookup_key, None)
        source_lookup[(MEGA_OFFICIAL_EPG_SOURCE, "0105")] = "0105"
    if TVN_OFFICIAL_EPG_SOURCE in source_roots and "0104" in expected_ids:
        for lookup_key, lookup_target in list(source_lookup.items()):
            if lookup_target == "0104":
                source_lookup.pop(lookup_key, None)
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
    source_overrides = {
        CANAL13_13GO_EPG_SOURCE: {
            "13Cultura.cl@DPS": "13cultura",
            "13Kids.cl": "13kids",
        },
        SKY_OFFICIAL_EPG_SOURCE: {
            channel_id: sid
            for channel_id, sid in SKY_OFFICIAL_EPG_CHANNELS.items()
        },
        AUTENTIC_HISTORY_EPG_SOURCE: {
            "AutenticHistory.de": AUTENTIC_HISTORY_CHANNEL_ID,
        },
    }
    for source_name, target_mappings in source_overrides.items():
        if source_name not in source_roots:
            continue
        for target_id, source_id in target_mappings.items():
            if target_id not in expected_ids:
                continue
            for lookup_key, lookup_target in list(source_lookup.items()):
                if lookup_target == target_id:
                    source_lookup.pop(lookup_key, None)
            source_lookup[(source_name, source_id)] = target_id

    # Si una fuente opcional por canal desaparece durante una renovación
    # forzada, conservar únicamente la parrilla real vigente de la publicación
    # anterior para ese canal. Nunca se mezcla con una fuente fresca ni se usa
    # para inventar continuidad genérica.
    published_fallback = source_roots.get(PUBLISHED_EPG_FALLBACK_SOURCE)
    if published_fallback is not None:
        fresh_targets: set[str] = set()
        for source_name, source_root in source_roots.items():
            if source_name == PUBLISHED_EPG_FALLBACK_SOURCE:
                continue
            for programme in source_root.findall("programme"):
                target_id = source_lookup.get(
                    (source_name, programme.get("channel", ""))
                )
                if target_id is None:
                    continue
                try:
                    stop = xmltv_datetime(programme.get("stop", ""))
                except ValueError:
                    continue
                if stop > now:
                    fresh_targets.add(target_id)
        fresh_targets.update(
            target_id
            for target_id, cards in red_bull_schedules.items()
            if target_id in expected_ids and cards
        )
        for target_id in expected_ids - fresh_targets - NO_EPG_CHANNEL_IDS:
            if target_id == "0102":
                # La Red queda estrictamente en la fuente oficial. No se
                # recicla una EPG antigua de EPGShare/Zapping como respaldo.
                continue
            source_lookup[(PUBLISHED_EPG_FALLBACK_SOURCE, target_id)] = target_id

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
            forced_title = FORCED_EPG_TITLES.get(target_id)
            if forced_title:
                title_element = copied.find("title")
                if title_element is None:
                    title_element = ET.SubElement(copied, "title", {"lang": "es"})
                title_element.text = forced_title
                for subtitle in copied.findall("sub-title"):
                    copied.remove(subtitle)
            try:
                start = xmltv_datetime(copied.get("start", ""))
                stop = xmltv_datetime(copied.get("stop", ""))
            except ValueError:
                continue
            if stop <= start:
                continue
            copied.set("channel", target_id)
            root.append(copied)
            programmes_by_target[target_id] += 1
            guide_types[target_id] = (
                "parrilla real conservada"
                if source_name == PUBLISHED_EPG_FALLBACK_SOURCE
                else "parrilla real"
            )
            guide_sources[target_id] = source_name
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
            guide_sources[red_bull_id] = "red-bull-oficial"
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
        last_stop = last_stop_by_channel.get(channel_id)
        if count and last_stop is not None and last_stop >= minimum_future:
            continue
        if channel_id in FORCED_EPG_TITLES:
            added = add_continuous_programmes(
                root,
                channel_id,
                channel.name,
                now=now,
                start_at=last_stop if count and last_stop is not None else None,
                technical=False,
            )
            programmes_by_target[channel_id] += added
            guide_types[channel_id] = (
                "parrilla Diego y Glot + continuidad"
                if count
                else "continuidad Diego y Glot"
            )
            if not count:
                guide_sources[channel_id] = "continuidad-diego-y-glot"
            continue
        added = add_continuous_programmes(
            root,
            channel_id,
            channel.name,
            now=now,
            start_at=last_stop if count and last_stop is not None else None,
            technical=True,
        )
        programmes_by_target[channel_id] += added
        guide_types[channel_id] = (
            "parrilla real parcial + continuidad tecnica"
            if count
            else "continuidad tecnica"
        )
        if not count:
            guide_sources[channel_id] = "continuidad-tecnica"

    for channel in root.findall("channel"):
        channel_id = channel.get("id", "")
        channel.set("data-guide", guide_types.get(channel_id, "senal continua"))
        channel.set("data-guide-source", guide_sources.get(channel_id, ""))

    real_stop_candidates = list(real_last_stop_by_target.values())
    if real_stop_candidates:
        next_refresh = max(
            min(real_stop_candidates) - EPG_REFRESH_LEAD,
            now + EPG_REFRESH_LEAD,
        )
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
        allow_empty_ids=EPG_ALLOWED_EMPTY_IDS,
    )
    status["guide_types"] = guide_types
    status["guide_sources"] = guide_sources
    status["real_last_stop_utc"] = {
        channel_id: stop.astimezone(timezone.utc).isoformat()
        for channel_id, stop in real_last_stop_by_target.items()
    }
    return output, status


def refresh_epg(channels: list[Channel], *, force: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    expected_ids = {channel.tvg_id for channel in channels if channel.tvg_id}
    public_ids: set[str] | None = None
    public_playlist_paths = [
        path
        for path in (DEFAULT_PLAYLIST, EXTERNAL_PLAYLIST)
        if path.exists()
    ]
    if CHANNEL_CATALOG_PATH.exists() and public_playlist_paths:
        catalog_ids = {
            channel.tvg_id
            for channel in channels
            if channel.tvg_id
        }
        public_ids: set[str] = set()
        for public_playlist in public_playlist_paths:
            public_ids.update(
                channel.tvg_id
                for channel in parse_channels(
                    public_playlist.read_text(encoding="utf-8-sig").splitlines()
                )
                if channel.tvg_id
            )
        retired_ids = catalog_ids - public_ids
        unknown_public_ids = public_ids - catalog_ids
        print(
            "EPG verificada contra las listas publicas y channel-catalog.m3u: "
            f"{len(public_ids & catalog_ids)} activos, "
            f"{len(retired_ids)} retirados temporalmente; "
            "se procesara el catalogo completo"
        )
        if unknown_public_ids:
            print(
                "  [AVISO] M3U publica contiene IDs fuera del catalogo; "
                "se ignoran para la EPG: "
                + ", ".join(sorted(unknown_public_ids)),
                file=sys.stderr,
            )
    existing_status = None
    existing_data: bytes | None = None
    if EPG_PATH.exists():
        try:
            existing_data = EPG_PATH.read_bytes()
            existing_root = ET.fromstring(existing_data)
            existing_channel_ids = {
                channel.get("id", "") for channel in existing_root.findall("channel")
            }
            missing_existing_ids = expected_ids - existing_channel_ids
            if missing_existing_ids:
                raise ValueError(
                    "la guia publicada no contiene canales del catalogo: "
                    + ", ".join(sorted(missing_existing_ids))
                )
            existing_status = epg_status_from_xml(
                existing_data,
                expected_ids,
                now=now,
                minimum_future=timedelta(hours=24),
                allow_empty_ids=EPG_ALLOWED_EMPTY_IDS,
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

    canal13_main_data, canal13_main_error = fetch_canal13_main_official_epg(
        channels, now
    )
    if canal13_main_data:
        source_documents[CANAL13_MAIN_EPG_SOURCE] = canal13_main_data
    if canal13_main_error:
        source_errors[CANAL13_MAIN_EPG_SOURCE] = canal13_main_error

    canal13_data, canal13_error = fetch_13c_official_epg(channels, now)
    if canal13_data:
        source_documents[CANAL13_13C_OFFICIAL_EPG_SOURCE] = canal13_data
    if canal13_error:
        source_errors[CANAL13_13C_OFFICIAL_EPG_SOURCE] = canal13_error

    canal13go_data, canal13go_error = fetch_13go_epg(channels, now)
    if canal13go_data:
        source_documents[CANAL13_13GO_EPG_SOURCE] = canal13go_data
    if canal13go_error:
        source_errors[CANAL13_13GO_EPG_SOURCE] = canal13go_error

    sky_data, sky_error = fetch_sky_official_epg(channels, now)
    if sky_data:
        source_documents[SKY_OFFICIAL_EPG_SOURCE] = sky_data
    if sky_error:
        source_errors[SKY_OFFICIAL_EPG_SOURCE] = sky_error

    autentic_data, autentic_error = fetch_autentic_history_epg(channels, now)
    if autentic_data:
        source_documents[AUTENTIC_HISTORY_EPG_SOURCE] = autentic_data
    if autentic_error:
        source_errors[AUTENTIC_HISTORY_EPG_SOURCE] = autentic_error

    pickx_data, pickx_error = fetch_pickx_dazn_epg(channels, now)
    if pickx_data:
        source_documents[PICKX_EPG_SOURCE] = pickx_data
    if pickx_error:
        source_errors[PICKX_EPG_SOURCE] = pickx_error

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
            CANAL13_MAIN_EPG_SOURCE,
            CANAL13_13C_OFFICIAL_EPG_SOURCE,
            CANAL13_13GO_EPG_SOURCE,
            SKY_OFFICIAL_EPG_SOURCE,
            AUTENTIC_HISTORY_EPG_SOURCE,
            PICKX_EPG_SOURCE,
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
    if existing_status is not None and existing_data is not None:
        source_documents[PUBLISHED_EPG_FALLBACK_SOURCE] = existing_data

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
    channel: Channel,
    attempts: int | None = None,
    *,
    allow_ci_geo_block: bool = False,
) -> CheckResult:
    policy = channel_check_policy(channel)
    attempt_count = max(1, attempts if attempts is not None else policy.attempts)
    last_error = "respuesta desconocida"
    for attempt in range(attempt_count):
        try:
            status, body, final_url = fetch_channel_bytes(
                channel.url,
                request_headers(channel.name),
                timeout=policy.playlist_timeout,
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
                        request_timeout=policy.playlist_timeout,
                        segment_timeout=policy.segment_timeout,
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
                        if attempt + 1 < attempt_count:
                            time.sleep(policy.retry_delay)
                            continue
                        return CheckResult(channel.name, channel.url, False, last_error)
                    detail += f"; {segment_detail}"
                return CheckResult(channel.name, channel.url, True, detail)
            last_error = f"HTTP {status}, contenido no reconocido"
        except urllib.error.HTTPError as error:
            geo_error_codes = {403}
            if channel.name in APP_HANDLED_CHANNELS:
                geo_error_codes.add(401)
            app_managed_master = (
                channel.name in APP_HANDLED_CHANNELS
                and "/live-stream-playlist/" in channel.url
            )
            if (
                (allow_ci_geo_block or app_managed_master)
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
        if attempt + 1 < attempt_count:
            time.sleep(policy.retry_delay)
    return CheckResult(channel.name, channel.url, False, last_error)


def check_hls_first_segment(
    url: str,
    headers: dict[str, str],
    *,
    initial_body: bytes | None = None,
    initial_final_url: str | None = None,
    depth: int = 0,
    request_timeout: int = 25,
    segment_timeout: int = 25,
) -> tuple[bool, str]:
    """Confirm that an HLS master or media playlist delivers a live segment."""
    if depth > 3:
        return False, "playlist HLS con demasiados niveles"
    try:
        if initial_body is None:
            status, body, final_url = fetch_bytes(
                url,
                headers,
                timeout=request_timeout,
                limit=1_048_576,
            )
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
            return check_hls_first_segment(
                child_url,
                headers,
                depth=depth + 1,
                request_timeout=request_timeout,
                segment_timeout=segment_timeout,
            )
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
                    segment_url,
                    headers,
                    timeout=segment_timeout,
                    limit=64,
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
        if status == 200 and webp_is_valid(body):
            return LogoResult(
                channel.name,
                channel.logo_url,
                True,
                f"WebP valido{source_suffix}",
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


def webp_is_valid(body: bytes) -> bool:
    return (
        len(body) >= 16
        and body[:4] == b"RIFF"
        and body[8:12] == b"WEBP"
        and body[12:16] in {b"VP8 ", b"VP8L", b"VP8X"}
    )


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
    repaired_results: dict[str, CheckResult] | None = None,
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
                channel.tvg_id,
                channel.display_name,
            )
            candidate_result = check_channel(
                candidate, allow_ci_geo_block=allow_ci_geo_block
            )
            if candidate_result.ok:
                lines[channel.url_line] = candidate_url
                repaired.append(channel.name)
                if repaired_results is not None:
                    repaired_results[channel.name] = candidate_result
                print(f"  [REPARADO] {channel.name}: enlace alternativo verificado")
                break
        if channel.name not in repaired:
            print(f"  [SIN REEMPLAZO] {channel.name}: se conserva el enlace para revision manual")
    return repaired


def fresh_24horas_url() -> str:
    html = megamedia_page_html(
        TWENTYFOUR_LIVE_PAGE,
        timeout=CHANNEL_CHECK_POLICIES["direct"].resolver_timeout,
    )
    stream_id_match = re.search(
        r'<a[^>]+class=["\'][^"\']*playertablink[^"\']*active[^"\']*["\']'
        r'[^>]+data-ms=["\']([a-zA-Z0-9]+)["\']',
        html,
        flags=re.IGNORECASE,
    )
    stream_id = stream_id_match.group(1) if stream_id_match else TWENTYFOUR_DEFAULT_ID
    return f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8"


def fresh_meganoticias_url() -> str:
    """Read the current official stream id without requesting its token."""
    html = megamedia_page_html(
        MEGANOTICIAS_LIVE_PAGE,
        timeout=CHANNEL_CHECK_POLICIES["meganoticias"].resolver_timeout,
    )
    stream_id_match = re.search(
        r"var\s+VideoSenalEnVivo\s*=\s*\{.{0,65536}?"
        r"\bid\s*:\s*['\"]([A-Za-z0-9_-]+)",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    stream_id = (
        stream_id_match.group(1)
        if stream_id_match
        else MEGANOTICIAS_DEFAULT_STREAM_ID
    )
    return f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8"


def fetch_highfly_manifest() -> dict:
    """Confirm the configured Highfly manifest without persisting its body."""
    status, body, _ = fetch_bytes(
        HIGHFLY_MANIFEST_URL,
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json",
        },
        timeout=CHANNEL_CHECK_POLICIES["highfly"].resolver_timeout,
        limit=1_048_576,
    )
    if status != 200:
        raise RuntimeError(f"manifest Highfly HTTP {status}")
    try:
        payload = json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError as error:
        raise ValueError(f"manifest Highfly no es JSON valido: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("manifest Highfly no contiene un objeto JSON")
    # El manifiesto describe un addon y puede cambiar de forma; exigir solo
    # sus secciones publicas evita depender de URLs de sesion o de un esquema
    # que no controla este repositorio.
    if not any(key in payload for key in ("resources", "catalogs", "types")):
        raise ValueError("manifest Highfly no parece un manifiesto de canales")
    return payload


def fresh_highfly_stream_urls(
    channel: Channel, *, manifest_verified: bool
) -> Iterable[str]:
    """Return the canonical Highfly leaf for a validated stable slug."""
    slug = HIGHFLY_RESOLVER_CHANNELS.get(channel.tvg_id)
    if not slug:
        raise ValueError(f"no hay slug Highfly para {channel.tvg_id or channel.name}")
    if not manifest_verified:
        raise RuntimeError("manifest Highfly no verificable en esta ejecucion")
    yield f"https://leaf.highfly.dev/m3u/{slug}/live.m3u8"


def load_health_state() -> dict:
    """Read token-free health metadata used for the short validation cache."""
    try:
        state = json.loads(HEALTH_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return state if isinstance(state, dict) else {}


def resolver_url_fingerprint(url: str) -> str:
    """Store only a non-reversible URL fingerprint in persistent state."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def dynamic_validation_is_fresh(
    channel: Channel,
    current_result: CheckResult,
    health_state: dict,
    *,
    now: datetime,
) -> bool:
    """Return whether a successful dynamic URL can be reused briefly.

    The fingerprint prevents a manually changed URL from inheriting the age of
    a previous one. A missing/invalid state always causes a normal renewal.
    """
    if not current_result.ok:
        return False
    resolver = resolver_engine_for(channel)
    ttl = RESOLVER_VALIDATION_TTL.get(resolver)
    if ttl is None:
        return False
    entries = health_state.get("channels", {})
    if not isinstance(entries, dict):
        return False
    entry = entries.get(channel.tvg_id or channel.name)
    if not isinstance(entry, dict):
        return False
    recorded_resolver = entry.get("resolver")
    if recorded_resolver and recorded_resolver != resolver:
        return False
    validated_at = entry.get("last_resolver_validated_at") or entry.get("last_ok_at")
    if not validated_at:
        return False
    try:
        previous = datetime.fromisoformat(str(validated_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=timezone.utc)
    age = now.astimezone(timezone.utc) - previous.astimezone(timezone.utc)
    if age < timedelta(0) or age > ttl:
        return False
    return entry.get("resolver_url_hash") == resolver_url_fingerprint(channel.url)


def iter_fresh_tvvoo_stream_urls(channel_name: str) -> Iterable[str]:
    """Yield current TvVoo HLS URLs lazily, without storing provider tokens."""
    resolver_ids = TVVOO_STREAM_RESOLVER_IDS.get(channel_name)
    if not resolver_ids:
        raise ValueError(f"no hay resolver TvVoo para {channel_name}")
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/json",
    }
    resolver_timeout = CHANNEL_CHECK_POLICIES["tvvoo"].resolver_timeout
    errors: list[str] = []
    yielded = False
    for resolver_id in resolver_ids:
        endpoint = f"{TVVOO_STREAM_BASE_URL}/{resolver_id}.json"
        try:
            status, body, _ = fetch_bytes(
                endpoint,
                headers,
                timeout=resolver_timeout,
                limit=131_072,
            )
            if status != 200:
                raise ValueError(f"HTTP {status}")
            payload = json.loads(body.decode("utf-8", "replace"))
            for stream in payload.get("streams", []):
                stream_url = str(stream.get("url", "")).strip()
                if not stream_url:
                    continue
                yielded = True
                yield stream_url
                parsed = urlparse(stream_url)
                # Algunos nodos HTTPS del proveedor estan entregando un
                # certificado vencido; el mismo JSON publica nodos HTTP que
                # siguen entregando el HLS. Se prueba HTTPS primero y HTTP
                # solo como compatibilidad del stream publico.
                if parsed.scheme.lower() == "https":
                    yield parsed._replace(scheme="http").geturl()
        except Exception as error:
            errors.append(f"{resolver_id}: {type(error).__name__}: {error}")
    if not yielded:
        detail = "; ".join(errors) if errors else "respuesta sin streams"
        raise RuntimeError(f"TvVoo no entrego una URL para {channel_name}: {detail}")


def fresh_tvvoo_stream_urls(channel_name: str) -> list[str]:
    """Return all current TvVoo candidates for diagnostics and compatibility."""
    return list(dict.fromkeys(iter_fresh_tvvoo_stream_urls(channel_name)))


def megamedia_page_html(page_url: str, *, timeout: int = 25) -> str:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": page_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        _, body, _ = fetch_bytes(
            page_url,
            headers,
            timeout=timeout,
            limit=2_097_152,
        )
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
            timeout=timeout,
            limit=2_097_152,
        )
    return body.decode("utf-8", "replace")


def refresh_dynamic_channel(
    channel: Channel,
    fresh_url_factory: Callable[[], str | Iterable[str]],
    *,
    running_in_ci: bool,
    current_result: CheckResult | None = None,
) -> DynamicRefreshOutcome:
    """Renew one dynamic source without mutating shared playlist lines.

    The initial parallel validation is passed in so this worker does not
    request the current URL a second time. A successful candidate is checked
    here and returned to the caller, which applies the URL serially.
    """
    if current_result is None:
        current_result = check_channel(channel, allow_ci_geo_block=running_in_ci)
    state = "OK" if current_result.ok else "FALLO"
    print(f"  [{state}] {channel.name}: {current_result.detail}")

    fresh_candidates: Iterable[str] = ()
    try:
        fresh_result = fresh_url_factory()
        fresh_candidates = (fresh_result,) if isinstance(fresh_result, str) else fresh_result
    except Exception as error:
        print(f"  [AVISO] {channel.name}: no se pudo renovar el enlace oficial: {error}")

    seen: set[str] = set()

    def try_candidate(candidate_url: str) -> DynamicRefreshOutcome | None:
        if candidate_url == channel.url or candidate_url in seen:
            return None
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
            if geo_blocked:
                print(
                    f"  [GEO] {channel.name}: maestro renovado; GitHub Actions no puede "
                    "reproducirlo fuera de Chile"
                )
            else:
                print(f"  [OK] {channel.name}: enlace renovado o respaldo verificado")
            accepted_result = candidate_result
            if geo_blocked:
                accepted_result = CheckResult(
                    channel.name,
                    candidate_url,
                    True,
                    "maestro renovado; Actions no puede probar el segmento fuera de Chile",
                )
            return DynamicRefreshOutcome(
                channel=channel.name,
                resolver=resolver_engine_for(channel),
                accepted=True,
                changed=candidate_url != channel.url,
                skipped=False,
                detail="enlace dinamico renovado y validado",
                resolved_url=candidate_url,
                check_result=accepted_result,
            )
        print(f"  [AVISO] {channel.name}: candidato no usable: {candidate_result.detail}")
        return None

    try:
        for candidate_url in fresh_candidates:
            outcome = try_candidate(candidate_url)
            if outcome is not None:
                return outcome
    except Exception as error:
        print(f"  [AVISO] {channel.name}: fallo al leer candidatos renovados: {error}")

    for candidate_url in KNOWN_STREAM_FALLBACKS.get(channel.name, []):
        outcome = try_candidate(candidate_url)
        if outcome is not None:
            return outcome

    if current_result.ok:
        print(f"  [AVISO] {channel.name}: se conserva el enlace actual")
        return DynamicRefreshOutcome(
            channel=channel.name,
            resolver=resolver_engine_for(channel),
            accepted=True,
            changed=False,
            skipped=False,
            detail="enlace actual validado; no hubo candidato nuevo",
            resolved_url=channel.url,
            check_result=current_result,
        )
    else:
        print(f"  [SIN RESPALDO] {channel.name}: se conserva el enlace fallido para revision")
        return DynamicRefreshOutcome(
            channel=channel.name,
            resolver=resolver_engine_for(channel),
            accepted=False,
            changed=False,
            skipped=False,
            detail="sin candidato dinamico usable",
            check_result=current_result,
        )


def skipped_dynamic_refresh(
    channel: Channel, current_result: CheckResult
) -> DynamicRefreshOutcome:
    """Represent a short-lived cache hit without contacting the resolver."""
    print(
        f"  [CACHE] {channel.name}: enlace {resolver_engine_for(channel)} "
        "validado recientemente; no se renueva"
    )
    return DynamicRefreshOutcome(
        channel=channel.name,
        resolver=resolver_engine_for(channel),
        accepted=current_result.ok,
        changed=False,
        skipped=True,
        detail="validacion dinamica reciente reutilizada",
        resolved_url=channel.url,
        check_result=current_result,
    )


def run_dynamic_refreshes(
    jobs: list[
        tuple[Channel, Callable[[], str | Iterable[str]], CheckResult]
    ],
    *,
    allow_ci_geo_block: bool,
) -> list[DynamicRefreshOutcome]:
    """Run TvVoo, Highfly and official dynamic renewals in isolated pools."""
    if not jobs:
        return []
    grouped: dict[str, list[tuple[Channel, Callable[[], str | Iterable[str]], CheckResult]]] = {}
    for job in jobs:
        grouped.setdefault(resolver_engine_for(job[0]), []).append(job)

    def run_group(
        engine: str,
        group: list[tuple[Channel, Callable[[], str | Iterable[str]], CheckResult]],
    ) -> list[DynamicRefreshOutcome]:
        workers = min(
            max(1, CHANNEL_CHECK_POLICIES.get(engine, CHANNEL_CHECK_POLICIES["direct"]).workers),
            len(group),
        )
        outcomes: list[DynamicRefreshOutcome] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    refresh_dynamic_channel,
                    channel,
                    fresh_url_factory,
                    running_in_ci=allow_ci_geo_block,
                    current_result=current_result,
                ): channel.name
                for channel, fresh_url_factory, current_result in group
            }
            for future in as_completed(futures):
                outcomes.append(future.result())
        return outcomes

    outcomes: list[DynamicRefreshOutcome] = []
    with ThreadPoolExecutor(max_workers=len(grouped)) as phase_pool:
        futures = {
            phase_pool.submit(run_group, engine, group): engine
            for engine, group in grouped.items()
        }
        for future in as_completed(futures):
            outcomes.extend(future.result())
    order = {job[0].name: index for index, job in enumerate(jobs)}
    return sorted(outcomes, key=lambda item: order.get(item.channel, len(order)))


def _verify_channel_group(
    channels: list[Channel], *, allow_ci_geo_block: bool
) -> dict[str, CheckResult]:
    if not channels:
        return {}

    by_resolver: dict[str, list[Channel]] = {}
    for channel in channels:
        by_resolver.setdefault(resolver_engine_for(channel), []).append(channel)

    def verify_resolver_group(
        resolver: str, resolver_channels: list[Channel]
    ) -> dict[str, CheckResult]:
        policy = CHANNEL_CHECK_POLICIES.get(
            resolver, CHANNEL_CHECK_POLICIES["direct"]
        )
        workers = min(policy.workers, len(resolver_channels))
        resolver_results: dict[str, CheckResult] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    check_channel,
                    channel,
                    allow_ci_geo_block=allow_ci_geo_block,
                ): channel
                for channel in resolver_channels
            }
            for future in as_completed(futures):
                result = future.result()
                resolver_results[result.channel] = result
                state = "OK" if result.ok else "FALLO"
                print(f"  [{state}] {result.channel}: {result.detail}")
        return resolver_results

    # Cada lista tiene pools independientes y cada proveedor tiene su propio
    # limite: un retraso de TvVoo/Highfly no consume los workers directos.
    results: dict[str, CheckResult] = {}
    with ThreadPoolExecutor(max_workers=len(by_resolver)) as phase_pool:
        futures = {
            phase_pool.submit(verify_resolver_group, resolver, resolver_channels): resolver
            for resolver, resolver_channels in by_resolver.items()
        }
        for future in as_completed(futures):
            results.update(future.result())
    return results


def verify_all(
    channels: list[Channel], *, allow_ci_geo_block: bool = False
) -> list[CheckResult]:
    """Validate every stream in parallel while isolating the two public lists."""
    if not channels:
        return []
    groups: dict[str, list[Channel]] = {"main": [], "external": []}
    for channel in channels:
        groups.setdefault(playlist_key_for(channel), []).append(channel)

    results: dict[str, CheckResult] = {}
    active_groups = {
        name: group for name, group in groups.items() if group
    }
    with ThreadPoolExecutor(max_workers=len(active_groups)) as phase_pool:
        futures = {
            phase_pool.submit(
                _verify_channel_group,
                group,
                allow_ci_geo_block=allow_ci_geo_block,
            ): name
            for name, group in active_groups.items()
        }
        for future in as_completed(futures):
            results.update(future.result())
    return [results[channel.name] for channel in channels]


def write_report(
    channels: list[Channel],
    results: list[CheckResult],
    tvn_refreshed: bool,
    logo_results: list[LogoResult] | None = None,
    repaired_channels: list[str] | None = None,
    epg_status: dict | None = None,
    *,
    main_epg_status: dict | None = None,
    refreshed_channels: list[str] | None = None,
    dynamic_refresh_status: dict[str, dict] | None = None,
) -> dict:
    """Write a token-free run report and update persistent channel health.

    A channel that exhausts all retries is removed from the public playlist for
    this run, including resolver-managed fallbacks. The canonical catalogue
    retains it for the next run. A systemic outage still blocks publication so
    a runner or provider incident cannot empty a large part of the playlist.
    """

    def safe_detail(value: str) -> str:
        sanitized = re.sub(r"https?://\S+", "[URL omitida]", value)
        sanitized = re.sub(
            r"(?i)\b(access_token|token|serverkey|signature|sig|auth)=\S+",
            r"\1=[omitido]",
            sanitized,
        )
        return sanitized[:500]

    try:
        previous_state = json.loads(HEALTH_STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(previous_state, dict):
            previous_state = {}
    except (OSError, json.JSONDecodeError):
        previous_state = {}
    previous_channels = previous_state.get("channels", {})
    if not isinstance(previous_channels, dict):
        previous_channels = {}

    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    checked_at = generated_at.isoformat().replace("+00:00", "Z")
    refreshed = set(refreshed_channels or [])
    repaired = set(repaired_channels or [])
    dynamic_status = dynamic_refresh_status or {}
    results_by_name = {result.channel: result for result in results}
    health_entries: list[dict] = []
    new_health_channels: dict[str, dict] = {}

    for channel in channels:
        result = results_by_name.get(channel.name)
        key = channel.tvg_id or channel.name
        old = previous_channels.get(key, {})
        if not isinstance(old, dict):
            old = {}
        old_failures = int(old.get("consecutive_failures", 0) or 0)
        attributes = resolver_attributes_for(channel)
        resolver = attributes.get("x-resolver")
        ok = bool(result and result.ok)
        failures = 0 if ok else old_failures + 1

        if ok:
            if old_failures:
                status = "recovered"
            elif channel.name in refreshed or channel.name in repaired:
                status = "renewed"
            else:
                status = "functional"
        else:
            status = "temporarily_unavailable"

        # Un fallo individual no congela las demás fuentes: se retira solo de
        # la M3U pública y permanece en el catálogo canónico. La protección
        # sistémica se calcula más abajo únicamente con fuentes directas;
        # los resolutores tienen enlaces efímeros y pueden fallar en bloque
        # mientras el motor de reproducción sigue siendo recuperable.
        blocking = False
        previous_status = str(old.get("status", "new"))
        last_ok_at = checked_at if ok else old.get("last_ok_at")
        resolver_validated_at = old.get("last_resolver_validated_at")
        resolver_url_hash = old.get("resolver_url_hash")
        if resolver in DYNAMIC_RESOLVER_ENGINES:
            if ok:
                resolver_validated_at = checked_at
                resolver_url_hash = resolver_url_fingerprint(channel.url)
            elif not isinstance(resolver_validated_at, str):
                resolver_validated_at = None
            elif not isinstance(resolver_url_hash, str):
                resolver_url_hash = None
        detail = safe_detail(result.detail if result else "sin resultado de validacion")
        source_host = urlparse(result.url).hostname if result and result.url else None
        playlist_key = playlist_key_for(channel)
        entry = {
            "id": key,
            "name": channel.display_name or channel.name,
            "tvg_id": channel.tvg_id,
            "group": channel.group,
            "playlist": playlist_key,
            "resolver": resolver or "direct",
            "test_candidate": is_direct_probe(channel),
            "source_host": source_host,
            "status": status,
            "previous_status": previous_status,
            "status_changed": previous_status != status,
            "ok": ok,
            "blocking": blocking,
            "consecutive_failures": failures,
            "last_checked_at": checked_at,
            "last_ok_at": last_ok_at,
            "detail": detail,
        }
        if resolver in DYNAMIC_RESOLVER_ENGINES:
            entry.update(
                {
                    "last_resolver_validated_at": resolver_validated_at,
                    "resolver_url_hash": resolver_url_hash,
                }
            )
        health_entries.append(entry)
        health_entry = {
            field: entry[field]
            for field in (
                "name",
                "tvg_id",
                "group",
                "playlist",
                "resolver",
                "status",
                "consecutive_failures",
                "last_checked_at",
                "last_ok_at",
            )
        }
        if resolver in DYNAMIC_RESOLVER_ENGINES:
            health_entry.update(
                {
                    "last_resolver_validated_at": resolver_validated_at,
                    "resolver_url_hash": resolver_url_hash,
                }
            )
        new_health_channels[key] = health_entry

    current_ids = set(new_health_channels)
    removed_channels = [
        {
            "id": key,
            "name": str(value.get("name", key)) if isinstance(value, dict) else key,
            "previous_status": (
                str(value.get("status", "unknown"))
                if isinstance(value, dict)
                else "unknown"
            ),
        }
        for key, value in previous_channels.items()
        if key not in current_ids
    ]

    health_state = {
        "schema": 1,
        "updated_at": checked_at,
        "failure_threshold": HEALTH_FAILURE_THRESHOLD,
        "channels": new_health_channels,
    }
    HEALTH_STATE_PATH.write_text(
        json.dumps(health_state, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    logos = logo_results or []
    main_epg = main_epg_status if main_epg_status is not None else (epg_status or {})
    direct_entries = [
        entry
        for entry in health_entries
        if entry["resolver"] == "direct" and not entry["test_candidate"]
    ]
    direct_failures = [entry for entry in direct_entries if not entry["ok"]]
    direct_probe_entries = [
        entry for entry in health_entries if entry["test_candidate"]
    ]
    direct_probe_failures = [
        entry for entry in direct_probe_entries if not entry["ok"]
    ]
    systemic_threshold = max(5, (len(direct_entries) + 3) // 4)
    systemic_direct_failure = len(direct_failures) >= systemic_threshold

    main_entries = [entry for entry in health_entries if entry["playlist"] == "main"]
    external_entries = [
        entry for entry in health_entries if entry["playlist"] == "external"
    ]
    main_working_entries = [entry for entry in main_entries if entry["ok"]]
    external_working_entries = [entry for entry in external_entries if entry["ok"]]
    main_epg_ok = bool(main_epg.get("ok"))
    channel_by_name = {channel.name: channel for channel in channels}
    logo_failures_by_playlist = {"main": [], "external": []}
    for result in logos:
        if result.ok:
            continue
        channel = channel_by_name.get(result.channel)
        key = playlist_key_for(channel) if channel else "main"
        logo_failures_by_playlist.setdefault(key, []).append(result.channel)
    main_logo_failures = sorted(logo_failures_by_playlist.get("main", []))
    external_logo_failures = sorted(logo_failures_by_playlist.get("external", []))

    # The 25% direct-source guard applies only to the principal list. An
    # outage in the external resolver pool must not hide otherwise healthy
    # direct/official channels, and the two outputs are published separately.
    if systemic_direct_failure:
        for entry in main_entries:
            if not entry["ok"]:
                entry["blocking"] = True

    main_hold_reason = None
    if systemic_direct_failure:
        main_hold_reason = "systemic_direct_failure"
    elif not main_epg_ok:
        main_hold_reason = "epg_incomplete"
    elif main_logo_failures:
        main_hold_reason = "logo_validation"
    elif not main_working_entries:
        main_hold_reason = "no_working_channels"

    external_hold_reason = None
    if external_logo_failures:
        external_hold_reason = "logo_validation"
    elif external_entries and not external_working_entries:
        external_hold_reason = "no_working_channels"

    for entry in health_entries:
        is_main = entry["playlist"] == "main"
        if is_main and systemic_direct_failure:
            entry["published"] = None
            entry["publication_action"] = "unchanged_systemic_guard"
        elif is_main and not main_epg_ok and entry["ok"]:
            entry["published"] = False
            entry["publication_action"] = "held_missing_epg"
        elif is_main and main_logo_failures and entry["ok"]:
            entry["published"] = False
            entry["publication_action"] = "held_logo_validation"
        elif is_main and not main_working_entries and entry["ok"]:
            entry["published"] = False
            entry["publication_action"] = "held_no_working_channels"
        elif is_main and entry["test_candidate"]:
            # Estas entradas se mantienen expresamente para la prueba manual
            # solicitada, aunque el chequeo automatico no logre llegar al
            # primer segmento. No cuentan para el guard de salud directa.
            entry["published"] = True
            entry["publication_action"] = "manual_test_candidate"
        elif not is_main and external_logo_failures and entry["ok"]:
            entry["published"] = False
            entry["publication_action"] = "held_logo_validation"
        elif not is_main and not external_working_entries and entry["ok"]:
            entry["published"] = False
            entry["publication_action"] = "held_no_working_channels"
        elif entry["ok"]:
            entry["published"] = True
            entry["publication_action"] = (
                "reactivated"
                if entry["previous_status"] in {
                    "intermittent",
                    "temporarily_unavailable",
                    "resolver_required",
                }
                else "published"
            )
        else:
            entry["published"] = False
            entry["publication_action"] = "temporarily_removed"

    blocking_failures = [entry for entry in health_entries if entry["blocking"]]
    degraded_channels = [
        entry
        for entry in health_entries
        if not entry["ok"] and entry["resolver"] != "direct"
    ]
    status_counts: dict[str, int] = {}
    for entry in health_entries:
        status = str(entry["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    logo_entries = [
        {
            "channel": result.channel,
            "ok": result.ok,
            "detail": safe_detail(result.detail),
        }
        for result in logos
    ]
    main_epg_types = main_epg.get("guide_types") or {}
    main_epg_covered = len(
        set(main_epg_types).intersection(
            {entry["tvg_id"] for entry in main_entries if entry["tvg_id"]}
        )
    )
    main_epg_coverage = round(
        100 * main_epg_covered / len(main_entries), 2
    ) if main_entries else 0
    main_ready = bool(
        main_entries
        and main_working_entries
        and main_epg_ok
        and not main_logo_failures
        and not systemic_direct_failure
    )
    external_ready = bool(
        external_entries
        and external_working_entries
        and not external_logo_failures
    )
    resolver_refresh_summary = {
        "attempted": sum(
            1
            for status in dynamic_status.values()
            if status.get("status") not in {"skipped_recent"}
        ),
        "skipped_recent": sum(
            1
            for status in dynamic_status.values()
            if status.get("status") == "skipped_recent"
        ),
        "changed": sum(
            1 for status in dynamic_status.values() if status.get("changed")
        ),
        "accepted": sum(
            1 for status in dynamic_status.values() if status.get("accepted")
        ),
        "failed": sum(
            1
            for status in dynamic_status.values()
            if status.get("status") == "failed"
        ),
        "by_engine": {},
    }
    for status in dynamic_status.values():
        engine = str(status.get("resolver", "unknown"))
        engine_summary = resolver_refresh_summary["by_engine"].setdefault(
            engine,
            {"attempted": 0, "skipped_recent": 0, "changed": 0, "failed": 0},
        )
        if status.get("status") == "skipped_recent":
            engine_summary["skipped_recent"] += 1
        else:
            engine_summary["attempted"] += 1
        if status.get("changed"):
            engine_summary["changed"] += 1
        if status.get("status") == "failed":
            engine_summary["failed"] += 1
    playlists = {
        "main": {
            "file": DEFAULT_PLAYLIST.name,
            "candidate_channels": len(main_entries),
            "working_channels": len(main_working_entries),
            "published_channels": sum(
                1
                for entry in main_entries
                if entry["published"] is True
            ),
            "epg_required": True,
            "epg_ok": main_epg_ok,
            "epg_covered_channels": main_epg_covered,
            "epg_coverage_percent": main_epg_coverage,
            "epg_programmes": main_epg.get("programmes", 0),
            "technical_guides": main_epg.get("technical_guides", []),
            "publication_ready": main_ready,
            "hold_reason": main_hold_reason,
            "logo_failures": main_logo_failures,
        },
        "external": {
            "file": EXTERNAL_PLAYLIST.name,
            "candidate_channels": len(external_entries),
            "working_channels": len(external_working_entries),
            "published_channels": sum(
                1
                for entry in external_entries
                if entry["published"] is True
            ),
            "epg_required": False,
            "epg_ok": None,
            "publication_ready": external_ready,
            "hold_reason": external_hold_reason,
            "logo_failures": external_logo_failures,
        },
    }
    report = {
        "playlist": DEFAULT_PLAYLIST.name,
        "generated_at": checked_at,
        "tvn_refreshed": tvn_refreshed,
        "refreshed_channels": refreshed_channels or [],
        "resolver_refresh": resolver_refresh_summary,
        "repaired_channels": repaired_channels or [],
        "all_ok": (
            not direct_failures
            and not degraded_channels
            and all(result.ok for result in logos)
            and main_epg_ok
        ),
        "publication_ready": main_ready and external_ready,
        "playlists": playlists,
        "main_epg": main_epg,
        "summary": {
            "total_channels": len(health_entries),
            "blocking_failures": len(blocking_failures),
            "direct_failures": len(direct_failures),
            "direct_probe_candidates": len(direct_probe_entries),
            "direct_probe_failures": len(direct_probe_failures),
            "resolver_degradations": len(degraded_channels),
            "systemic_direct_failure": systemic_direct_failure,
            "systemic_direct_failure_threshold": systemic_threshold,
            "published_channels": sum(
                1 for entry in health_entries if entry["published"] is True
            ),
            "temporarily_removed": sum(
                1
                for entry in health_entries
                if entry["publication_action"] == "temporarily_removed"
            ),
            "held_channels": sum(
                1
                for entry in health_entries
                if str(entry["publication_action"]).startswith("held_")
            ),
            "reactivated": sum(
                1
                for entry in health_entries
                if entry["publication_action"] == "reactivated"
            ),
            "main_epg_ok": main_epg_ok,
            "main_epg_coverage_percent": main_epg_coverage,
            "main_publication_ready": main_ready,
            "external_publication_ready": external_ready,
            "removed_since_previous_run": len(removed_channels),
            "resolver_refresh_attempted": resolver_refresh_summary["attempted"],
            "resolver_refresh_skipped_recent": resolver_refresh_summary[
                "skipped_recent"
            ],
            "resolver_refresh_changed": resolver_refresh_summary["changed"],
            "status_counts": status_counts,
        },
        "epg": epg_status or {},
        "channels": health_entries,
        "blocking_failures": blocking_failures,
        "direct_failures": direct_failures,
        "direct_probe_candidates": direct_probe_entries,
        "direct_probe_failures": direct_probe_failures,
        "degraded_channels": degraded_channels,
        "temporarily_removed": [
            entry
            for entry in health_entries
            if entry["publication_action"] == "temporarily_removed"
        ],
        "removed_channels": removed_channels,
        "logos": logo_entries,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return report


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


def sync_short_playlist_aliases() -> list[Path]:
    """Keep the official one-character playlist aliases byte-for-byte current."""
    changed: list[Path] = []
    for canonical, alias in SHORT_PLAYLIST_ALIASES:
        if not canonical.is_file():
            raise RuntimeError(f"falta la lista canonica para el alias: {canonical.name}")
        content = canonical.read_bytes()
        if alias.is_file() and alias.read_bytes() == content:
            continue
        temporary = alias.with_name(f".{alias.name}.tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(alias)
        finally:
            if temporary.exists():
                temporary.unlink()
        changed.append(alias)
    if changed:
        print(
            "Alias cortos oficiales sincronizados: "
            + ", ".join(path.name for path in changed)
        )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--verify-published", metavar="URL")
    parser.add_argument("--verify-epg-published", metavar="URL")
    parser.add_argument(
        "--sync-resolver-contract",
        action="store_true",
        help="genera metadatos M3U y resolver-catalog.json sin usar la red",
    )
    parser.add_argument(
        "--validate-resolvers-only",
        action="store_true",
        help="valida el contrato M3U/catalogo sin actualizar streams ni EPG",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--refresh-epg-only",
        action="store_true",
        help="fuerza y publica solo la EPG sobre el catalogo completo",
    )
    mode_group.add_argument(
        "--channels-only",
        action="store_true",
        help="actualiza solo canales, resolutores y salud; no toca la EPG",
    )
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

    source_playlist = (
        CHANNEL_CATALOG_PATH
        if playlist == DEFAULT_PLAYLIST.resolve() and CHANNEL_CATALOG_PATH.exists()
        else playlist
    )
    lines = source_playlist.read_text(encoding="utf-8-sig").splitlines()
    if args.refresh_epg_only:
        epg_playlist = (
            CHANNEL_CATALOG_PATH
            if playlist == DEFAULT_PLAYLIST.resolve() and CHANNEL_CATALOG_PATH.exists()
            else playlist
        )
        channels = parse_channels(
            epg_playlist.read_text(encoding="utf-8-sig").splitlines()
        )
        if not channels:
            raise RuntimeError("el catalogo no contiene canales para la EPG")
        epg_status = refresh_epg(channels, force=True)
        print(
            f"EPG actualizada: {epg_status['channels']} canales y "
            f"{epg_status['programmes']} programas"
        )
        return 0
    if args.validate_resolvers_only:
        validate_resolver_contract(lines)
        return 0
    if args.sync_resolver_contract:
        resolver_changed = pin_resolver_metadata(lines)
        if resolver_changed:
            source_playlist.write_text(
                "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
            )
        write_resolver_catalog()
        validate_resolver_contract(lines)
        return 0

    content_order_changed = order_channels_by_content(lines)
    epg_url_changed = ensure_playlist_epg_url(lines)
    if epg_url_changed:
        source_playlist.write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
        if epg_url_changed:
            print("Cabecera M3U enlazada a la guia EPG publicada en GitHub")
    news_order_changed = pin_news_channel_order(lines)
    preferred_logo_changed = pin_preferred_logos(lines)
    resolver_changed = pin_resolver_metadata(lines)
    if content_order_changed or news_order_changed or preferred_logo_changed or resolver_changed:
        source_playlist.write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
        print("Cambios de lista y maestros originales guardados")
    write_resolver_catalog()
    validate_resolver_contract(lines)
    channels = parse_channels(lines)
    if not channels:
        raise RuntimeError("la lista no contiene canales activos")

    if args.channels_only:
        main_epg_status = validate_main_playlist_epg(channels)
        epg_status = dict(main_epg_status)
        epg_status.update(
            {
                "updated": False,
                "skipped": True,
                "catalog_scope": CHANNEL_CATALOG_PATH.name,
            }
        )
        print(
            "EPG omitida: este proceso mantiene canales y resolutores; "
            "la EPG se ejecuta de forma independiente sobre channel-catalog.m3u"
        )
        if main_epg_status.get("ok"):
            print(
                "  [OK] Compuerta EPG de m3u.m3u: cobertura 100% para "
                f"{main_epg_status['required_channels']} canales"
            )
        else:
            print(
                "  [AVISO] Compuerta EPG de m3u.m3u cerrada: "
                + str(main_epg_status.get("error", "cobertura incompleta")),
                file=sys.stderr,
            )
    else:
        print("Actualizando la guia de programacion de todos los canales")
        force_epg_refresh = os.environ.get("EPG_FORCE_REFRESH", "").lower() == "true"
        epg_status = refresh_epg(channels, force=force_epg_refresh)
        main_epg_status = validate_main_playlist_epg(channels)
        updated = "actualizada" if epg_status.get("updated") else "vigente"
        print(
            f"  [OK] EPG {updated}: {epg_status['channels']} canales y "
            f"{epg_status['programmes']} programas"
        )
        for channel in channels:
            guide_type = epg_status.get("guide_types", {}).get(channel.tvg_id, "sin datos")
            print(f"  [EPG] {channel.name}: {guide_type}")
        for warning in epg_status.get("warnings", []):
            print(f"  [AVISO] EPG: {warning}", file=sys.stderr)
        if not main_epg_status.get("ok"):
            print(
                "  [AVISO] Compuerta EPG de m3u.m3u cerrada: "
                + str(main_epg_status.get("error", "cobertura incompleta")),
                file=sys.stderr,
            )

    print(
        f"Revisando {len(channels)} candidatos de {source_playlist.name} "
        f"para publicar {playlist.name}"
    )
    running_in_ci = os.environ.get("CI", "").lower() == "true"
    allow_geo_restricted = running_in_ci or (
        os.environ.get("M3U_ALLOW_GEO_RESTRICTED", "").lower() == "true"
    )
    print("Validacion paralela inicial de fuentes directas y resolutores")
    initial_results = verify_all(
        channels, allow_ci_geo_block=allow_geo_restricted
    )
    results_by_name = {result.channel: result for result in initial_results}
    previous_health_state = load_health_state()
    validation_now = datetime.now(timezone.utc)

    # Primero se decide que necesita renovar cada canal. Si una corrida manual
    # se repite poco despues de otra, una URL dinamica ya comprobada se
    # conserva; si fallo o supero su TTL, vuelve a consultarse el proveedor.
    dynamic_jobs: list[
        tuple[Channel, Callable[[], str | Iterable[str]], CheckResult]
    ] = []
    dynamic_outcomes: list[DynamicRefreshOutcome] = []
    cached_dynamic_names: set[str] = set()
    highfly_channels_needing_refresh: list[Channel] = []
    for channel in channels:
        resolver = resolver_engine_for(channel)
        if resolver not in DYNAMIC_RESOLVER_ENGINES:
            continue
        current_result = results_by_name[channel.name]
        if dynamic_validation_is_fresh(
            channel,
            current_result,
            previous_health_state,
            now=validation_now,
        ):
            dynamic_outcomes.append(
                skipped_dynamic_refresh(channel, current_result)
            )
            cached_dynamic_names.add(channel.name)
            continue
        if resolver == "highfly":
            highfly_channels_needing_refresh.append(channel)

    highfly_manifest_verified = False
    if highfly_channels_needing_refresh:
        try:
            fetch_highfly_manifest()
            highfly_manifest_verified = True
            print(
                f"  [OK] Highfly: manifest verificado para "
                f"{len(highfly_channels_needing_refresh)} canales"
            )
        except Exception as error:
            print(
                f"  [AVISO] Highfly: no se pudo verificar el manifest; "
                f"se conservaran los enlaces actuales si siguen funcionando: {error}"
            )

    for channel in channels:
        resolver = resolver_engine_for(channel)
        if resolver not in DYNAMIC_RESOLVER_ENGINES:
            continue
        current_result = results_by_name[channel.name]
        if channel.name in cached_dynamic_names:
            continue
        if resolver == "tvvoo":
            fresh_url_factory = lambda channel_name=channel.name: iter_fresh_tvvoo_stream_urls(
                channel_name
            )
        elif resolver == "meganoticias":
            fresh_url_factory = fresh_meganoticias_url
        elif resolver == "highfly":
            fresh_url_factory = lambda channel=channel: fresh_highfly_stream_urls(
                channel,
                manifest_verified=highfly_manifest_verified,
            )
        else:
            continue
        dynamic_jobs.append((channel, fresh_url_factory, current_result))

    dynamic_outcomes.extend(
        run_dynamic_refreshes(
            dynamic_jobs,
            allow_ci_geo_block=allow_geo_restricted,
        )
    )
    dynamic_outcomes_by_name = {
        outcome.channel: outcome for outcome in dynamic_outcomes
    }
    refreshed_channels: list[str] = []
    for channel in channels:
        outcome = dynamic_outcomes_by_name.get(channel.name)
        if outcome is None:
            continue
        if outcome.check_result is not None:
            results_by_name[channel.name] = outcome.check_result
        if outcome.changed and outcome.resolved_url:
            lines[channel.url_line] = outcome.resolved_url
            refreshed_channels.append(channel.name)

    refresh_changed = bool(refreshed_channels)
    if refresh_changed:
        source_playlist.write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
    tvn_refreshed = "TVN" in refreshed_channels

    print(
        "Validacion de resolutores completada; no se repite la comprobacion "
        "de los candidatos ya validados"
    )
    final_lines = list(lines)
    final_channels = parse_channels(final_lines)
    results = [results_by_name[channel.name] for channel in final_channels]
    repaired_results: dict[str, CheckResult] = {}
    repaired_channels = repair_failed_channels(
        final_lines,
        final_channels,
        results,
        allow_ci_geo_block=allow_geo_restricted,
        repaired_results=repaired_results,
    )
    if repaired_channels:
        source_playlist.write_text(
            "\n".join(final_lines) + "\n", encoding="utf-8", newline="\n"
        )
        final_lines = list(final_lines)
        final_channels = parse_channels(final_lines)
        results_by_name.update(repaired_results)
        results = [results_by_name[channel.name] for channel in final_channels]

    dynamic_refresh_status = {
        outcome.channel: {
            "resolver": outcome.resolver,
            "status": (
                "skipped_recent"
                if outcome.skipped
                else (
                    "failed"
                    if not outcome.accepted
                    else ("renewed" if outcome.changed else "validated")
                )
            ),
            "accepted": outcome.accepted,
            "changed": outcome.changed,
        }
        for outcome in dynamic_outcomes
    }

    print("Verificacion de logos")
    logo_results = verify_logos(final_channels)
    report = write_report(
        final_channels,
        results,
        tvn_refreshed,
        logo_results,
        repaired_channels,
        epg_status,
        main_epg_status=main_epg_status,
        refreshed_channels=refreshed_channels,
        dynamic_refresh_status=dynamic_refresh_status,
    )
    working_names = {result.channel for result in results if result.ok}
    main_publication = report["playlists"]["main"]
    external_publication = report["playlists"]["external"]
    main_probe_names = {
        channel.name
        for channel in final_channels
        if playlist_key_for(channel) == "main" and is_direct_probe(channel)
    }
    main_working_names = {
        channel.name
        for channel in final_channels
        if playlist_key_for(channel) == "main" and channel.name in working_names
    } | main_probe_names
    external_working_names = {
        channel.name
        for channel in final_channels
        if playlist_key_for(channel) == "external" and channel.name in working_names
    }
    if main_publication["publication_ready"]:
        public_lines = filter_playlist_to_working_channels(
            final_lines, final_channels, main_working_names
        )
        playlist.write_text(
            "\n".join(public_lines) + "\n", encoding="utf-8", newline="\n"
        )
        print(
            f"M3U principal: {len(main_working_names)} canales activos; "
            f"EPG 100% validada sobre {main_publication['candidate_channels']} candidatos"
        )
    else:
        print(
            "M3U principal conservada sin reemplazo: "
            + str(main_publication.get("hold_reason", "validacion incompleta")),
            file=sys.stderr,
        )
    if external_publication["publication_ready"]:
        external_lines = filter_playlist_to_working_channels(
            final_lines, final_channels, external_working_names
        )
        EXTERNAL_PLAYLIST.write_text(
            "\n".join(external_lines) + "\n", encoding="utf-8", newline="\n"
        )
        print(
            f"M3U externa: {len(external_working_names)} canales activos; "
            f"catalogo de reintento: {external_publication['candidate_channels']} candidatos"
        )
    else:
        print(
            "M3U externa conservada sin reemplazo: "
            + str(external_publication.get("hold_reason", "validacion incompleta")),
            file=sys.stderr,
        )
    sync_short_playlist_aliases()
    failed = [entry["name"] for entry in report["blocking_failures"]]
    direct_failed = [entry["name"] for entry in report["direct_failures"]]
    direct_probe_failed = [
        entry["name"] for entry in report["direct_probe_failures"]
    ]
    degraded = [entry["name"] for entry in report["degraded_channels"]]
    failed_logos = [result.channel for result in logo_results if not result.ok]
    epg_failed = not bool(main_epg_status.get("ok"))
    if degraded:
        print(
            "Respaldos degradados retirados temporalmente; el resolutor y el "
            "catalogo los volveran a intentar: "
            + ", ".join(degraded),
            file=sys.stderr,
        )
    if direct_failed:
        print(
            "Canales directos retirados temporalmente de la M3U publica: "
            + ", ".join(direct_failed),
            file=sys.stderr,
        )
    if direct_probe_failed:
        print(
            "Sondas directas de Sky conservadas para prueba manual aunque el "
            "chequeo automatico fallo: "
            + ", ".join(direct_probe_failed),
            file=sys.stderr,
        )
    if failed or failed_logos or epg_failed:
        if failed:
            print("Canales directos con problemas: " + ", ".join(failed), file=sys.stderr)
        if failed_logos:
            print("Logos con problemas: " + ", ".join(failed_logos), file=sys.stderr)
        if epg_failed:
            print(
                "La EPG de la lista principal no supero la compuerta; "
                "se conserva la salida anterior",
                file=sys.stderr,
            )
    if not main_publication["publication_ready"] and not external_publication[
        "publication_ready"
    ]:
        print(
            "Ninguna de las dos listas pudo publicarse de forma segura; "
            "se conservaron las salidas anteriores",
            file=sys.stderr,
        )
        return 1
    working = sum(1 for result in results if result.ok)
    print(
        f"Catalogo verificado: {working} canales activos y "
        f"{len(results) - working} retirados temporalmente "
        f"({len(results)} candidatos conservados)"
    )
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
