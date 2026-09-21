from pathlib import Path
from PIL import Image
import gen_assets

def test_generate_all(tmp_path: Path):
    files = gen_assets.generate(tmp_path)
    names = {f.name for f in files}
    assert {"bar_bottom.png", "bar_bottom_ep.png", "bookmark_1.png", "bookmark_30.png", "reel.png", "edge_gray.png", "edge_red.png",
            "tab_NewEp_Wed.png", "tab_ReturnsIn_13.png", "tab_Returns_Feb.png", "tab_Returns_2027.png", "tab_Returns_TBA.png"} <= names
    assert sum(n.startswith("tab_") for n in names) == 7 + 23 + 12 + 7 + 1   # NewEp, ReturnsIn, month, 7 years, TBA
    assert sum(n.startswith("score_") for n in names) == 101 and not any(n.startswith("arc_") for n in names)
    assert "bar_top.png" not in names                          # episode bar moved to the bottom (task 11)
    assert Image.open(tmp_path / "bar_bottom.png").size == (1000, 240)
    assert Image.open(tmp_path / "bar_bottom_ep.png").size == (1920, 269)   # episode canvas is 1920x1080
    assert Image.open(tmp_path / "reel.png").size == (95, 95)
    bm = Image.open(tmp_path / "bookmark_12.png").convert("RGBA")
    assert bm.width == 1000 and bm.height == Image.open(tmp_path / "tab_NewEp_Wed.png").height   # LEAVING plate = tab height
    tab = Image.open(tmp_path / "tab_NewEp_Wed.png").convert("RGBA")
    assert tab.width == 1000 and 100 < tab.height < 112
    # plate fits its text: plate spans x=40..(text+58); the widest tab is wider than the narrowest
    def plate_right(im):
        return max(x for x in range(1000) if im.getpixel((x, 50))[3] > 0)
    assert plate_right(Image.open(tmp_path / "tab_ReturnsIn_13.png").convert("RGBA")) > plate_right(tab) + 100
    assert 40 + 300 + 58 <= plate_right(tab) < 40 + 300 + 58 + 45    # 'NEW EP' 42px + 'WED' 46px ~300px + tracking + 58 padding
    assert tab.getpixel((500, 8))[:3] == (0x5a, 0xc8, 0xfa) and tab.getpixel((500, 25))[3] == 255   # 26px line ...
    assert tab.getpixel((500, 26))[3] == 0 and tab.getpixel((500, 50))[3] == 0                        # ... only, past the plate
    assert tab.getpixel((60, 26))[3] == 255 and tab.getpixel((60, tab.height - 3))[3] == 255          # tab hangs from the line
    assert bm.getpixel((300, bm.height - 3))[3] == 255 and bm.getpixel((300, bm.height - 40))[3] == 255   # LEAVING: no notch
    assert sum(n.startswith("chip_") for n in names) == 168 == sum(n.startswith("chipl_") for n in names)
    row = Image.open(tmp_path / "chip_k4_dvhdr_atmos.png").convert("RGBA")
    assert row.height < 65 and 580 < row.width < 800          # cap-height tight, three 60px chips wide
    assert row.getpixel((0, 0))[3] == 0                        # transparent background
    big = Image.open(tmp_path / "chipl_k4_dvhdr_atmos.png").convert("RGBA")
    assert 1.8 < big.width / row.width < 2.0                   # episode renders are 1.92x, drawn natively

def test_chip_descenders_not_clipped(tmp_path: Path):
    gen_assets.generate(tmp_path)
    for name in ("chip_p1080_x_ddp.png", "chipl_p1080_x_ddp.png", "chip_p720_x_x.png"):
        im = Image.open(tmp_path / name).convert("RGBA")
        bottom = [im.getpixel((x, y))[3] for y in (im.height - 2, im.height - 1) for x in range(im.width)]
        assert max(bottom) == 0, f"{name}: descender runs into the canvas edge"
        cap, descent, height = gen_assets.chip_metrics(1.0 if name.startswith("chip_") else gen_assets.EP_SCALE)
        assert im.height == height == cap + 1 + descent + 2
        # the 'p' really does descend below the baseline (row cap+1) into the reserved band
        below = [im.getpixel((x, y))[3] for y in range(cap + 3, cap + 1 + descent) for x in range(im.width)]
        assert max(below) > 0

def test_tab_years_follow_today(tmp_path: Path):
    gen_assets.generate(tmp_path)
    from ww.buckets import tab_years
    for y in tab_years():
        assert (tmp_path / f"tab_Returns_{y}.png").exists()

def test_score_plate(tmp_path: Path):
    gen_assets.generate(tmp_path)
    p86 = Image.open(tmp_path / "score_86.png").convert("RGBA")
    assert 180 < p86.width < 260 and 170 < p86.height < 230
    # content is flush with the right edge (glyph pixels in the last few columns), 6px safety on the left only
    assert any(p86.getpixel((p86.width - 1, y))[:3] != (0, 0, 0) for y in range(p86.height))
    assert all(max(p86.getpixel((3, y))[:3]) < 40 for y in range(p86.height) if p86.getpixel((3, y))[3] == 255)
    # flush box: the right-most column is opaque near the bottom (square right corners), the top row is transparent (fade)
    assert p86.getpixel((p86.width - 1, p86.height - 5))[3] == 255
    assert all(p86.getpixel((x, 0))[3] == 0 for x in range(p86.width))
    assert p86.getpixel((0, p86.height - 1))[3] == 0 and p86.getpixel((0, 5))[3] == 0 and p86.getpixel((0, 100))[3] == 255   # rounded left corners (r12 / r25), straight left side between
    def has(im, rgb, tol=12):
        return any(all(abs(px[i] - rgb[i]) <= tol for i in range(3)) and px[3] > 200 for px in im.get_flattened_data())
    gold = (0xf5, 0xc5, 0x18)
    assert has(Image.open(tmp_path / "score_90.png").convert("RGBA"), gold)
    assert not has(Image.open(tmp_path / "score_50.png").convert("RGBA"), gold)
    assert has(Image.open(tmp_path / "score_50.png").convert("RGBA"), (0x8a, 0x94, 0xa6))   # gray band
    assert has(Image.open(tmp_path / "score_80.png").convert("RGBA"), (0x5a, 0xc8, 0xfa))   # blue band
    assert has(p86, (255, 255, 255))                                                        # WINS / RANK stay white
    # every plate shares the height (layout is cap-height based, not per-digit)
    assert len({Image.open(tmp_path / f"score_{s:02d}.png").size[1] for s in (0, 7, 50, 100)}) == 1

def test_bar_gradient_direction(tmp_path: Path):
    gen_assets.generate(tmp_path)
    b = Image.open(tmp_path / "bar_bottom.png").convert("RGBA")
    assert b.getpixel((500, 2))[3] < 20          # transparent at top
    assert b.getpixel((500, 238))[3] > 230       # near-opaque at bottom
    t = Image.open(tmp_path / "bar_bottom_ep.png").convert("RGBA")
    assert t.getpixel((500, 2))[3] < 20            # episode bar: same fade, bottom of the still
    assert t.getpixel((500, 267))[3] > 230
