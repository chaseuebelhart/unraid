"""Generate every PNG the Wins Watch overlays use. Deterministic; re-run any time."""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from ww.colors import band, BRAND, DEEP, GOLD, LEAVE_GOLD, LEAVE_INK, INK, WHITE, RED, GRAY, CODEC
from ww.chips import chip_combos
from ww.buckets import DOW, MON

W, H = 1000, 1500
EP_W, EP_SCALE = 1920, 1.92   # Kometa draws episode stills on a 1920x1080 canvas: episode assets are 1.92x the poster ones
FONT = Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch/fonts/Avenir_95_Black.ttf"
CHIP_PX, CHIP_TRACK, CHIP_GAP = 46, 0.1, 30   # font px, letter-spacing (em), gap between chips (px)

def _hex(h: str, a: int = 255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

def _gradient(width, height, stops, out):
    """stops: list of (y_fraction, alpha 0..255) piecewise-linear. Black."""
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0)); px = im.load()
    for y in range(height):
        f = y / (height - 1)
        for (y0, a0), (y1, a1) in zip(stops, stops[1:]):
            if y0 <= f <= y1:
                a = a0 + (a1 - a0) * ((f - y0) / (y1 - y0) if y1 > y0 else 0); break
        for x in range(width):
            px[x, y] = (0, 0, 0, int(a))
    im.save(out)

def _arc(score: int, out: Path):
    """220x130 half-circle gauge. Track (remainder) + fill in band color, halo baked in."""
    S = 4  # supersample
    w, h = 220 * S, 130 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = w // 2, h - 12 * S, 92 * S
    bbox = [cx - r, cy - r, cx + r, cy + r]
    col = band(score)
    track = _hex(GOLD, 97) if score >= 85 else (255, 255, 255, 36)
    halo = (0, 0, 0, 217)
    d.arc(bbox, 180, 360, fill=halo, width=int(15.6 * S))                     # halo (5.4u wider than stroke)
    d.arc(bbox, 180, 360, fill=(8, 10, 14, 235), width=int(9 * S))              # dark base so track reads on white art
    d.arc(bbox, 180, 360, fill=track, width=int(9 * S))
    if score > 0:
        d.arc(bbox, 180, 180 + 180 * score / 100, fill=_hex(col), width=int(9 * S))
    im = im.resize((220, 130), Image.LANCZOS); im.save(out)

def _tracked(d, x, baseline, text, font, fill, track):
    """Draw text with letter-spacing `track` px; returns the x after the last glyph (no trailing spacing)."""
    for i, c in enumerate(text):
        d.text((x, baseline), c, font=font, fill=fill, anchor="ls"); x += font.getlength(c) + (track if i < len(text) - 1 else 0)
    return x

def _tracked_width(text, font, track):
    return sum(font.getlength(c) for c in text) + track * (len(text) - 1)

def _line_and_tab(color, ink, parts, out, notch=False):
    """Status edge line (16px, full width) + a tab hanging from it at x=40 with the text baked in.
    parts: [(text, font_px), ...] drawn on one baseline, 0.1em tracking, padding 16/26/14 (spec §2.2).
    notch=True is the LEAVING bookmark: padding 18/26/42 with a 26px notch cut from the bottom (§2.5)."""
    fonts = {px: ImageFont.truetype(str(FONT), px) for _, px in parts}
    track = 4.2
    gap = fonts[parts[0][1]].getlength(" ") + track     # word gap between parts (the 52px count sits between two words)
    text_w = sum(_tracked_width(t, fonts[px], track) for t, px in parts) + gap * (len(parts) - 1)
    plate_w = int(round(text_w)) + 52
    x0, x1 = 40, 40 + plate_w
    top_pad = 18 if notch else 16
    cap = 30                                  # cap height of the 42px face; the 52px count shares the baseline
    baseline = 16 + top_pad + cap
    y1 = baseline + 12 + (42 if notch else 14)          # padding below the 1.5 line box, as in the artifact
    im = Image.new("RGBA", (W, y1 + 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 16], fill=_hex(color))
    if notch:
        d.polygon([(x0, 0), (x1, 0), (x1, y1), ((x0 + x1) // 2, y1 - 26), (x0, y1)], fill=_hex(color))
    else:
        d.rounded_rectangle([x0, 0, x1, y1], radius=15, fill=_hex(color))
        d.rectangle([x0, 0, x1, 20], fill=_hex(color))  # square the top corners
    x = x0 + 26
    for t, px in parts:
        x = _tracked(d, x, baseline, t, fonts[px], _hex(ink), track) + gap
    im.save(out)

def _edge(color, out):
    im = Image.new("RGBA", (W, 16), _hex(color)); im.save(out)

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

def _chip_row(keys, out, scale=1.0):
    """One PNG for a whole codec row, e.g. ('k4','dvhdr','atmos') -> '4K DV·HDR ATMOS' with per-chip color,
    0.1em tracking and 30px gaps. Canvas is cap-height tight: top edge = cap top, baseline 4px above the bottom."""
    px = round(CHIP_PX * scale); gap = round(CHIP_GAP * scale)
    font = ImageFont.truetype(str(FONT), px)
    track = px * CHIP_TRACK
    cap = -font.getbbox("H", anchor="ls")[1]
    base = cap + 1
    runs = []
    for k in keys:
        label, color = CODEC[k]
        widths = [font.getlength(c) for c in label]
        runs.append((label, color, widths, sum(widths) + track * (len(label) - 1)))
    total = int(math.ceil(sum(r[3] for r in runs) + gap * (len(runs) - 1))) + 2
    im = Image.new("RGBA", (total, base + 5), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0.0
    for label, color, widths, w in runs:
        for c, cw in zip(label, widths):
            d.text((x, base), c, font=font, fill=_hex(color), anchor="ls"); x += cw + track
        x += gap - track
    im.save(out)

def tab_texts() -> dict:
    """label -> text parts for every status tab. Keys are the Plex labels airdates.py writes."""
    t = {f"NewEp_{d}": [(f"NEW EP {d.upper()}", 42)] for d in DOW}
    t.update({f"ReturnsIn_{i}": [(f"RETURNS IN {i} DAYS", 42)] for i in range(8, 31)})
    t.update({f"Returns_{m}": [(f"RETURNS {m.upper()}", 42)] for m in MON})
    t.update({f"Returns_{y}": [(f"RETURNS {y}", 42)] for y in range(2026, 2031)})
    t["Returns_TBA"] = [("RETURNS TBA", 42)]
    return t

def generate(out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    _gradient(W, 240, [(0.0, 0), (0.30, 89), (0.72, 235), (1.0, 235)], out_dir / "bar_bottom.png")
    _gradient(EP_W, round(140 * EP_SCALE), [(0.0, 235), (0.30, 235), (0.72, 89), (1.0, 0)], out_dir / "bar_top.png")   # episodes
    for s in range(101):
        _arc(s, out_dir / f"arc_{s:02d}.png")
    _edge(GRAY, out_dir / "edge_gray.png"); _edge(RED, out_dir / "edge_red.png")
    for label, parts in tab_texts().items():
        color, ink = (BRAND, INK) if label.startswith("NewEp_") else (DEEP, WHITE)
        _line_and_tab(color, ink, parts, out_dir / f"tab_{label}.png")
    for i in range(1, 31):
        _line_and_tab(LEAVE_GOLD, LEAVE_INK, [("LEAVING", 42), (str(i), 52), ("DAY" if i == 1 else "DAYS", 42)],
                      out_dir / f"bookmark_{i}.png", notch=True)
    _reel(out_dir / "reel.png")
    for combo in chip_combos():
        keys = [k for k in combo if k]; name = "_".join(k or "x" for k in combo)
        _chip_row(keys, out_dir / f"chip_{name}.png")                       # movie posters (1000x1500)
        _chip_row(keys, out_dir / f"chipl_{name}.png", scale=EP_SCALE)      # episode stills (1920x1080)
    return sorted(out_dir.glob("*.png"))

if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch/assets"
    print(f"wrote {len(generate(dest))} files to {dest}")
