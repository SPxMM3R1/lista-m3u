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
from urllib.parse import quote, urlencode, urljoin, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_PLAYLIST = Path(__file__).with_name("m3u.m3u")
EPG_PATH = Path(__file__).with_name("epg.xml")
REPORT_PATH = Path(__file__).with_name("channel-status.json")
PUBLIC_RAW_BASE = "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main"
EPG_PUBLIC_URL = f"{PUBLIC_RAW_BASE}/epg.xml"
CUSTOM_HLS_DIR = Path(__file__).with_name("custom-hls")
CUSTOM_HLS_PUBLIC_BASE = f"{PUBLIC_RAW_BASE}/custom-hls"
NHK_MASTER_URL = "https://masterpl.hls.nhkworld.jp/hls/w/live/smarttv.m3u8"
FRANCE24_ES_1080_URL = (
    "https://live.france24.com/hls/live/2037220/F24_ES_HI_HLS/master_5000.m3u8"
)
EPG_SOURCES = {
    "cl": "https://epgshare01.online/epgshare01/epg_ripper_CL1.xml.gz",
    "es": "https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz",
    "fr": "https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
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
    "NHKWorldJapan.jp": ("cl", "Canal.NHK.World.cl"),
    "AlJazeera.qa": ("es", "Al.Jazeera.English.es"),
    "MeganoticiasAhora.cl": ("tecnocentro", "LCH7159"),
    "0124": ("tecnocentro", "LCH6525"),
    "1153": ("tecnocentro", "LCH7017"),
    "45": ("tecnocentro", "LCH4087"),
}
TECNOCENTRO_EPG_URL = "https://tecnocentro.cl/"
try:
    CHILE_TIMEZONE = ZoneInfo("America/Santiago")
except ZoneInfoNotFoundError:
    CHILE_TIMEZONE = timezone(timedelta(hours=-4))
RED_BULL_EPG_PAGE = "https://www.redbull.tv/es_CL/epg"
RED_BULL_CHANNEL_ID = "rrn:content:video-channels:c81f8686-ab67-4965-ba04-5f6658bb96cc"
# Red Bull personaliza la parrilla por IP; GitHub Actions se ejecuta fuera de
# Chile, asi que enviamos una IP publica chilena para conservar la parrilla local.
RED_BULL_CHILE_GEO_IP = "186.67.0.1"
EPG_REFRESH_INTERVAL = timedelta(hours=12)
TVN_LIVE_PAGE = "https://live.tvn.cl/"
TVN_DEFAULT_ID = "57a498c4d7b86d600e5461cb"
TVN_ALTERNATIVE_URL = "https://iptv2.intersurtv.cl/TVN/index.m3u8?PlaylistM3UCL"
TWENTYFOUR_LIVE_PAGE = "https://www.24horas.cl/envivo"
TWENTYFOUR_DEFAULT_ID = "57d1a22064f5d85712b20dab"
MEGA_LIVE_PAGE = "https://www.mega.cl/senal-en-vivo/"
MEGA_SOURCE_MASTER_URL = (
    "https://tr.live.clarovtrcdn.vtrplay.com/megahdchi/"
    "vxfmt=dp/playlist.m3u8?device_profile=STB_HLS_VCAS_LIVE_HD"
)
MEGANOTICIAS_LIVE_PAGE = "https://www.meganoticias.cl/senal-en-vivo/meganoticias/"
MEGAMEDIA_API_URL = "https://api.mega.cl/api/v1/mdstrm"
MEGANOTICIAS_DEFAULT_ID = "561430ae330428c223687e1e"
CI_GEO_RESTRICTED_CHANNELS = {
    "TVN",
    "Mega",
    "Meganoticias Ahora",
    "NTV",
    "CHV",
    "CHV Deportes",
    "Canal 13",
    "24 Horas",
    "La Red",
}
# El resolutor publico se ejecuta en Cloudflare. La variable se configura en
# GitHub despues del despliegue y mantiene la M3U sin IPs privadas.
CLOUD_RESOLVER_BASE_URL = os.environ.get("M3U_RESOLVER_BASE_URL", "").strip().rstrip("/")
CLOUD_RESOLVER_URLS = {
    "TVN": f"{CLOUD_RESOLVER_BASE_URL}/tvn.m3u8",
    "Mega": f"{CLOUD_RESOLVER_BASE_URL}/mega.m3u8",
    "Meganoticias Ahora": f"{CLOUD_RESOLVER_BASE_URL}/meganoticias.m3u8",
} if CLOUD_RESOLVER_BASE_URL else {}
CLOUD_RESOLVER_CHANNELS = set(CLOUD_RESOLVER_URLS)
CLOUD_CHANNEL_INFO = {
    "Meganoticias Ahora": (
        '#EXTINF:-1 tvg-id="MeganoticiasAhora.cl" '
        'tvg-name="Meganoticias Ahora" '
        'tvg-logo="https://static2-meganoticias.cdn.mdstrm.com/_common/images/logo-meganoticias-.png" '
        'group-title="Noticias Chile",Meganoticias Ahora'
    ),
}
PREFERRED_LOGOS = {
    "TVN": "https://i.imgur.com/3FKZHL4.png",
    "Mega": "https://i.imgur.com/RlZfR84.png",
    "CHV": "https://i.imgur.com/2Pu8yXf.png",
    "Canal 13": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/chile/canal13-cl.png",
    "La Red": "https://i.imgur.com/nJOVM6e.png",
    "24 Horas": "https://i.imgur.com/CEE9zPe.png",
    "Meganoticias Ahora": "https://static2-meganoticias.cdn.mdstrm.com/_common/images/logo-meganoticias-.png",
    "T13": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/chile/t13-cl.png",
    "CHV Noticias": "https://media.chilevision.cl/2026/01/CHV-NOTICIAS-LOGO@2x.png",
    "NTV": f"{PUBLIC_RAW_BASE}/logos/ntv-transparent.png",
    "TVN3": f"{PUBLIC_RAW_BASE}/logos/tvn3-transparent.png",
    "CHV Deportes": f"{PUBLIC_RAW_BASE}/logos/chv-deportes-transparent.png",
    "France 24 Espanol": f"{PUBLIC_RAW_BASE}/logos/france24-transparent.png",
    "NHK World Japan": f"{PUBLIC_RAW_BASE}/logos/nhk-world-transparent.png",
    "Al Jazeera English": f"{PUBLIC_RAW_BASE}/logos/aljazeera-transparent.png",
    "XITE Hits Germany": f"{PUBLIC_RAW_BASE}/logos/xite-transparent.png",
}
CONTINUOUS_PROGRAMME_DETAILS = {
    "TVN3": (
        "TVN3 - clasicos de TVN",
        "Rotacion continua de programas historicos de TVN; no publica horarios XMLTV estables.",
    ),
    "CHV Deportes": (
        "CHV Deportes en vivo",
        "Senal deportiva continua; la parrilla horaria depende de los eventos publicados por CHV.",
    ),
    "XITE Hits Germany": (
        "XITE Hits Germany - videoclips",
        "Rotacion continua de videoclips musicales; no publica una parrilla horaria XMLTV estable.",
    ),
    "M1": (
        "M1 - rotacion musical",
        "Rotacion continua de videos musicales de M1; los programas especiales pueden cambiar de horario.",
    ),
    "M2": (
        "M2 - rotacion musical",
        "Rotacion continua de videos musicales de M2; los programas especiales pueden cambiar de horario.",
    ),
}
NEWS_CHANNEL_ORDER = ("24 Horas", "Meganoticias Ahora", "CHV Noticias", "T13")
PLAYER_USER_AGENT = "VLC/3.0.20 LibVLC/3.0.20"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
OFFICIAL_STREAM_PAGES = {
    "Mega": ["https://www.mega.cl/senal-en-vivo/"],
    "Meganoticias Ahora": [MEGANOTICIAS_LIVE_PAGE],
    "CHV": ["https://www.chilevision.cl/senal-online"],
    "Canal 13": ["https://www.13.cl/en-vivo"],
    "T13": ["https://www.t13.cl/en-vivo"],
    "24 Horas": ["https://www.24horas.cl/envivo"],
    "La Red": ["https://www.lared.cl/senal-online/"],
}
OFFICIAL_CANDIDATE_HINTS = {
    "Mega": re.compile(r"mega", re.IGNORECASE),
    "Meganoticias Ahora": re.compile(r"(?:mega|meganoticias)", re.IGNORECASE),
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
        "https://unlimited2-cl-isp.dps.live/mega/mega.smil/playlist.m3u8",
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
        "https://live2.airstream.run/3969875408/ts:abr.m3u8",
        "https://d1kqwrirylysyt.cloudfront.net/ts:abr.m3u8",
    ],
    "DW Espanol": [
        "https://dwamdstream104.akamaized.net/hls/live/2015530/dwstream104/master.m3u8"
    ],
    "France 24 Espanol": [
        FRANCE24_ES_1080_URL
    ],
    "Euronews Espanol": [
        "https://cdn-euronews.akamaized.net/live/eds/euronews-es/25053/index.m3u8"
    ],
    "NHK World Japan": [NHK_MASTER_URL],
    "Al Jazeera English": ["https://live-hls-apps-aje-v3-fa.getaj.net/AJE/index.m3u8"],
    "Red Bull TV": ["https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8"],
    "XITE Hits Germany": [
        "https://d726x48n2pd5h.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-skxr1pazhltvp/XITE_Hits.m3u8"
    ],
}
PREFERRED_VARIANT_MASTERS = {
    "CHV": "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/chv/chv.smil/playlist.m3u8",
    "Canal 13": "https://redirector.dps.live/hls/13cl/playlist.m3u8",
    "24 Horas": "https://mdstrm.com/live-stream-playlist/57d1a22064f5d85712b20dab.m3u8",
    "T13": "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/t13/t13.smil/playlist.m3u8",
    "DW Espanol": "https://dwamdstream104.akamaized.net/hls/live/2015530/dwstream104/master.m3u8",
    "Euronews Espanol": "https://cdn-euronews.akamaized.net/live/eds/euronews-es/25053/index.m3u8",
    "Al Jazeera English": "https://live-hls-apps-aje-v3-fa.getaj.net/AJE/index.m3u8",
    "Red Bull TV": "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
    "XITE Hits Germany": "https://d726x48n2pd5h.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-skxr1pazhltvp/XITE_Hits.m3u8",
    "M1": "http://stream.mcquack.net/218/index.m3u8",
    "M2": "http://stream.mcquack.net/330/index.m3u8",
}
MASTER_ONLY_CHANNELS = {"Canal 13"}
CUSTOM_VARIANT_MASTERS = {
    "CHV": (
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/chv/chv.smil/playlist.m3u8",
        "chv-audio.m3u8",
    ),
    "CHV Noticias": (
        "https://redirector.rudo.video/hls-video/339f69c6122f6d8f4574732c235f09b7683e31a5/chvn/chvn.smil/playlist.m3u8",
        "chv-noticias-audio.m3u8",
    ),
    "CHV Deportes": (
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/chvdeportes/chvdeportes.smil/playlist.m3u8",
        "chv-deportes-audio.m3u8",
    ),
    "Canal 13": (
        "https://redirector.dps.live/hls/13cl/playlist.m3u8",
        "canal13-audio.m3u8",
    ),
    "T13": (
        "https://redirector.rudo.video/hls-video/10b92cafdf3646cbc1e727f3dc76863621a327fd/t13/t13.smil/playlist.m3u8",
        "t13-audio.m3u8",
    ),
    "DW Espanol": (
        "https://dwamdstream104.akamaized.net/hls/live/2015530/dwstream104/master.m3u8",
        "dw-espanol-audio.m3u8",
    ),
    "Euronews Espanol": (
        "https://cdn-euronews.akamaized.net/live/eds/euronews-es/25053/index.m3u8",
        "euronews-espanol-audio.m3u8",
    ),
    "Al Jazeera English": (
        "https://live-hls-apps-aje-v3-fa.getaj.net/AJE/index.m3u8",
        "al-jazeera-audio.m3u8",
    ),
    "Red Bull TV": (
        "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
        "red-bull-audio.m3u8",
    ),
    "XITE Hits Germany": (
        "https://d726x48n2pd5h.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-skxr1pazhltvp/XITE_Hits.m3u8",
        "xite-hits-audio.m3u8",
    ),
    "M1": ("http://stream.mcquack.net/218/index.m3u8", "m1-audio.m3u8"),
    "M2": ("http://stream.mcquack.net/330/index.m3u8", "m2-audio.m3u8"),
}
SEGMENT_CHECK_CHANNELS = {
    "TVN",
    "NTV",
    "TVN3",
    "Mega",
    "Meganoticias Ahora",
    "24 Horas",
    "La Red",
    "Canal 13",
    "CHV Noticias",
    "CHV Deportes",
    "France 24 Espanol",
    "DW Espanol",
    "Euronews Espanol",
    "NHK World Japan",
    "Al Jazeera English",
    "Red Bull TV",
    "XITE Hits Germany",
    "M1",
    "M2",
}
CUSTOM_AUDIO_MASTERS = {
    "Mega": (
        MEGA_SOURCE_MASTER_URL,
        "mega-1080-audio.m3u8",
    ),
    "La Red": (
        "https://tv-mgmt.gtd.cl/bpk-tv/LARED/default/index.m3u8",
        "lared-1080-audio.m3u8",
    ),
    "NHK World Japan": (NHK_MASTER_URL, "nhk-1080-audio.m3u8"),
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
        name = line.rsplit(",", 1)[-1].strip() or f"Canal en linea {index + 1}"
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
                Channel(name, candidate, url_line, index, logo_url, group, tvg_id)
            )
            break
        else:
            raise ValueError(f"{name}: falta la URL al final del archivo")
    return channels


def preferred_variant_url(channel_name: str, master_url: str) -> str | None:
    """Return the highest child up to 1080p without dropping separate audio."""
    base_headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "application/vnd.apple.mpegurl,*/*;q=0.8",
    }
    header_sets = [base_headers]
    if channel_name == "TVN":
        header_sets = [
            {
                **base_headers,
                "Referer": "https://live.tvn.cl/",
                "Origin": "https://live.tvn.cl",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            },
            {
                **base_headers,
                "Referer": "https://www.tvn.cl/",
                "Origin": "https://www.tvn.cl",
            },
            {
                "User-Agent": PLAYER_USER_AGENT,
                "Accept": "application/vnd.apple.mpegurl,*/*;q=0.8",
                "Referer": "https://live.tvn.cl/",
                "Origin": "https://live.tvn.cl",
            },
        ]
    last_error: Exception | None = None
    for headers in header_sets:
        try:
            _, body, final_url = fetch_bytes(master_url, headers, limit=1_048_576)
            break
        except Exception as error:
            last_error = error
    else:
        print(
            f"  [AVISO] {channel_name}: no se pudo resolver la variante hasta 1080p: "
            f"{last_error}"
        )
        return None

    text = body.decode("utf-8", "replace")
    if not text.lstrip().startswith("#EXTM3U"):
        return None
    lines = text.splitlines()
    if any(
        line.startswith("#EXT-X-MEDIA:") and re.search(r"TYPE=AUDIO(?:,|$)", line)
        for line in lines
    ):
        print(f"  [OK] {channel_name}: se conserva el maestro HLS para mantener su audio")
        return master_url
    variants: list[tuple[int, int, int, str]] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:") or index + 1 >= len(lines):
            continue
        resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
        if not resolution:
            continue
        codecs_match = re.search(r'CODECS="([^"]+)"', line)
        codecs = codecs_match.group(1).lower() if codecs_match else ""
        if not re.search(r"(?:^|,)\s*(?:mp4a|ac-3|ec-3|opus|vorbis)", codecs):
            continue
        width, height = (int(value) for value in resolution.groups())
        if height > 1080:
            continue
        bandwidth_match = re.search(r"(?:AVERAGE-)?BANDWIDTH=(\d+)", line)
        bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
        variants.append((height, width, bandwidth, urljoin(final_url, lines[index + 1].strip())))
    if not variants:
        return None
    return max(variants)[3]


def pin_preferred_variants(lines: list[str]) -> bool:
    changed = False
    for channel in parse_channels(lines):
        if channel.name in CUSTOM_VARIANT_MASTERS:
            continue
        master_url = PREFERRED_VARIANT_MASTERS.get(channel.name)
        if not master_url:
            continue
        selected_url = (
            master_url
            if channel.name in MASTER_ONLY_CHANNELS
            else preferred_variant_url(channel.name, master_url)
        )
        if selected_url and selected_url != channel.url:
            lines[channel.url_line] = selected_url
            if selected_url == master_url:
                print(f"  [OK] {channel.name}: restaurado maestro HLS con audio")
            else:
                print(f"  [OK] {channel.name}: fijada variante maxima con audio")
            changed = True
    return changed


def pin_cloud_resolver_channels(lines: list[str]) -> bool:
    """Replace renewable channel URLs after the cloud resolver is deployed."""
    if not CLOUD_RESOLVER_URLS:
        return False
    changed = False
    channels = parse_channels(lines)
    present = {channel.name for channel in channels}
    for channel in channels:
        public_url = CLOUD_RESOLVER_URLS.get(channel.name)
        if public_url and channel.url != public_url:
            lines[channel.url_line] = public_url
            changed = True
            print(f"  [OK] {channel.name}: resolutor cloud configurado")
    missing = [
        channel_name
        for channel_name in CLOUD_CHANNEL_INFO
        if channel_name not in present and channel_name in CLOUD_RESOLVER_URLS
    ]
    if missing:
        marker = "# CLOUD_RESOLVER_CHANNELS"
        insertion_index = lines.index(marker) + 1 if marker in lines else len(lines)
        additions: list[str] = []
        for channel_name in missing:
            additions.extend(
                [CLOUD_CHANNEL_INFO[channel_name], CLOUD_RESOLVER_URLS[channel_name], ""]
            )
            print(f"  [OK] {channel_name}: canal agregado al resolutor cloud")
        lines[insertion_index:insertion_index] = additions
        changed = True
    return changed


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
            print(f"  [OK] {channel.name}: logo PNG preferido configurado")
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
    if channel in {"TVN", "NTV", "TVN3"}:
        headers["Referer"] = "https://live.tvn.cl/"
        headers["Origin"] = "https://live.tvn.cl"
    elif channel == "Mega":
        headers["Referer"] = MEGA_LIVE_PAGE
        headers["Origin"] = "https://www.mega.cl"
    elif channel == "Meganoticias Ahora":
        headers["Referer"] = MEGANOTICIAS_LIVE_PAGE
        headers["Origin"] = "https://www.meganoticias.cl"
    elif channel == "La Red":
        headers["Referer"] = "https://www.lared.cl/senal-online/"
    elif channel in {"CHV Noticias", "CHV Deportes"}:
        headers["Referer"] = "https://www.chilevision.cl/senal-online"
        headers["Origin"] = "https://www.chilevision.cl"
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
    """Read generated HLS wrappers locally before they are published by CI."""
    prefix = f"{CUSTOM_HLS_PUBLIC_BASE}/"
    if url.startswith(prefix):
        relative = url[len(prefix) :].split("?", 1)[0]
        parts = Path(relative).parts
        if parts and all(part not in {"", ".", ".."} for part in parts):
            local_path = CUSTOM_HLS_DIR.joinpath(*parts)
            if local_path.is_file():
                return 200, local_path.read_bytes(), url
    return fetch_bytes(url, headers)


def hls_attribute(line: str, name: str) -> str | None:
    match = re.search(
        rf"(?:^|[:,]){re.escape(name)}=(?:\"([^\"]*)\"|([^,]*))", line
    )
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2).strip()


def replace_hls_attribute(line: str, name: str, value: str) -> str:
    pattern = rf"({re.escape(name)}=)(?:\"[^\"]*\"|[^,]*)"
    return re.sub(pattern, rf'\1"{value}"', line, count=1)


def remove_hls_attribute(line: str, name: str) -> str:
    return re.sub(
        rf",?{re.escape(name)}=(?:\"[^\"]*\"|[^,]*)", "", line, count=1
    )


def custom_audio_master(
    channel_name: str, source_url: str, filename: str
) -> str | None:
    """Publish a stable wrapper that pairs a 1080p video child with audio."""
    wrapper_path = CUSTOM_HLS_DIR / filename
    public_url = f"{CUSTOM_HLS_PUBLIC_BASE}/{filename}"
    try:
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/vnd.apple.mpegurl,*/*;q=0.8",
        }
        _, body, final_url = fetch_bytes(source_url, headers, limit=1_048_576)
        source_lines = body.decode("utf-8", "replace").splitlines()
        if not source_lines or not source_lines[0].lstrip().startswith("#EXTM3U"):
            raise ValueError("el maestro fuente no tiene formato HLS")

        variants: list[tuple[int, int, int, str, str, str]] = []
        for index, line in enumerate(source_lines):
            if not line.startswith("#EXT-X-STREAM-INF:") or index + 1 >= len(source_lines):
                continue
            resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
            audio_group = hls_attribute(line, "AUDIO")
            child_line = source_lines[index + 1].strip()
            if not resolution or not audio_group or not child_line or child_line.startswith("#"):
                continue
            width, height = (int(value) for value in resolution.groups())
            if height > 1080:
                continue
            average_bandwidth = hls_attribute(line, "AVERAGE-BANDWIDTH")
            bandwidth = average_bandwidth or hls_attribute(line, "BANDWIDTH") or "0"
            variants.append(
                (
                    height,
                    width,
                    int(bandwidth),
                    audio_group,
                    line,
                    urljoin(final_url, child_line),
                )
            )
        if not variants:
            raise ValueError("no hay variante de video con audio alternativo")

        _, _, _, audio_group, stream_line, video_url = max(variants)
        audio_line = next(
            (
                line
                for line in source_lines
                if line.startswith("#EXT-X-MEDIA:")
                and hls_attribute(line, "TYPE") == "AUDIO"
                and hls_attribute(line, "GROUP-ID") == audio_group
                and hls_attribute(line, "URI")
            ),
            None,
        )
        if audio_line is None:
            raise ValueError(f"no se encontro la pista de audio {audio_group}")
        audio_uri = hls_attribute(audio_line, "URI")
        assert audio_uri is not None
        audio_url = urljoin(final_url, audio_uri)

        for role, child_url in (("video", video_url), ("audio", audio_url)):
            _, child_body, _ = fetch_bytes(child_url, headers, limit=262_144)
            if not child_body.lstrip().startswith(b"#EXTM3U"):
                raise ValueError(f"la pista {role} no devolvio una playlist HLS")

        custom_group = "custom-audio"
        audio_line = replace_hls_attribute(audio_line, "GROUP-ID", custom_group)
        audio_line = replace_hls_attribute(audio_line, "URI", audio_url)
        if hls_attribute(audio_line, "DEFAULT") is None:
            audio_line = audio_line.replace(
                "TYPE=AUDIO,", "TYPE=AUDIO,DEFAULT=YES,", 1
            )

        stream_line = remove_hls_attribute(stream_line, "SUBTITLES")
        stream_line = remove_hls_attribute(stream_line, "CLOSED-CAPTIONS")
        stream_line = replace_hls_attribute(stream_line, "AUDIO", custom_group)
        if hls_attribute(stream_line, "AUDIO") is None:
            stream_line += f',AUDIO="{custom_group}"'

        output_lines = ["#EXTM3U"]
        output_lines.extend(
            line
            for line in source_lines[1:]
            if line.startswith("#EXT-X-VERSION:")
            or line.startswith("#EXT-X-INDEPENDENT-SEGMENTS")
        )
        output_lines.extend([audio_line, stream_line, video_url, ""])
        output = "\n".join(output_lines)
        CUSTOM_HLS_DIR.mkdir(parents=True, exist_ok=True)
        if not wrapper_path.exists() or wrapper_path.read_text(encoding="utf-8") != output:
            temporary = wrapper_path.with_suffix(".m3u8.tmp")
            temporary.write_text(output, encoding="utf-8", newline="\n")
            temporary.replace(wrapper_path)
        resolution = hls_attribute(stream_line, "RESOLUTION") or "video"
        print(f"  [OK] {channel_name}: wrapper directo {resolution} con audio generado")
        return public_url
    except Exception as error:
        if wrapper_path.is_file():
            print(
                f"  [AVISO] {channel_name}: no se pudo renovar su wrapper ({error}); "
                "se conserva el ultimo publicado"
            )
            return public_url
        print(f"  [AVISO] {channel_name}: no se pudo generar wrapper con audio: {error}")
        return None


def custom_variant_master(
    channel_name: str, source_url: str, filename: str
) -> str | None:
    """Publish one stable child variant when its video already embeds audio."""
    wrapper_path = CUSTOM_HLS_DIR / filename
    public_url = f"{CUSTOM_HLS_PUBLIC_BASE}/{filename}"
    try:
        headers = {
            **request_headers(channel_name),
            "Accept": "application/vnd.apple.mpegurl,*/*;q=0.8",
        }
        _, body, final_url = fetch_bytes(source_url, headers, limit=1_048_576)
        source_lines = body.decode("utf-8", "replace").splitlines()
        if not source_lines or not source_lines[0].lstrip().startswith("#EXTM3U"):
            raise ValueError("el maestro fuente no tiene formato HLS")

        variants: list[tuple[int, int, int, str, str]] = []
        for index, line in enumerate(source_lines):
            if not line.startswith("#EXT-X-STREAM-INF:") or index + 1 >= len(source_lines):
                continue
            resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
            child_line = source_lines[index + 1].strip()
            codecs = (hls_attribute(line, "CODECS") or "").lower()
            has_embedded_audio = bool(
                re.search(r"(?:^|,)\s*(?:mp4a|ac-3|ec-3|opus|vorbis)", codecs)
            )
            if not resolution or not child_line or child_line.startswith("#"):
                continue
            if not has_embedded_audio:
                continue
            width, height = (int(value) for value in resolution.groups())
            if height > 1080:
                continue
            bandwidth_match = re.search(r"(?:AVERAGE-)?BANDWIDTH=(\d+)", line)
            bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
            variants.append(
                (
                    height,
                    width,
                    bandwidth,
                    line,
                    urljoin(final_url, child_line),
                )
            )
        if not variants:
            raise ValueError("el maestro no declara una variante con audio embebido")

        _, _, _, stream_line, child_url = max(variants)
        child_status, child_body, _ = fetch_bytes(child_url, headers, limit=262_144)
        if child_status != 200 or not child_body.lstrip().startswith(b"#EXTM3U"):
            raise ValueError("la variante seleccionada no devolvio una playlist HLS")

        output_lines = ["#EXTM3U"]
        output_lines.extend(
            line
            for line in source_lines[1:]
            if line.startswith("#EXT-X-VERSION:")
            or line.startswith("#EXT-X-INDEPENDENT-SEGMENTS")
        )
        output_lines.extend([stream_line, child_url, ""])
        output = "\n".join(output_lines)
        CUSTOM_HLS_DIR.mkdir(parents=True, exist_ok=True)
        if not wrapper_path.exists() or wrapper_path.read_text(encoding="utf-8") != output:
            temporary = wrapper_path.with_suffix(".m3u8.tmp")
            temporary.write_text(output, encoding="utf-8", newline="\n")
            temporary.replace(wrapper_path)
        resolution = hls_attribute(stream_line, "RESOLUTION") or "video"
        print(f"  [OK] {channel_name}: wrapper directo {resolution} con audio embebido")
        return public_url
    except Exception as error:
        if wrapper_path.is_file():
            print(
                f"  [AVISO] {channel_name}: no se pudo renovar su wrapper ({type(error).__name__}); "
                "se conserva el ultimo publicado"
            )
            return public_url
        print(
            f"  [AVISO] {channel_name}: no se pudo generar wrapper con audio embebido: "
            f"{type(error).__name__}"
        )
        return None


def pin_custom_audio_channels(lines: list[str]) -> bool:
    changed = False
    for channel in parse_channels(lines):
        if CLOUD_RESOLVER_URLS.get(channel.name) == channel.url:
            continue
        source = CUSTOM_AUDIO_MASTERS.get(channel.name)
        if not source:
            continue
        custom_url = custom_audio_master(channel.name, source[0], source[1])
        if custom_url and custom_url != channel.url:
            lines[channel.url_line] = custom_url
            changed = True
    return changed


def pin_custom_variant_channels(lines: list[str]) -> bool:
    changed = False
    for channel in parse_channels(lines):
        source = CUSTOM_VARIANT_MASTERS.get(channel.name)
        if not source:
            continue
        custom_url = custom_variant_master(channel.name, source[0], source[1])
        if custom_url and custom_url != channel.url:
            lines[channel.url_line] = custom_url
            changed = True
    return changed


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


def epg_status_from_xml(
    data: bytes,
    expected_ids: set[str],
    *,
    now: datetime,
    minimum_future: timedelta,
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
    first_start: datetime | None = None
    last_stop: datetime | None = None
    for programme in root.findall("programme"):
        channel_id = programme.get("channel", "")
        if channel_id not in expected_ids:
            continue
        start = xmltv_datetime(programme.get("start", ""))
        stop = xmltv_datetime(programme.get("stop", ""))
        counts[channel_id] += 1
        previous = last_by_channel.get(channel_id)
        last_by_channel[channel_id] = stop if previous is None or stop > previous else previous
        first_start = start if first_start is None or start < first_start else first_start
        last_stop = stop if last_stop is None or stop > last_stop else last_stop

    empty = sorted(channel_id for channel_id, count in counts.items() if count == 0)
    if empty:
        raise ValueError("canales sin programas en la EPG: " + ", ".join(empty))
    expiring = sorted(
        channel_id
        for channel_id in expected_ids
        if last_by_channel.get(channel_id, now) < now + minimum_future
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
        "guide_types": guide_types,
    }


def find_red_bull_channel_rails(value):
    if isinstance(value, dict):
        rails = value.get("channelRails")
        if isinstance(rails, list):
            return rails
        for child in value.values():
            found = find_red_bull_channel_rails(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_red_bull_channel_rails(child)
            if found is not None:
                return found
    return None


def red_bull_schedule(page_html: str) -> list[dict]:
    scripts = re.findall(
        r"<script>self\.__next_f\.push\((.*?)\)</script>", page_html, re.DOTALL
    )
    rails = None
    for script in scripts:
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue
        if len(payload) < 2 or not isinstance(payload[1], str):
            continue
        if "schedule_dates_state" not in payload[1]:
            continue
        serialized = payload[1].split(":", 1)[-1]
        rails = find_red_bull_channel_rails(json.loads(serialized))
        if rails:
            break
    if not rails:
        raise ValueError("Red Bull TV no publico la estructura de su parrilla")

    channel = next(
        (item for item in rails if item.get("id") == RED_BULL_CHANNEL_ID), None
    )
    if channel is None:
        raise ValueError("no se encontro el canal World of Red Bull")
    schedule: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for card in channel.get("cards", []):
        title = card.get("title")
        start = card.get("start_time")
        stop = card.get("end_time")
        if not title or not start or not stop:
            continue
        key = (start, stop, title)
        if key in seen:
            continue
        seen.add(key)
        schedule.append(card)
    if len(schedule) < 5:
        raise ValueError("Red Bull TV entrego una parrilla demasiado corta")
    return schedule


def decode_web_text(data: bytes) -> str:
    decoded = data.decode("utf-8", "replace")
    if "\ufffd" in decoded:
        return data.decode("cp1252", "replace")
    return decoded


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
                previous_start: datetime | None = None
                for start_text, stop_text, title in items:
                    try:
                        start_clock = datetime.strptime(start_text, "%H:%M").time()
                        stop_clock = datetime.strptime(stop_text, "%H:%M").time()
                    except ValueError:
                        continue
                    start = datetime.combine(
                        schedule_day, start_clock, tzinfo=CHILE_TIMEZONE
                    )
                    if previous_start is not None and start <= previous_start:
                        start += timedelta(days=1)
                    stop = datetime.combine(
                        schedule_day, stop_clock, tzinfo=CHILE_TIMEZONE
                    )
                    while stop <= start:
                        stop += timedelta(days=1)
                    previous_start = start
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
                            "start": xmltv_format(start),
                            "stop": xmltv_format(stop),
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
    formatter: Callable[[datetime], str] = xmltv_format,
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
        ET.SubElement(programme, "desc", {"lang": "es"}).text = description
        count += 1
        start = stop
    return count


def build_epg(
    source_documents: dict[str, bytes],
    channels: list[Channel],
    red_bull_cards: list[dict],
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
            "source-info-name": "EPGShare01, TecnoCentro y fuentes oficiales",
            "data-generated-at": now.astimezone(timezone.utc).isoformat(),
        },
    )
    channel_by_id = {channel.tvg_id: channel for channel in channels}
    guide_types: dict[str, str] = {}
    for channel in channels:
        element = ET.SubElement(root, "channel", {"id": channel.tvg_id})
        ET.SubElement(element, "display-name").text = channel.name
        if channel.logo_url:
            ET.SubElement(element, "icon", {"src": channel.logo_url})

    source_roots: dict[str, ET.Element] = {}
    for source_name, source_xml in source_documents.items():
        source_root = ET.fromstring(source_xml)
        if source_root.tag != "tv":
            raise ValueError(f"la fuente EPG {source_name} no contiene una raiz <tv>")
        source_roots[source_name] = source_root

    programmes_by_target = {channel_id: 0 for channel_id in expected_ids}
    source_lookup = {
        (source_name, source_id): target_id
        for target_id, (source_name, source_id) in EPG_PROGRAMME_SOURCES.items()
        if target_id in expected_ids
    }
    for source_name, source_root in source_roots.items():
        for programme in source_root.findall("programme"):
            target_id = source_lookup.get((source_name, programme.get("channel", "")))
            if target_id is None:
                continue
            copied = copy.deepcopy(programme)
            copied.set("channel", target_id)
            root.append(copied)
            programmes_by_target[target_id] += 1
            guide_types[target_id] = "parrilla real"

    red_bull_id = "RedBullTV.at"
    if red_bull_id in expected_ids:
        red_bull_last_stop: datetime | None = None
        for card in red_bull_cards:
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
            ET.SubElement(programme, "title", {"lang": "es"}).text = card["title"]
            subtitle = card.get("subheading")
            if subtitle:
                ET.SubElement(programme, "sub-title", {"lang": "es"}).text = subtitle
            description = card.get("short_description") or card.get("long_description")
            if description:
                ET.SubElement(programme, "desc", {"lang": "es"}).text = description
            programmes_by_target[red_bull_id] += 1
            red_bull_last_stop = (
                stop
                if red_bull_last_stop is None or stop > red_bull_last_stop
                else red_bull_last_stop
            )
        if programmes_by_target[red_bull_id]:
            programmes_by_target[red_bull_id] += add_continuous_programmes(
                root,
                red_bull_id,
                channel_by_id[red_bull_id].name,
                now=now,
                start_at=red_bull_last_stop,
                formatter=xmltv_format_chile,
            )
            guide_types[red_bull_id] = "parrilla oficial + continuidad"

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

    ET.indent(root, space="  ")
    output = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    status = epg_status_from_xml(
        output,
        expected_ids,
        now=now,
        minimum_future=timedelta(hours=24),
    )
    status["guide_types"] = guide_types
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

    if source_errors and existing_status is not None:
        existing_status.update(
            {
                "updated": False,
                "preserved": True,
                "warning": "se conservo la guia anterior por fallos de fuente",
                "source_errors": source_errors,
            }
        )
        return existing_status

    tecnocentro_data, tecnocentro_errors = fetch_tecnocentro_epg(channels, now)
    if tecnocentro_data:
        source_documents["tecnocentro"] = tecnocentro_data
    source_errors.update(
        {f"tecnocentro:{target_id}": error for target_id, error in tecnocentro_errors.items()}
    )
    if not source_documents:
        raise RuntimeError("ninguna fuente EPG respondio correctamente")

    red_bull_cards: list[dict] = []
    try:
        _, body, _ = fetch_bytes(
            f"{RED_BULL_EPG_PAGE}?refresh={int(time.time())}",
            {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "text/html,*/*",
                "X-Forwarded-For": RED_BULL_CHILE_GEO_IP,
            },
            timeout=90,
            limit=25_165_824,
        )
        red_bull_cards = red_bull_schedule(body.decode("utf-8", "replace"))
    except Exception as error:
        source_errors["red_bull"] = str(error)

    output, epg_status = build_epg(
        source_documents, channels, red_bull_cards, now=now
    )
    temporary = EPG_PATH.with_suffix(".xml.tmp")
    temporary.write_bytes(output)
    temporary.replace(EPG_PATH)
    epg_status.update(
        {
            "updated": True,
            "sources": list(source_documents),
            "source_errors": source_errors,
        }
    )
    return epg_status


def check_channel(
    channel: Channel, attempts: int = 2, *, allow_ci_geo_block: bool = False
) -> CheckResult:
    if (
        allow_ci_geo_block
        and CLOUD_RESOLVER_URLS.get(channel.name) == channel.url
    ):
        return CheckResult(
            channel.name,
            channel.url,
            True,
            "resolutor Cloud Run conservado; el stream se valida desde Santiago",
        )
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
                        return CheckResult(
                            channel.name, channel.url, False, segment_detail
                        )
                    detail += f"; {segment_detail}"
                return CheckResult(channel.name, channel.url, True, detail)
            last_error = f"HTTP {status}, contenido no reconocido"
        except urllib.error.HTTPError as error:
            geo_error_codes = {403}
            if channel.name == "TVN":
                geo_error_codes.add(401)
            if (
                allow_ci_geo_block
                and channel.name in CI_GEO_RESTRICTED_CHANNELS
                and error.code in geo_error_codes
            ):
                return CheckResult(
                    channel.name,
                    channel.url,
                    True,
                    f"reproduccion limitada fuera de Chile (HTTP {error.code})",
                )
            last_error = f"HTTP {error.code} {error.reason}"
        except Exception as error:  # Network and TLS failures need a compact report.
            if (
                allow_ci_geo_block
                and channel.name == "TVN"
                and "/live-stream-playlist/" in channel.url
                and isinstance(error, urllib.error.URLError)
            ):
                return CheckResult(
                    channel.name,
                    channel.url,
                    True,
                    "maestro vigente; runner fuera de Chile no pudo probarlo",
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
        segment = next((line for line in lines if line and not line.startswith("#")), None)
        if not segment:
            return False, "playlist sin segmento multimedia"
        segment_url = urljoin(final_url, segment)
        segment_status, segment_body, _ = fetch_bytes(
            segment_url, headers, timeout=25, limit=64
        )
        if segment_status == 200 and segment_body:
            return True, "primer segmento multimedia valido"
        return False, f"segmento HTTP {segment_status}"
    except urllib.error.HTTPError as error:
        return False, f"segmento HTTP {error.code} {error.reason}"
    except Exception as error:
        return False, f"segmento {type(error).__name__}: {error}"


def check_logo(channel: Channel) -> LogoResult:
    if not channel.logo_url:
        return LogoResult(channel.name, "", False, "falta tvg-logo")
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "image/png,image/*;q=0.8,*/*;q=0.5"}
    try:
        status, body, _ = fetch_bytes(channel.logo_url, headers, limit=65_536)
        if status == 200 and body.startswith(b"\x89PNG\r\n\x1a\n"):
            if not png_has_transparency(body):
                return LogoResult(
                    channel.name,
                    channel.logo_url,
                    False,
                    "PNG valido pero sin canal alfa transparente",
                )
            return LogoResult(channel.name, channel.logo_url, True, "PNG valido y transparente")
        return LogoResult(channel.name, channel.logo_url, False, f"HTTP {status}, no es PNG")
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
        "TVN": fresh_tvn_url,
        "24 Horas": fresh_24horas_url,
        "Meganoticias Ahora": fresh_meganoticias_url,
    }
    factory = dynamic_factories.get(channel.name)
    if factory:
        try:
            candidates.append(factory())
        except Exception as error:
            print(f"  [AVISO] {channel.name}: no se pudo renovar el enlace oficial: {error}")
    candidates.extend(KNOWN_STREAM_FALLBACKS.get(channel.name, []))
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
        if CLOUD_RESOLVER_URLS.get(channel.name) == channel.url:
            print(
                f"  [CONSERVADO] {channel.name}: el resolutor Cloud Run se mantiene; "
                "su stream se valida desde Santiago"
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


def tvn_page_html() -> str:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": "https://www.tvn.cl/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    try:
        _, body, _ = fetch_bytes(TVN_LIVE_PAGE, headers, limit=1_048_576)
    except urllib.error.URLError as error:
        reason = str(getattr(error, "reason", error)).lower()
        if "certificate verify failed" not in reason and "certificate has expired" not in reason:
            raise
        print("  TVN: certificado web vencido; usando excepcion TLS solo para su pagina oficial")
        insecure_context = ssl.create_default_context()
        insecure_context.check_hostname = False
        insecure_context.verify_mode = ssl.CERT_NONE
        _, body, _ = fetch_bytes(
            TVN_LIVE_PAGE, headers, context=insecure_context, limit=1_048_576
        )
    return body.decode("utf-8", "replace")


def fresh_tvn_url() -> str:
    html = tvn_page_html()
    stream_id_match = re.search(r"\bid\s*:\s*['\"]([a-zA-Z0-9]+)['\"]", html)
    token_match = re.search(r"\baccess_token\s*:\s*['\"]([^'\"]+)['\"]", html)
    if not token_match:
        raise RuntimeError("la pagina oficial de TVN no publico un access_token")
    stream_id = stream_id_match.group(1) if stream_id_match else TVN_DEFAULT_ID
    token = token_match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise RuntimeError("TVN entrego un token con formato inesperado")
    playlist_url = f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8?access_token={token}"
    return playlist_url


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


def fresh_megamedia_url(page_url: str, default_id: str, label: str) -> str:
    html = megamedia_page_html(page_url)
    config_match = re.search(
        r"var\s+VideoSenalEnVivo\s*=\s*\{\s*id:\s*'([^']+)'"
        r".*?serverKey\s*:\s*'([^']+)'",
        html,
        flags=re.DOTALL,
    )
    if not config_match:
        raise RuntimeError(f"la pagina de {label} no publico la configuracion del reproductor")
    stream_id, server_key = config_match.groups()
    stream_id = stream_id or default_id
    query = urlencode(
        {
            "id": stream_id,
            "ua": BROWSER_USER_AGENT,
            "type": "live",
            "process": "access_token",
            "key": server_key,
        }
    )
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": page_url,
        "Origin": urlsplit(page_url).scheme + "://" + urlsplit(page_url).netloc,
        "Accept": "application/json",
    }
    status, body, _ = fetch_bytes(
        f"{MEGAMEDIA_API_URL}?{query}", headers, limit=262_144
    )
    if status != 200:
        raise RuntimeError(f"la API de {label} respondio HTTP {status}")
    try:
        response = json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"la API de {label} no devolvio JSON") from error
    token = response.get("access_token") if isinstance(response, dict) else None
    if not token or not isinstance(token, str):
        message = response.get("message", "sin token") if isinstance(response, dict) else "sin token"
        raise RuntimeError(f"la API de {label} no emitio access_token ({message})")
    if not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise RuntimeError(f"{label} entrego un token con formato inesperado")
    return (
        f"https://mdstrm.com/live-stream-playlist/{stream_id}.m3u8?access_token="
        f"{quote(token, safe='')}"
    )


def fresh_meganoticias_url() -> str:
    return fresh_megamedia_url(
        MEGANOTICIAS_LIVE_PAGE,
        MEGANOTICIAS_DEFAULT_ID,
        "Meganoticias Ahora",
    )


def refresh_dynamic_channel(
    lines: list[str],
    channel: Channel,
    fresh_url_factory: Callable[[], str],
    *,
    running_in_ci: bool,
) -> bool:
    if CLOUD_RESOLVER_URLS.get(channel.name) == channel.url:
        current_result = check_channel(channel, allow_ci_geo_block=running_in_ci)
        state = "OK" if current_result.ok else "FALLO"
        print(f"  [{state}] {channel.name}: resolutor Cloud Run conservado; {current_result.detail}")
        return False
    if running_in_ci and CLOUD_RESOLVER_URLS.get(channel.name) == channel.url:
        print(
            f"  [CI] {channel.name}: se conserva el resolutor Cloud Run; "
            "la renovacion se ejecuta en Santiago"
        )
        return False
    current_result = check_channel(channel, allow_ci_geo_block=running_in_ci)
    state = "OK" if current_result.ok else "FALLO"
    print(f"  [{state}] {channel.name}: {current_result.detail}")
    use_dynamic_master = "/live-stream-gdai/" not in channel.url
    needs_refresh = running_in_ci or not current_result.ok or not use_dynamic_master
    if not needs_refresh:
        return False

    candidates: list[str] = []
    try:
        candidates.append(fresh_url_factory())
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
    if ensure_playlist_epg_url(lines):
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("Cabecera M3U enlazada a la guia EPG publicada en GitHub")
    cloud_resolver_changed = pin_cloud_resolver_channels(lines)
    news_order_changed = pin_news_channel_order(lines)
    preferred_logo_changed = pin_preferred_logos(lines)
    custom_audio_changed = pin_custom_audio_channels(lines)
    custom_variant_changed = pin_custom_variant_channels(lines)
    variants_changed = pin_preferred_variants(lines)
    if (
        cloud_resolver_changed
        or news_order_changed
        or preferred_logo_changed
        or custom_audio_changed
        or custom_variant_changed
        or variants_changed
    ):
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("Wrappers y variantes de video compatibles guardados en la lista")
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
    refreshed_channels: list[str] = []
    refresh_changed = False
    dynamic_channels = {
        "TVN": fresh_tvn_url,
        "24 Horas": fresh_24horas_url,
        "Meganoticias Ahora": fresh_meganoticias_url,
    }
    for channel_name, fresh_url_factory in dynamic_channels.items():
        channel = next((item for item in channels if item.name == channel_name), None)
        if channel and refresh_dynamic_channel(
            lines,
            channel,
            fresh_url_factory,
            running_in_ci=running_in_ci,
        ):
            refreshed_channels.append(channel_name)
            refresh_changed = True
    if refresh_changed:
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    tvn_refreshed = "TVN" in refreshed_channels

    print("Verificacion final de la lista completa")
    final_lines = playlist.read_text(encoding="utf-8-sig").splitlines()
    final_channels = parse_channels(final_lines)
    results = verify_all(final_channels, allow_ci_geo_block=running_in_ci)
    repaired_channels = repair_failed_channels(
        final_lines,
        final_channels,
        results,
        allow_ci_geo_block=running_in_ci,
    )
    if repaired_channels:
        playlist.write_text(
            "\n".join(final_lines) + "\n", encoding="utf-8", newline="\n"
        )
        final_lines = playlist.read_text(encoding="utf-8-sig").splitlines()
        final_channels = parse_channels(final_lines)
        print("Verificacion posterior a las reparaciones")
        results = verify_all(final_channels, allow_ci_geo_block=running_in_ci)

    print("Verificacion de logos PNG")
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
