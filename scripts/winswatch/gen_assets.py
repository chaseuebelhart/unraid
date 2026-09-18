"""Generate every PNG the Wins Watch overlays use. Deterministic; re-run any time."""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw
from ww.colors import band, BRAND, DEEP, GOLD, LEAVE_GOLD, RED, GRAY

W, H = 1000, 1500

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

def _line_and_tab(color, plate_w, out, notch=False, plate_h=64, total_h=80):
    im = Image.new("RGBA", (W, total_h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 16], fill=_hex(color))
    x0, y0, x1, y1 = 40, 0, 40 + plate_w, 16 + plate_h
    if notch:
        d.polygon([(x0, y0), (x1, y0), (x1, y1), ((x0 + x1) // 2, y1 - 26), (x0, y1)], fill=_hex(color))
    else:
        d.rounded_rectangle([x0, y0, x1, y1], radius=15, fill=_hex(color))
        d.rectangle([x0, y0, x1, y0 + 20], fill=_hex(color))  # square the top corners
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

def generate(out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    _gradient(W, 240, [(0.0, 0), (0.30, 89), (0.72, 235), (1.0, 235)], out_dir / "bar_bottom.png")
    _gradient(W, 140, [(0.0, 235), (0.30, 235), (0.72, 89), (1.0, 0)], out_dir / "bar_top.png")
    for s in range(101):
        _arc(s, out_dir / f"arc_{s:02d}.png")
    _edge(GRAY, out_dir / "edge_gray.png"); _edge(RED, out_dir / "edge_red.png")
    _line_and_tab(BRAND, 230, out_dir / "tab_lightblue_narrow.png"); _line_and_tab(BRAND, 330, out_dir / "tab_lightblue_wide.png")
    _line_and_tab(DEEP, 230, out_dir / "tab_deepblue_narrow.png"); _line_and_tab(DEEP, 330, out_dir / "tab_deepblue_wide.png")
    _line_and_tab(LEAVE_GOLD, 300, out_dir / "bookmark.png", notch=True, plate_h=96, total_h=112)
    _reel(out_dir / "reel.png")
    return sorted(out_dir.glob("*.png"))

if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch/assets"
    print(f"wrote {len(generate(dest))} files to {dest}")
