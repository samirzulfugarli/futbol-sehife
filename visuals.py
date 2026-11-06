"""Rəngli Futbol AZ şəkilləri üçün ortaq çəkmə funksiyaları."""
import math
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

# Azərbaycan bayrağının rəngləri + canlı əlavə rənglər
BLUE = (0, 181, 226)
RED = (237, 41, 57)
GREEN = (80, 158, 47)
YELLOW = (255, 214, 10)
ORANGE = (255, 138, 0)
PINK = (255, 61, 129)
PURPLE = (124, 58, 237)
NAVY = (10, 20, 60)

# (yuxarı rəng, aşağı rəng, vurğu rəngi) — hər şəkil üçün fərqli canlı palitra
SCHEMES = [
    ((20, 40, 140), (124, 58, 237), YELLOW),
    ((0, 120, 200), (0, 200, 170), YELLOW),
    ((200, 30, 90), (255, 120, 0), (255, 255, 255)),
    ((10, 110, 60), (60, 190, 90), YELLOW),
    ((90, 30, 170), (255, 61, 129), (120, 255, 220)),
    ((255, 90, 0), (255, 190, 0), NAVY),
]


def font(size, bold=True):
    cands = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in cands:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def gradient(size, top, bottom, diagonal=True):
    w, h = size
    base = Image.new("RGB", size, top)
    px = base.load()
    for y in range(h):
        for x in range(w):
            t = ((x / w) * 0.4 + (y / h) * 0.6) if diagonal else y / h
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base


def fast_gradient(size, top, bottom):
    """Şaquli keçid (sürətli)."""
    w, h = size
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h))


def tricolor(draw, y, w, h=14):
    third = w // 3
    draw.rectangle((0, y, third, y + h), fill=BLUE)
    draw.rectangle((third, y, 2 * third, y + h), fill=RED)
    draw.rectangle((2 * third, y, w, y + h), fill=GREEN)


def ball(draw, cx, cy, r, fill=(255, 255, 255), patch=(20, 20, 40), width=0):
    """Sadə futbol topu: ağ dairə + mərkəzdə və kənarlarda tünd beşbucaq."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=patch, width=max(3, r // 14))

    def pent(x, y, pr, rot=-90):
        pts = [
            (x + pr * math.cos(math.radians(rot + i * 72)), y + pr * math.sin(math.radians(rot + i * 72)))
            for i in range(5)
        ]
        draw.polygon(pts, fill=patch)

    pent(cx, cy, r * 0.36)
    for i in range(5):
        a = math.radians(-90 + i * 72)
        px, py = cx + r * 0.88 * math.cos(a), cy + r * 0.88 * math.sin(a)
        pent(px, py, r * 0.2, rot=-90 + i * 72 + 180)
        # mərkəzlə birləşdirən xətt
        draw.line(
            (cx + r * 0.36 * math.cos(a), cy + r * 0.36 * math.sin(a), px, py),
            fill=patch,
            width=max(2, r // 16),
        )


def confetti(img, accent_colors, seed=0, region=None, count=26):
    """Rəngli dairələr/üçbucaqlar — arxa fonu canlandırır."""
    import random

    rnd = random.Random(seed)
    w, h = img.size
    x0, y0, x1, y1 = region or (0, 0, w, h)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        c = rnd.choice(accent_colors)
        a = rnd.randint(40, 110)
        x, y = rnd.randint(x0, x1), rnd.randint(y0, y1)
        r = rnd.randint(14, 60)
        if rnd.random() < 0.6:
            d.ellipse((x - r, y - r, x + r, y + r), fill=c + (a,))
        else:
            d.polygon([(x, y - r), (x - r, y + r), (x + r, y + r)], fill=c + (a,))
    img.paste(layer, (0, 0), layer)


def pitch_stripes(img, color_a, color_b, y0=0, y1=None, step=90):
    d = ImageDraw.Draw(img)
    y1 = y1 or img.height
    for i, x in enumerate(range(0, img.width, step)):
        d.rectangle((x, y0, x + step, y1), fill=color_a if i % 2 == 0 else color_b)


def boost(photo, color=1.25, contrast=1.08):
    photo = ImageEnhance.Color(photo).enhance(color)
    return ImageEnhance.Contrast(photo).enhance(contrast)


def cover(photo, w, h, focus_top=0.25):
    """Fotonu w×h çərçivəyə sığdırır; üzü kəsməmək üçün yuxarıya doğru fokus."""
    ratio = max(w / photo.width, h / photo.height)
    p = photo.resize((int(photo.width * ratio) + 1, int(photo.height * ratio) + 1), Image.Resampling.LANCZOS)
    left = (p.width - w) // 2
    top = int((p.height - h) * focus_top)
    return p.crop((left, top, left + w, top + h))


def circle_portrait(photo, diameter, ring=(255, 255, 255), ring_w=10):
    """Dairəvi portret (üz üçün yuxarıdan kəsilir) + rəngli halqa."""
    p = cover(photo, diameter, diameter, focus_top=0.1)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter - 1, diameter - 1), fill=255)
    out = Image.new("RGBA", (diameter + 2 * ring_w, diameter + 2 * ring_w), (0, 0, 0, 0))
    od = ImageDraw.Draw(out)
    od.ellipse((0, 0, out.width - 1, out.height - 1), fill=ring + (255,))
    out.paste(p, (ring_w, ring_w), mask)
    return out


def pill(draw, xy, text, fill, fg, f, pad=22):
    x, y = xy
    tw = draw.textbbox((0, 0), text, font=f)[2]
    h = f.size + 26
    draw.rounded_rectangle((x, y, x + tw + 2 * pad, y + h), radius=h // 2, fill=fill)
    draw.text((x + pad, y + 11), text, font=f, fill=fg)
    return x + tw + 2 * pad
