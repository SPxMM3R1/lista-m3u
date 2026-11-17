"""Parrillas deportivas del operador Movistar Plus España."""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode

from update_m3u import MOVISTAR_SPAIN_FEEDS, fetch_bytes


def fetch_movistar_spain_epg(channels, now):
    root = ET.Element("tv")
    wanted = {channel.tvg_id for channel in channels}
    for channel_id, feed in MOVISTAR_SPAIN_FEEDS.items():
        if channel_id not in wanted:
            continue
        query = urlencode({
            "from": now.astimezone(timezone.utc).strftime("%Y-%m-%dT00:00:00"),
            "span": 3, "channel": feed, "version": 8, "mdrm": "true",
            "tlsstream": "true", "demarcation": 18,
        })
        try:
            status, body, _ = fetch_bytes(
                "https://ottcache.dof6.com/movistarplus/webplayer/OTT/epg?" + query,
                {"Accept": "application/json"}, timeout=25, limit=4_000_000,
            )
            events = json.loads(body) if status == 200 else []
        except (OSError, ValueError, RuntimeError):
            continue
        for event in events if isinstance(events, list) else []:
            if not isinstance(event, dict) or (event.get("Canal") or {}).get("CodCadenaTv") != feed:
                continue
            title = (event.get("Titulo") or "").strip()
            episode = (event.get("TituloEpisodio") or "").strip('" ')
            try:
                start, stop = (datetime.fromtimestamp(int(event[key]) / 1000, timezone.utc)
                               for key in ("FechaHoraInicio", "FechaHoraFin"))
            except (TypeError, KeyError, ValueError, OSError, OverflowError):
                continue
            if not title or stop <= start:
                continue
            row = ET.SubElement(root, "programme", channel=feed,
                                start=start.strftime("%Y%m%d%H%M%S %z"),
                                stop=stop.strftime("%Y%m%d%H%M%S %z"))
            ET.SubElement(row, "title", lang="es").text = (
                f"{title}: {episode}" if episode and episode != title else title
            )
    if not len(root):
        return None, "Movistar Plus sin programas para las señales solicitadas"
    return ET.tostring(root, encoding="utf-8"), None
