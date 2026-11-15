"""Une los respaldos de los 4 National Geographic de Lista 2 en el principal 5fa93eee (2026-11-15)."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PRINCIPAL = "PublicDirect.5fa93eee31589e2105958c0e"
MERGED = ["PublicDirect.f753ad9eb3f48c300c6fa4b4", "PublicDirect.8a5d0371ff496197a85a71b8", "PublicDirect.956ee9e1ecd09ce19202225f"]
backups = json.loads((ROOT / "backups.json").read_text(encoding="utf-8"))
layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
rows = {r.get("tvgId"): r for r in layout["channels"]}
l2 = json.loads((ROOT / "epg-l2-map.json").read_text(encoding="utf-8"))
def guide(i):
    def find(d):
        if isinstance(d, dict):
            if i in d and isinstance(d[i], dict) and "source" in d[i]:
                return {"source": d[i]["source"], "source_id": d[i]["source_id"]}
            for v in d.values():
                r = find(v)
                if r: return r
    return find(l2) or {}
m3u = (ROOT / "2.m3u").read_text(encoding="utf-8")
urls = dict(re.findall(r'tvg-id="([^"]+)"[^\n]*\n(\S+)', m3u))
principal = backups["channels"][PRINCIPAL]
items = list(principal.get("backups", []))
for mid in MERGED:
    r = rows[mid]
    entry = backups["channels"].pop(mid, None)
    items.append({
        "tvg_id": mid, "display_name": r["displayName"], "source_name": r["name"],
        "from_list": "Lista 2", "from_number": r["number"], "group": r["group"],
        "logo": r.get("logoOverride") or r.get("logoPath"), "url": urls[mid], "guide": guide(mid),
    })
    if entry:
        items.extend(entry.get("backups", []))
seen, merged = set(), []
for b in items:
    if b["tvg_id"] in seen or b["tvg_id"] == PRINCIPAL: continue
    seen.add(b["tvg_id"]); merged.append(b)
principal["backups"] = merged
principal["verified"] += (" 2026-11-15 (pedido del usuario «¿Por qué los Natgeo no están como backups entre ellos?», "
    "aplicado con «aplícalas»): fotogramas simultáneos del 2026-11-14 muestran que los 4 National Geographic de Lista 2 "
    "son la misma señal con segundos de desfase; se suman como respaldos f753ad9e, 8a5d0371 y 956ee9e1 con sus copias. "
    "Principal: 200.7.99.59 (1080p 59,94, AC3).")
(ROOT / "backups.json").write_bytes((json.dumps(backups, ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8"))
print("respaldos:", len(merged))
