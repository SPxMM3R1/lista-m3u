"""Reuse Main Event UHD geometry and the existing F1 mark, without redrawing."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LOGOS = ROOT / "logos"
NS = "http://www.w3.org/2000/svg"


def bounds(path):
    # These traced assets contain only absolute M/L/Z coordinate pairs.
    assert not re.search(r"[A-KN-Yac-z]", path)
    numbers = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", path)))
    return min(numbers[::2]), min(numbers[1::2]), max(numbers[::2]), max(numbers[1::2])


def main():
    target = LOGOS / "sky-sports-f1-uhd.png"
    base = Image.open(LOGOS / "sky-sports-main-event-uhd.png").convert("RGBA")
    source = ET.parse(LOGOS / "sky-sports-f1-uhd.svg").getroot()
    stored_mark = source.find(f"{{{NS}}}g[@id='f1-identifier']")
    if stored_mark is not None:
        symbol = stored_mark.find(f"{{{NS}}}path").get("d")
    else:
        symbol = " ".join(p for p in re.findall(r"M[^M]*", source.find(f"{{{NS}}}path").get("d"))
                          if bounds(p)[1] >= 470)
    assert symbol
    x0, y0, x1, y1 = bounds(symbol)
    replacement_box = (round(base.width * .15), round(base.height * .55),
                       round(base.width * .85), round(base.height * .91))
    old_text = base.crop(replacement_box).getchannel("A").getbbox()
    assert old_text is not None
    cx = base.width / 2
    cy = replacement_box[1] + (old_text[1] + old_text[3]) / 2
    width = round(base.width * .31)
    height = round(width * (y1 - y0) / (x1 - x0))
    mark = Image.new("RGBA", (width * 4, height * 4))
    draw = ImageDraw.Draw(mark)
    for contour in re.findall(r"M[^M]*", symbol):
        numbers = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", contour)))
        points = [((x - x0) * (width * 4 - 1) / (x1 - x0),
                   (y - y0) * (height * 4 - 1) / (y1 - y0))
                  for x, y in zip(numbers[::2], numbers[1::2])]
        draw.polygon(points, fill=(255, 255, 255, 255))
    mark = mark.resize((width, height), Image.Resampling.LANCZOS)
    result = base.copy()
    result.paste((0, 0, 0, 0), replacement_box)
    result.alpha_composite(mark, (round(cx - width / 2), round(cy - height / 2)))
    # Every pixel outside the replaced identifier must remain exactly unchanged.
    for box in ((0, 0, base.width, replacement_box[1]),
                (0, replacement_box[3], base.width, base.height),
                (0, replacement_box[1], replacement_box[0], replacement_box[3]),
                (replacement_box[2], replacement_box[1], base.width, replacement_box[3])):
        assert base.crop(box).tobytes() == result.crop(box).tobytes()

    ET.register_namespace("", NS)
    vector = ET.parse(LOGOS / "sky-sports-main-event-uhd.svg")
    root = vector.getroot()
    root.find(f"{{{NS}}}title").text = "Sky Sports F1 UHD"
    path = root.find(f"{{{NS}}}path")
    contours = re.findall(r"M[^M]*", path.get("d"))
    shared = [p for p in contours if bounds(p)[1] < 263 or bounds(p)[2] - bounds(p)[0] > 1100]
    assert len(shared) == 17
    path.set("d", " ".join(shared))
    x0, y0, x1, y1 = bounds(symbol)
    scale = 1185 * .31 / (x1 - x0)
    tx = 48 + 1185 / 2 - scale * (x0 + x1) / 2
    ty = 334.5 - scale * (y0 + y1) / 2
    group = ET.SubElement(root, f"{{{NS}}}g", {"id": "f1-identifier", "transform": f"translate({tx:.8f} {ty:.8f}) scale({scale:.8f})"})
    ET.SubElement(group, f"{{{NS}}}path", {"fill": "#fff", "d": symbol})
    vector.write(LOGOS / "sky-sports-f1-uhd.svg", encoding="utf-8", xml_declaration=True)
    result.save(target)
    print(f"PNG: {result.size}, RGBA; shared geometry is pixel-identical to Main Event UHD.")
    print("SVG: identical viewBox and 17 unchanged shared contours; F1 mark centered below.")


if __name__ == "__main__":
    main()
