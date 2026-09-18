from pathlib import Path
from PIL import Image
import gen_assets

def test_generate_all(tmp_path: Path):
    files = gen_assets.generate(tmp_path)
    names = {f.name for f in files}
    assert {"bar_bottom.png", "bar_top.png", "bookmark_1.png", "bookmark_30.png", "reel.png", "edge_gray.png", "edge_red.png",
            "tab_NewEp_Wed.png", "tab_ReturnsIn_13.png", "tab_Returns_Feb.png", "tab_Returns_2027.png", "tab_Returns_TBA.png"} <= names
    assert sum(n.startswith("tab_") for n in names) == 7 + 23 + 12 + 5 + 1
    assert sum(n.startswith("arc_") for n in names) == 101
    assert Image.open(tmp_path / "bar_bottom.png").size == (1000, 240)
    assert Image.open(tmp_path / "bar_top.png").size == (1920, 269)   # episode canvas is 1920x1080
    assert Image.open(tmp_path / "arc_86.png").size == (220, 130)
    assert Image.open(tmp_path / "reel.png").size == (95, 95)
    bm = Image.open(tmp_path / "bookmark_12.png").convert("RGBA")
    assert bm.width == 1000 and 110 < bm.height < 140
    tab = Image.open(tmp_path / "tab_NewEp_Wed.png").convert("RGBA")
    assert tab.width == 1000 and 85 < tab.height < 95
    # plate fits its text: plate spans x=40..(text+52); the widest tab is wider than the narrowest
    def plate_right(im):
        return max(x for x in range(1000) if im.getpixel((x, 40))[3] > 0)
    assert plate_right(Image.open(tmp_path / "tab_ReturnsIn_13.png").convert("RGBA")) > plate_right(tab) + 100
    assert 40 + 281 + 52 <= plate_right(tab) < 40 + 281 + 52 + 45    # 'NEW EP WED' ~281px + 0.1em tracking + 52 padding
    assert tab.getpixel((500, 8))[:3] == (0x5a, 0xc8, 0xfa) and tab.getpixel((500, 40))[3] == 0   # line only, past the plate
    assert sum(n.startswith("chip_") for n in names) == 168 == sum(n.startswith("chipl_") for n in names)
    row = Image.open(tmp_path / "chip_k4_dvhdr_atmos.png").convert("RGBA")
    assert row.height < 50 and 450 < row.width < 620          # cap-height tight, three chips wide
    assert row.getpixel((0, 0))[3] == 0                        # transparent background
    big = Image.open(tmp_path / "chipl_k4_dvhdr_atmos.png").convert("RGBA")
    assert 1.8 < big.width / row.width < 2.0                   # episode renders are 1.92x, drawn natively

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
    assert t.getpixel((500, 267))[3] < 20
