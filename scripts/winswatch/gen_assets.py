"""Generate every PNG the Wins Watch overlays use. Deterministic; re-run any time."""
import math, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from ww.colors import band, BRAND, DEEP, GOLD, LEAVE_GOLD, LEAVE_INK, INK, WHITE, RED, GRAY, CODEC
from ww.chips import chip_combos
from ww.buckets import DOW, MON, tab_years

W = 1000
EP_W, EP_SCALE = 1920, 1.92   # Kometa draws episode stills on a 1920x1080 canvas: episode assets are 1.92x the poster ones
HERE = Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch"
FONT = HERE / "fonts/Avenir_95_Black.ttf"
PAW = HERE / "src/paw_512.png"                 # white RGBA silhouette, tinted per band on the score plate
CHIP_PX, CHIP_TRACK, CHIP_GAP = 60, 0.1, 39   # font px, letter-spacing (em), gap between chips (px)
EDGE = 26                                     # status edge line height (2.6u); tabs hang from its bottom edge
BAR_STOPS = [(0.0, 0), (0.30, 89), (0.72, 235), (1.0, 235)]   # bottom bar fade, poster and episode

def _hex(h: str, a: int = 255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

def _alpha_at(stops, f: float) -> float:
    for (y0, a0), (y1, a1) in zip(stops, stops[1:]):
        if y0 <= f <= y1:
            return a0 + (a1 - a0) * ((f - y0) / (y1 - y0) if y1 > y0 else 0)
    return stops[-1][1]

def _gradient(width, height, stops, out):
    """stops: list of (y_fraction, alpha 0..255) piecewise-linear. Black."""
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0)); px = im.load()
    for y in range(height):
        a = int(_alpha_at(stops, y / (height - 1)))
        for x in range(width):
            px[x, y] = (0, 0, 0, a)
    im.save(out)

def _glow(layer: Image.Image, radius: float, alpha: float = 0.9) -> Image.Image:
    """Dark glow: a black copy of `layer`'s alpha, blurred, at `alpha` strength."""
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v * alpha))
    g = Image.new("RGBA", layer.size, (0, 0, 0, 255)); g.putalpha(a)
    return g

def _score_plate(score: int, out: Path):
    """The locked score block: 'WINS <paw>' / 'RANK' in white over the score in the band colour, on a black plate
    flush with the poster's right edge (right corners square, TL r25 / BL r12, feathered top). Sizes in poster px:
    label 45px (0.14em tracking), paw 52px, score 83px, padding 42 top / 0 sides (+6 safety) / 12 bottom."""
    S = 2
    f45, f83 = ImageFont.truetype(str(FONT), 45 * S), ImageFont.truetype(str(FONT), 83 * S)
    cap45, cap83 = -f45.getbbox("H", anchor="ls")[1], -f83.getbbox("H", anchor="ls")[1]
    track, paw_px, paw_gap = 0.14 * 45 * S, 52 * S, 0.18 * 45 * S
    col = band(score); text = str(score)
    w1 = _tracked_width("WINS", f45, track) + paw_gap + paw_px
    w2 = _tracked_width("RANK", f45, track)
    w3 = f83.getlength(text)
    pad = 6 * S
    pw = int(math.ceil(max(w1, w2, w3))) + 2 * pad
    base1 = 42 * S + cap45                       # line 1 baseline (cap top = 42px top padding)
    base2 = base1 + round(1.05 * 45 * S)          # line pitch 1.05 x 45px
    base3 = base2 + 6 * S + cap83                 # score cap top 6px below RANK's baseline
    ph = base3 + 12 * S
    # plate: vertical fade (solid black with a short feathered top) clipped to the corner shape
    plate = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); px = plate.load()
    fade = [(0.0, 0), (0.14, 184), (0.38, 255), (1.0, 255)]
    for y in range(ph):
        a = int(round(_alpha_at(fade, y / (ph - 1))))
        for x in range(pw):
            px[x, y] = (0, 0, 0, a)
    m1 = Image.new("L", (pw, ph), 0); ImageDraw.Draw(m1).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=25 * S, fill=255, corners=(True, False, False, False))
    m2 = Image.new("L", (pw, ph), 0); ImageDraw.Draw(m2).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=12 * S, fill=255, corners=(False, False, False, True))
    plate.putalpha(ImageChops.multiply(plate.getchannel("A"), ImageChops.multiply(m1, m2)))
    # content layers (drawn on their own canvases so the glow is blurred from the exact glyph alpha)
    labels = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(labels)
    x1 = (pw - w1) / 2
    xe = _tracked(d, x1, base1, "WINS", f45, _hex(WHITE), track)
    _tracked(d, (pw - w2) / 2, base2, "RANK", f45, _hex(WHITE), track)
    paw = Image.open(PAW).convert("RGBA").resize((paw_px, paw_px), Image.LANCZOS)
    tint = Image.new("RGBA", paw.size, _hex(col)); tint.putalpha(paw.getchannel("A"))
    py = round(base1 - cap45 / 2 - paw_px / 2)   # centred on the cap height
    labels.alpha_composite(tint, (round(xe + paw_gap), py))
    num = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(num).text(((pw - w3) / 2, base3), text, font=f83, fill=_hex(col), anchor="ls")
    im = plate
    im.alpha_composite(_glow(labels, 6 * S)); im.alpha_composite(labels)
    im.alpha_composite(_glow(num, 10 * S)); im.alpha_composite(num)
    im = im.resize((pw // S, ph // S), Image.LANCZOS)
    ImageDraw.Draw(im).line([(0, 0), (im.width, 0)], fill=(0, 0, 0, 0))   # keep the feathered top's first row fully clear after resampling
    im.save(out)

def _tracked(d, x, baseline, text, font, fill, track):
    """Draw text with letter-spacing `track` px; returns the x after the last glyph (no trailing spacing)."""
    for i, c in enumerate(text):
        d.text((x, baseline), c, font=font, fill=fill, anchor="ls"); x += font.getlength(c) + (track if i < len(text) - 1 else 0)
    return x

def _tracked_width(text, font, track):
    return sum(font.getlength(c) for c in text) + track * (len(text) - 1)

def _line_and_tab(color, ink, parts, out, bookmark=False):
    """Status edge line (26px, full width) + a tab hanging from its bottom edge at x=40 with the text baked in.
    parts: [(text, font_px), ...] drawn on one baseline, 0.1em tracking (prefix 42px, variable part 46px, count 57px).
    Padding 18/29/15 (top/sides/bottom); bookmark=True is the LEAVING plate: 20/29/46, same plain rounded shape."""
    fonts = {px: ImageFont.truetype(str(FONT), px) for _, px in parts}
    track = 4.2
    gap = fonts[parts[0][1]].getlength(" ") + track     # word gap between parts (the count sits between two words)
    text_w = sum(_tracked_width(t, fonts[px], track) for t, px in parts) + gap * (len(parts) - 1)
    plate_w = int(round(text_w)) + 58
    x0, x1 = 40, 40 + plate_w
    top_pad = 20 if bookmark else 18
    cap = 33                                  # cap height of the 46px face; every part shares its baseline
    plate_top = EDGE - 1                      # overlap the line by 1px so line + tab read as one unit
    baseline = plate_top + top_pad + cap
    y1 = baseline + 13 + (46 if bookmark else 15)       # padding below the 1.5 line box, as in the artifact
    im = Image.new("RGBA", (W, y1 + 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, EDGE - 1], fill=_hex(color))
    d.rounded_rectangle([x0, plate_top, x1, y1], radius=15, fill=_hex(color))
    d.rectangle([x0, plate_top, x1, plate_top + 20], fill=_hex(color))  # square the top corners
    x = x0 + 29
    for t, px in parts:
        x = _tracked(d, x, baseline, t, fonts[px], _hex(ink), track) + gap
    im.save(out)

def _edge(color, out):
    im = Image.new("RGBA", (W, EDGE), _hex(color)); im.save(out)

def _reel(out):
    S = 4; n = 95 * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, n - 1, n - 1], fill=(0, 0, 0, 184), outline=_hex(GOLD), width=6 * S)
    inset = 16 * S
    for k in range(12):  # dotted inner ring
        a = 2 * math.pi * k / 12
        cx, cy = n / 2 + (n / 2 - inset) * math.cos(a), n / 2 + (n / 2 - inset) * math.sin(a)
        rr = 3.2 * S; d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=_hex(GOLD))
    im.resize((95, 95), Image.LANCZOS).save(out)

def chip_metrics(scale: float = 1.0) -> tuple[int, int, int]:
    """(cap height, descent, canvas height) of a chip row at this scale. gen_overlays uses the descent to keep the
    chip baseline where the spec puts it after the canvas grew to hold descenders ('p' in 1080p/720p)."""
    px = round(CHIP_PX * scale)
    font = ImageFont.truetype(str(FONT), px)
    cap = -font.getbbox("H", anchor="ls")[1]
    descent = font.getbbox("pgyj", anchor="ls")[3]
    return cap, descent, cap + 1 + descent + 2

def _chip_row(keys, out, scale=1.0):
    """One PNG for a whole codec row, e.g. ('k4','dvhdr','atmos') -> '4K DV·HDR ATMOS' with per-chip color,
    0.1em tracking and 39px gaps. Canvas: top edge = cap top, baseline at cap+1, then the font's full descent + 2px."""
    px = round(CHIP_PX * scale); gap = round(CHIP_GAP * scale)
    font = ImageFont.truetype(str(FONT), px)
    track = px * CHIP_TRACK
    cap, descent, height = chip_metrics(scale)
    base = cap + 1
    runs = []
    for k in keys:
        label, color = CODEC[k]
        widths = [font.getlength(c) for c in label]
        runs.append((label, color, widths, sum(widths) + track * (len(label) - 1)))
    total = int(math.ceil(sum(r[3] for r in runs) + gap * (len(runs) - 1))) + 2
    im = Image.new("RGBA", (total, height), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0.0
    for label, color, widths, w in runs:
        for c, cw in zip(label, widths):
            d.text((x, base), c, font=font, fill=_hex(color), anchor="ls"); x += cw + track
        x += gap - track
    im.save(out)

def tab_texts() -> dict:
    """label -> text parts for every status tab: [(prefix, 42), (variable part, 46)] — the variable part reads as the
    'bold' word (we only ship one weight). Keys are the Plex labels airdates.py writes."""
    t = {f"NewEp_{d}": [("NEW EP", 42), (d.upper(), 46)] for d in DOW}
    t.update({f"ReturnsIn_{i}": [("RETURNS IN", 42), (f"{i} DAYS", 46)] for i in range(8, 31)})
    t.update({f"Returns_{m}": [("RETURNS", 42), (m.upper(), 46)] for m in MON})
    t.update({f"Returns_{y}": [("RETURNS", 42), (str(y), 46)] for y in tab_years()})
    t["Returns_TBA"] = [("RETURNS", 42), ("TBA", 46)]
    return t

def generate(out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for old in list(out_dir.glob("arc_*.png")) + [out_dir / "bar_top.png"]:
        old.unlink(missing_ok=True)                                          # retired by the locked look (task 11)
    _gradient(W, 240, BAR_STOPS, out_dir / "bar_bottom.png")
    _gradient(EP_W, round(140 * EP_SCALE), BAR_STOPS, out_dir / "bar_bottom_ep.png")   # episodes: same bar, bottom of the still
    for s in range(101):
        _score_plate(s, out_dir / f"score_{s:02d}.png")
    _edge(GRAY, out_dir / "edge_gray.png"); _edge(RED, out_dir / "edge_red.png")
    for label, parts in tab_texts().items():
        color, ink = (BRAND, INK) if label.startswith("NewEp_") else (DEEP, WHITE)
        _line_and_tab(color, ink, parts, out_dir / f"tab_{label}.png")
    for i in range(1, 31):
        _line_and_tab(LEAVE_GOLD, LEAVE_INK, [("LEAVING", 42), (str(i), 57), ("DAY" if i == 1 else "DAYS", 46)],
                      out_dir / f"bookmark_{i}.png", bookmark=True)
    _reel(out_dir / "reel.png")
    for combo in chip_combos():
        keys = [k for k in combo if k]; name = "_".join(k or "x" for k in combo)
        _chip_row(keys, out_dir / f"chip_{name}.png")                       # movie posters (1000x1500)
        _chip_row(keys, out_dir / f"chipl_{name}.png", scale=EP_SCALE)      # episode stills (1920x1080)
    return sorted(out_dir.glob("*.png"))

if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "assets"
    print(f"wrote {len(generate(dest))} files to {dest}")
