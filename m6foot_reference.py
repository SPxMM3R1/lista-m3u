"""Public, tokenless M6Foot locators. Player ids only; signed URLs never belong here."""
import re
from urllib.parse import quote, unquote, urlsplit

PLAYER_ID = re.compile(r"[0-9]{1,6}")


def channel_id(player_id: str) -> str:
    if not PLAYER_ID.fullmatch(player_id):
        raise ValueError("Identificador M6Foot no permitido")
    return f"M6Foot.{player_id}@M6Foot"


def reference(player_id: str) -> str:
    if not PLAYER_ID.fullmatch(player_id):
        raise ValueError("Identificador M6Foot no permitido")
    return "vibem3u://resolver/m6foot/" + quote(player_id, safe="")


def parse_reference(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme != "vibem3u" or parsed.netloc != "resolver" or parsed.query or parsed.fragment:
        return None
    parts = parsed.path.split("/")
    if len(parts) != 3 or parts[:2] != ["", "m6foot"]:
        return None
    player_id = unquote(parts[2])
    return player_id if PLAYER_ID.fullmatch(player_id) else None
