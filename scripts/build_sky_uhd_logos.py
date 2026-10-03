"""Logo UHD como el real de Sky: píldora «sports» intacta y «UHD» en una caja de contorno.

La caja usa el mismo trazo que el recuadro inferior del logo normal (4 px gris claro), con
esquinas derechas redondeadas; sus líneas nacen detrás de la píldora. «UHD» va en blanco y
delgado. Todo lo demás sale del logo normal sin tocarlo.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W = Path(__file__).parent
OUT = W / "uhdlogo"
PILL_TOP, PILL_BOTTOM, PILL_RIGHT = 12, 193, 857
LINE = 4
LINE_COLOR = (205, 205, 205, 255)
RADIUS = 14
SS = 4


def text_image(text, cap_height, color):
    size = 10
    while True:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
        box = font.getbbox(text)
        if box[3] - box[1] >= cap_height:
            break
        size += 2
    img = Image.new("RGBA", (box[2] - box[0] + 16, box[3] - box[1] + 16), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((8 - box[0], 8 - box[1]), text, font=font, fill=color,
                             stroke_width=round(cap_height * 0.025), stroke_fill=color)
    return img


def build(normal_path, out_name):
    n = Image.open(normal_path).convert("RGBA")
    w, h = n.size
    pill_h = PILL_BOTTOM - PILL_TOP + 1
    box_w = round(pill_h * 1.40)  # ancho de la caja UHD a la derecha de la píldora
    new_right = PILL_RIGHT + box_w
    extra = new_right - PILL_RIGHT
    out = Image.new("RGBA", (w + extra, h), (0, 0, 0, 0))

    # Caja de contorno (detrás de la píldora), dibujada a 4× para bordes lisos.
    left = PILL_RIGHT - 40
    big = Image.new("RGBA", ((new_right - left + 1) * SS, pill_h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, big.width - 1, big.height - 1), radius=RADIUS * SS,
                        outline=LINE_COLOR, width=LINE * SS, corners=(False, True, True, False))
    cap = round(pill_h * 0.33) * SS
    txt = text_image("UHD", cap, (255, 255, 255, 255))
    inner_left = (PILL_RIGHT - left + 1) * SS
    cx = inner_left + (big.width - inner_left) // 2
    big.alpha_composite(txt, (cx - txt.width // 2, (big.height - txt.height) // 2))
    out.alpha_composite(big.resize((new_right - left + 1, pill_h), Image.LANCZOS), (left, PILL_TOP))

    # Fila de arriba del logo normal encima (la píldora tapa el inicio de las líneas).
    out.alpha_composite(n.crop((0, 0, w, PILL_BOTTOM + 1)), (0, 0))

    # Recuadro inferior alargado con piezas del mismo logo; contenido idéntico y centrado.
    lower_top = PILL_BOTTOM + 1
    out.alpha_composite(n.crop((0, lower_top, 24, h)), (0, lower_top))
    straight = n.crop((30, lower_top, 31, h))
    for x in range(24, new_right - 16):
        out.alpha_composite(straight, (x, lower_top))
    out.alpha_composite(n.crop((PILL_RIGHT - 16, lower_top, w, h)), (new_right - 16, lower_top))
    inner = n.crop((20, lower_top, PILL_RIGHT - 7, 350))
    box = inner.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    out.alpha_composite(inner.crop(box), (20 + box[0] + extra // 2, lower_top + box[1]))
    out.save(OUT / out_name)
    return out


def fit(img, area=150 * 46 * 4, max_h=128, max_w=420):
    box = img.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    t = img.crop(box)
    a = t.width / t.height
    hh = math.sqrt(area / a)
    ww = a * hh
    if hh > max_h:
        hh, ww = max_h, a * max_h
    if ww > max_w:
        ww, hh = max_w, max_w / a
    return t.resize((round(ww), round(hh)), Image.LANCZOS)


f1 = build(W / "lista/logos/sky-sports-f1.png", "sky-sports-f1-uhd_C.png")
me = build(W / "lista/logos/sky-sports-main-event.png", "sky-sports-main-event-uhd_C.png")
big = Image.new("RGBA", (f1.width + 40, f1.height * 2 + 60), (8, 10, 12, 255))
big.alpha_composite(f1, (20, 20))
big.alpha_composite(me, (20, f1.height + 40))
big.save(OUT / "uhd_big6.png")
sheet = Image.new("RGBA", (1000, 380), (8, 10, 12, 255))
for index, img in enumerate([Image.open(W / "lista/logos/sky-sports-f1.png").convert("RGBA"), f1,
                             Image.open(W / "lista/logos/sky-sports-main-event.png").convert("RGBA"), me]):
    logo = fit(img)
    sheet.alpha_composite(logo, (40 + (index // 2) * 520, 40 + (index % 2) * 170 + (128 - logo.height) // 2))
sheet.save(OUT / "uhd_sheet6.png")
print(f1.size)
