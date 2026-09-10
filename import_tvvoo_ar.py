"""Import the user-requested complete ar metadata inventory without session URLs."""

import argparse
from collections import defaultdict
import json
import hashlib
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import urlopen

import discover_tvvoo_catalog as discovery
import update_m3u as updater


SOURCE = "https://raw.githubusercontent.com/qwertyuiop8899/tvvoo/main/src/channels/lists.json"
ROOT = Path(__file__).resolve().parent


def group_entries(entries):
    groups = defaultdict(list)
    for entry in entries:
        if entry.get("country") != "Arabia":
            continue
        name = discovery.normalize_spaces(entry.get("name", ""))
        alias = "vavoo_" + quote(name, safe="") + "%7Cgroup%3Aar"
        # Preserve non-Latin names; ASCII-only grouping would merge distinct
        # Arabic channels which happen to share an English prefix.
        tokens = re.findall(r"\w+", name.upper())
        key = " ".join("SPORT" if t == "SPORTS" else t for t in tokens if t not in discovery.QUALITY_TOKENS)
        if not key:
            key = "CHANNEL" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:16].upper()
        if not updater.TVVOO_DISCOVERY_ALIAS_PATTERN.fullmatch(alias) or not name or len(name) > 100 or not key:
            raise ValueError("Invalid ar channel metadata: " + name)
        groups[key].append((name, alias, entry))
    return groups


def import_entries(entries, document, catalog_text):
    """Preserve existing channels and merge quality variants by stable alias."""
    sidecar = document["channels"]
    alias_owners = {}
    used_ids = set(sidecar)
    used_names = {entry["name"] for entry in sidecar.values()}
    lines = catalog_text.splitlines()
    for line in lines:
        if not line.startswith("#EXTINF:"):
            continue
        cid = discovery.m3u_attribute(line, "tvg-id")
        used_ids.add(cid)
        used_names.add(line.rsplit(",", 1)[-1])
        for alias in discovery.m3u_attribute(line, "x-resolver-ids").split(";"):
            if alias:
                alias_owners[alias] = cid
    for cid, entry in sidecar.items():
        for alias in entry["aliases"]:
            alias_owners[alias] = cid

    stats = {"source_entries": 0, "groups": 0, "existing": 0, "added": 0, "without_logo": 0}
    for key, variants in sorted(group_entries(entries).items()):
        stats["source_entries"] += len(variants)
        stats["groups"] += 1
        aliases = sorted({v[1] for v in variants}, key=discovery.alias_preference)
        if len(aliases) > updater.TVVOO_DISCOVERY_MAX_ALIASES:
            raise ValueError("Too many variants: " + key)
        if any(alias in alias_owners for alias in aliases):
            stats["existing"] += 1
            continue
        name, _, meta = min(variants, key=lambda v: discovery.alias_preference(v[1]))
        logo = next((discovery.safe_logo(v[2].get("logo")) for v in variants if discovery.safe_logo(v[2].get("logo"))), "")
        category = discovery.category_for(name, meta.get("category", ""), meta)
        group = discovery.CandidateGroup("ar", name, tuple(aliases), logo, category, key if len(key) >= 2 else key + "TV")
        cid = discovery.stable_channel_id(group, used_ids)
        display = re.sub(r'[",]', " ", name) + " [TvVoo ar]"
        if display in used_names:
            display += " " + cid.split(".")[-1].split("@")[0][-8:]
        sidecar[cid] = dict(name=display, aliases=aliases, region="ar", sourceName=name, category=category, logo=logo)
        lines.extend([
            f'#EXTINF:-1 tvg-id="{cid}" tvg-name="{display}" tvg-logo="{logo}" '
            f'group-title="PRUEBA - {category}" x-resolver="tvvoo" '
            f'x-resolver-endpoint="{updater.TVVOO_STREAM_BASE_URL}" '
            f'x-resolver-ids="{";".join(aliases)}" x-resolver-refresh="on_play" '
            f'x-resolver-recipe="{updater.TVVOO_RECIPE_ID}",{display}',
            f"{updater.TVVOO_STREAM_BASE_URL}/{aliases[0]}.json",
        ])
        used_ids.add(cid)
        used_names.add(display)
        for alias in aliases:
            alias_owners[alias] = cid
        stats["added"] += 1
        stats["without_logo"] += not bool(logo)
    updater.validate_tvvoo_discovery_document(document)
    return document, "\n".join(lines) + "\n", stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the inventory; default is dry run")
    args = parser.parse_args()
    with urlopen(SOURCE, timeout=30) as response:
        entries = json.load(response)
    sidecar_path = ROOT / "tvvoo-discovered.json"
    catalog_path = ROOT / "channel-catalog.m3u"
    document, catalog, stats = import_entries(
        entries,
        json.loads(sidecar_path.read_text(encoding="utf-8")),
        catalog_path.read_text(encoding="utf-8"),
    )
    if args.write:
        discovery.write_text_if_changed(sidecar_path, json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        discovery.write_text_if_changed(catalog_path, catalog)
    print(json.dumps(stats, ensure_ascii=False))
    print("Inventory only: playback must be checked by channel maintenance.")


if __name__ == "__main__":
    main()
