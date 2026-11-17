"""Drawing helpers: easing, cached text, glass cards, ghosts (fake motion blur)."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def ease_out_expo(t):
    t = clamp(t); return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)

def ease_out_back(t, k=1.7):
    t = clamp(t); return 1 + (k + 1) * (t - 1) ** 3 + k * (t - 1) ** 2

def ease_in_out_cubic(t):
    t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2

def ease_in_cubic(t):
    t = clamp(t); return t ** 3

EASE = {"ease_out_expo": ease_out_expo, "ease_out_back": ease_out_back,
        "ease_in_out_cubic": ease_in_out_cubic}

def lerp(a, b, t):
    return a + (b - a) * t

def hexrgb(h, a=255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

def envelope(t, t0, t1, fin=0.25, fout=0.25):
    """0..1 visibility: fade in after t0, fade out before t1."""
    if t < t0 or t > t1:
        return 0.0
    return clamp((t - t0) / fin) * clamp((t1 - t) / fout)


# ---------------------------------------------------------------- fonts / text
_FONTS = {}
def font(path, size):
    k = (path, size)
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(path, size)
    return _FONTS[k]


@lru_cache(maxsize=512)
def text_img(text, path, size, fill, shadow=True, stroke=0, stroke_fill=(0, 0, 0, 255), glow=None):
    """Render text once (with drop shadow / optional glow) and cache it."""
    f = font(path, size)
    bb = f.getbbox(text, stroke_width=stroke)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(size * 0.35) + (30 if glow else 0)
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((pad - bb[0], pad - bb[1]), text, font=f, fill=glow)
        g = g.filter(ImageFilter.GaussianBlur(size * 0.18))
        im.alpha_composite(g); im.alpha_composite(g)
    if shadow:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).text((pad - bb[0] + size * 0.04, pad - bb[1] + size * 0.06), text, font=f,
                               fill=(0, 0, 0, 150))
        s = s.filter(ImageFilter.GaussianBlur(max(2, size * 0.06)))
        im.alpha_composite(s)
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def text_size(text, path, size):
    f = font(path, size); bb = f.getbbox(text); return bb[2] - bb[0], bb[3] - bb[1]


def paste(layer, im, cx, cy, alpha=1.0, scale=1.0):
    """Paste an RGBA image centred at (cx, cy) with opacity and scale."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    layer.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def paste_tl(layer, im, x, y, alpha=1.0):
    if alpha <= 0.003:
        return
    if alpha < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    layer.alpha_composite(im, (int(x), int(y)))


def ghost_paste(layer, im, pos_fn, t, alpha=1.0, scale_fn=None, n=4, dt=1 / 60):
    """Fake motion blur: faded copies at earlier positions when the element moves fast."""
    x0, y0 = pos_fn(t)
    for i in range(n, 0, -1):
        x, y = pos_fn(t - i * dt)
        if abs(x - x0) + abs(y - y0) < 6:
            continue
        s = scale_fn(t - i * dt) if scale_fn else 1.0
        paste(layer, im, x, y, alpha * (0.22 / i), s)
    paste(layer, im, x0, y0, alpha, scale_fn(t) if scale_fn else 1.0)


# ---------------------------------------------------------------- glass card
@lru_cache(maxsize=64)
def glass_card(w, h, r=28, border=(0, 245, 212, 140), fill=(13, 17, 23, 222)):
    pad = 40
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([pad + 6, pad + 14, pad + w + 6, pad + h + 14], r, fill=(0, 0, 0, 120))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad, pad, pad + w, pad + h], r, fill=fill, outline=border, width=3)
    # top sheen
    sheen = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sheen).rounded_rectangle([pad + 3, pad + 3, pad + w - 3, pad + 3 + h * 0.22], r, fill=(255, 255, 255, 12))
    im.alpha_composite(sheen)
    return im


def card(layer, x, y, w, h, alpha=1.0, **kw):
    paste_tl(layer, glass_card(w, h, **kw), x - 40, y - 40, alpha)


def pill(text, path, size, fg, bg, padx=26, pady=12):
    w, h = text_size(text, path, size)
    im = Image.new("RGBA", (w + padx * 2, h + pady * 2 + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], im.height // 2, fill=bg)
    f = font(path, size); bb = f.getbbox(text)
    d.text((padx - bb[0], pady - bb[1] + 3), text, font=f, fill=fg)
    return im
