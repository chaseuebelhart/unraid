from pathlib import Path
from PIL import Image
import gen_assets

def test_generate_all(tmp_path: Path):
    files = gen_assets.generate(tmp_path)
    names = {f.name for f in files}
    assert {"bar_bottom.png", "bar_top.png", "bookmark.png", "reel.png", "edge_gray.png", "edge_red.png",
            "tab_lightblue_narrow.png", "tab_deepblue_wide.png"} <= names
    assert sum(n.startswith("arc_") for n in names) == 101
    assert Image.open(tmp_path / "bar_bottom.png").size == (1000, 240)
    assert Image.open(tmp_path / "bar_top.png").size == (1000, 140)
    assert Image.open(tmp_path / "arc_86.png").size == (220, 130)
    assert Image.open(tmp_path / "reel.png").size == (95, 95)
    assert Image.open(tmp_path / "bookmark.png").size == (1000, 112)
    assert Image.open(tmp_path / "tab_deepblue_wide.png").size == (1000, 80)

def test_arc_fill_and_band_color(tmp_path: Path):
    gen_assets.generate(tmp_path)
    # the arc's left end (score 0 side) is painted for any score > 0; right end only for ~100
    a86 = Image.open(tmp_path / "arc_86.png").convert("RGBA")
    a20 = Image.open(tmp_path / "arc_20.png").convert("RGBA")
    # sample a point on the left end of the arc ring
    # (18, 118) sits on the LANCZOS-downscaled anti-aliasing fringe of the ring's
    # left foot rather than the solid stroke; (22, 110) is on the same foot but
    # squarely inside the solid color, per task-2's guidance to adjust sample
    # coordinates rather than the arc geometry.
    lx, ly = 22, 110
    assert a86.getpixel((lx, ly))[:3] == (0xf5, 0xc5, 0x18)   # gold at 86
    assert a20.getpixel((lx, ly))[:3] == (0x8a, 0x94, 0xa6)   # gray at 20
    # right end: 86 filled? 86% of the arc ends before the right foot, so the right foot is track only (dim)
    rx, ry = 202, 118
    assert a86.getpixel((rx, ry))[3] < 255 or a86.getpixel((rx, ry))[:3] != (0xf5, 0xc5, 0x18)

def test_bar_gradient_direction(tmp_path: Path):
    gen_assets.generate(tmp_path)
    b = Image.open(tmp_path / "bar_bottom.png").convert("RGBA")
    assert b.getpixel((500, 2))[3] < 20          # transparent at top
    assert b.getpixel((500, 238))[3] > 230       # near-opaque at bottom
    t = Image.open(tmp_path / "bar_top.png").convert("RGBA")
    assert t.getpixel((500, 2))[3] > 230
    assert t.getpixel((500, 138))[3] < 20
