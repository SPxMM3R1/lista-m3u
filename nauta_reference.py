"""Public, tokenless Nauta locators. Provider IDs and playback URLs never belong here."""
import hashlib
import re
from urllib.parse import quote, unquote, urlsplit


def channel_id(name: str) -> str:
    return "Nauta." + hashlib.sha256(name.encode("utf-8")).hexdigest()[:24] + "@Nauta"


def locator(catalog: str, name: str) -> str:
    if not re.fullmatch(r"cat_[0-9]+|nautatv_catalog", catalog):
        raise ValueError("Catálogo Nauta no permitido")
    if not name or len(name) > 200 or any(ord(c) < 32 for c in name) or any(c in name for c in "\\?#") or "://" in name:
        raise ValueError("Nombre Nauta no permitido")
    return catalog + "|" + name


def reference(catalog: str, name: str) -> str:
    return "vibem3u://resolver/nauta/" + quote(locator(catalog, name), safe="")


def parse_reference(url: str) -> tuple[str, str] | None:
    p = urlsplit(url)
    if p.scheme != "vibem3u" or p.netloc != "resolver" or p.query or p.fragment:
        return None
    parts = p.path.split("/")
    if len(parts) != 3 or parts[:2] != ["", "nauta"]:
        return None
    decoded = unquote(parts[2])
    catalog, separator, name = decoded.partition("|")
    try:
        return (catalog, name) if separator and locator(catalog, name) == decoded else None
    except ValueError:
        return None
