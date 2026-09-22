"""Generate the collection card art for every Wins Watch Home row (personal, trending, new, popular,
leaving, theme, seasonal), and (Step 5) upload the ones we own to the matching Plex collections."""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 1500
HERE = Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch"
TITLE_FONT = HERE / "fonts/BricolageGrotesque[opsz,wdth,wght].ttf"
EYEBROW_FONT = HERE / "fonts/Manrope[wght].ttf"
PAW = HERE / "src/paw_512.png"

# slug -> (kind, emoji, title). Every Home row, incl. the generic personal "byw" (Because you watched)
# card, every theme slug and every seasonal card.
CARDS = {
    # personal (Shortlist, per person)
    "for-you-movies": ("personal", "✨", "Movies for you"),
    "for-you-shows": ("personal", "✨", "Shows for you"),
    "byw": ("personal", "\U0001F3AF", "Because you watched"),
    # trending (Kometa mdblist_list)
    "trending-movies": ("trending", "\U0001F525", "Trending Movies"),
    "trending-shows": ("trending", "\U0001F525", "Trending Shows"),
    # new (ours)
    "new-movies": ("new", "\U0001F4E5", "New Movies · Your Requests"),
    "new-shows": ("new", "\U0001F4E5", "New Shows · Your Requests"),
    # popular (Shortlist, shared)
    "popular-movies": ("popular", "\U0001F465", "Popular Movies on Wins Watch"),
    "popular-shows": ("popular", "\U0001F465", "Popular Shows on Wins Watch"),
    # leaving (Maintainerr)
    "leaving-movies": ("leaving", "⏳", "Movies Leaving Wins Watch"),
    "leaving-shows": ("leaving", "⏳", "Shows Leaving Wins Watch"),
    # theme (Kometa smart collections, "today's shelf")
    "adrenaline-rush": ("theme", "\U0001F4A5", "Adrenaline Rush"),
    "crime-files": ("theme", "\U0001F575️", "Crime Files"),
    "sci-fi-odyssey": ("theme", "\U0001F680", "Sci-Fi Odyssey"),
    "hidden-gems": ("theme", "\U0001F48E", "Hidden Gems"),
    "love-and-laughs": ("theme", "\U0001F498", "Love & Laughs"),
    "mind-benders": ("theme", "\U0001F300", "Mind Benders"),
    "based-on-a-true-story": ("theme", "\U0001F4F0", "Based on a True Story"),
    "directors-spotlight": ("theme", "\U0001F3AC", "Director's Spotlight"),
    "fresh-picks": ("theme", "\U0001F37F", "Fresh Picks"),
    "raunchy-comedy": ("theme", "\U0001F37A", "Raunchy Comedy"),
    "worlds-beyond": ("theme", "\U0001FA90", "Worlds Beyond"),
    "peak-tv": ("theme", "\U0001F3D4️", "Peak TV"),
    "crime-beat": ("theme", "\U0001F694", "Crime Beat"),
    "comfort-binge": ("theme", "\U0001F6CB️", "Comfort Binge"),
    "just-dropped": ("theme", "\U0001F4FA", "Just Dropped"),
    "edge-of-your-seat": ("theme", "\U0001F3A2", "Edge of Your Seat"),
    "date-night": ("theme", "\U0001F377", "Date Night"),
    "sunday-slow-burn": ("theme", "☕", "Sunday Slow Burn"),
    # seasonal
    "halloween": ("seasonal", "\U0001F383", "Halloween"),
    "christmas": ("seasonal", "\U0001F384", "Christmas Movies"),
    "valentines": ("seasonal", "\U0001F498", "Valentine's Picks"),
    "awards-season": ("seasonal", "\U0001F3C6", "Awards Season"),
}

EYEBROW = {
    "personal": "JUST FOR YOU",
    "trending": "RIGHT NOW",
    "new": "NEW ON WINS WATCH",
    "popular": "EVERYONE'S WATCHING",
    "leaving": "LAST CALL",
    "theme": "TODAY'S SHELF",
    "seasonal": "THIS SEASON",
}

# TINT[kind] = (top_hex, bottom_hex, ink_hex, ring: bool). TINT["seasonal"] is further keyed by slug
# since each season gets its own colours.
RING_COLOR = "#5ac8fa"
TINT = {
    "personal": ("#0e3b57", "#1b5e8a", "#ffffff", True),
    "trending": ("#3b1f5e", "#6d3fb8", "#ffffff", False),
    "new": ("#0e3b57", "#5ac8fa", "#06131c", False),
    "popular": ("#4a2e00", "#e8b84a", "#1a1200", False),
    "leaving": ("#5a1010", "#e52d27", "#ffffff", False),
    "theme": ("#1a1d26", "#3a4052", "#ffffff", False),
    "seasonal": {
        "halloween": ("#1a0a2e", "#ff7a1a", "#ffffff", False),
        "christmas": ("#0b2e1a", "#c62828", "#ffffff", False),
        "valentines": ("#3a0a1e", "#ff4f8b", "#ffffff", False),
        # awards-season's gold bottom is as bright as popular's; dark ink for the same contrast reason.
        "awards-season": ("#2a2000", "#f5c518", "#1a1200", False),
    },
}

# Only these kinds are ours to upload (Step 5): Shortlist's personal/popular rows, Maintainerr's
# leaving row, and our own new-arrivals row. Trending/theme/seasonal collections are Kometa-owned and
# get their art through Kometa's own asset pipeline, not this function.
UPLOAD_KINDS = {"personal", "popular", "leaving", "new"}
ZW_CHARS = "​‌‍﻿"


def _tint(slug: str, kind: str):
    t = TINT[kind]
    return t[slug] if isinstance(t, dict) else t


def _hex(h: str, a: int = 255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _gradient_plate(top_hex: str, bottom_hex: str) -> Image.Image:
    top, bottom = _hex(top_hex), _hex(bottom_hex)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(top[c] + (bottom[c] - top[c]) * t) for c in range(3)) + (255,)
        d.line([(0, y), (W - 1, y)], fill=row)
    return im


_EMOJI_FONT = None
_EMOJI_CHECKED = False


def _emoji_font_path():
    """Path to a colour emoji font (Noto Color Emoji), or None if fontconfig doesn't have one."""
    global _EMOJI_FONT, _EMOJI_CHECKED
    if not _EMOJI_CHECKED:
        _EMOJI_CHECKED = True
        try:
            out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=5).stdout
        except Exception:
            out = ""
        for line in out.splitlines():
            if "noto color emoji" in line.lower():
                _EMOJI_FONT = line.split(":")[0].strip()
                break
    return _EMOJI_FONT


def _emoji_glyph(emoji_ch: str, target_h: int):
    """Render `emoji_ch` with NotoColorEmoji (only works at font size 109) and scale to `target_h` tall.
    Returns None if no colour emoji font is installed."""
    path = _emoji_font_path()
    if not path or not emoji_ch:
        return None
    font = ImageFont.truetype(path, 109)
    tmp = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((20, 20), emoji_ch, font=font, embedded_color=True)
    bbox = tmp.getbbox()
    if not bbox:
        return None
    tmp = tmp.crop(bbox)
    scale = target_h / tmp.height
    w = max(1, round(tmp.width * scale))
    return tmp.resize((w, target_h), Image.LANCZOS)


def _tracked_draw(d, xy, text, font, fill, track):
    x, y = xy
    for i, c in enumerate(text):
        d.text((x, y), c, font=font, fill=fill, anchor="ls")
        x += font.getlength(c) + (track if i < len(text) - 1 else 0)


EYEBROW_BASELINE = 1130   # default; floats higher when a long title needs 3 lines (see render())


def _draw_eyebrow(d, word: str, ink: str, baseline: int = EYEBROW_BASELINE):
    font = ImageFont.truetype(str(EYEBROW_FONT), 34)
    font.set_variation_by_name("ExtraBold")
    track = 34 * 0.14
    _tracked_draw(d, (80, baseline), word, font, _hex(ink), track)


def _merge_orphan_dot(words: list) -> list:
    """Keep a standalone '·' glued to the word after it, so wrapping never starts a line with it."""
    out, i = [], 0
    while i < len(words):
        if words[i] == "·" and i + 1 < len(words):
            out.append(words[i] + " " + words[i + 1])
            i += 2
        else:
            out.append(words[i])
            i += 1
    return out


def _title_lines(name: str, emoji_img, font, max_width: float):
    """Greedy word-wrap; the emoji (if any) is just the first token on the first line."""
    space_w = font.getlength(" ")
    tokens = []
    if emoji_img is not None:
        tokens.append(("img", emoji_img, emoji_img.width))
    for w in _merge_orphan_dot(name.split(" ")):
        tokens.append(("text", w, font.getlength(w)))
    lines, cur, cur_w = [], [], 0.0
    for tok in tokens:
        w = tok[2]
        add = w if not cur else space_w + w
        if cur and cur_w + add > max_width:
            lines.append(cur)
            cur, cur_w = [], 0.0
            add = w
        cur.append(tok)
        cur_w += add
    if cur:
        lines.append(cur)
    return lines, space_w


def _title_layout(name, emoji_ch, font_size=120, max_width=840, baseline_bottom=1400, pitch=1.05):
    """Wrap the title and work out where its top edge lands, so a 3-line title can push the eyebrow up
    out of its way (see render())."""
    font = ImageFont.truetype(str(TITLE_FONT), font_size)
    font.set_variation_by_name("ExtraBold")
    cap = -font.getbbox("H", anchor="ls")[1]
    emoji_img = _emoji_glyph(emoji_ch, cap)
    lines, space_w = _title_lines(name, emoji_img, font, max_width)
    line_h = round(font_size * pitch)
    n = len(lines)
    top = baseline_bottom - (n - 1) * line_h - cap
    return {"font": font, "cap": cap, "lines": lines, "space_w": space_w, "line_h": line_h,
            "n": n, "top": top, "baseline_bottom": baseline_bottom}


def _draw_title(im, d, layout, ink, x0=80):
    font, cap, space_w, line_h, n, baseline_bottom = (
        layout["font"], layout["cap"], layout["space_w"], layout["line_h"], layout["n"], layout["baseline_bottom"])
    for i, line in enumerate(layout["lines"]):
        baseline = baseline_bottom - (n - 1 - i) * line_h
        x = float(x0)
        for kind, val, w in line:
            if kind == "img":
                im.alpha_composite(val, (round(x), round(baseline - cap)))
            else:
                d.text((x, baseline), val, font=font, fill=_hex(ink), anchor="ls")
            x += w + space_w


def render(slug: str) -> Image.Image:
    kind, emoji, title = CARDS[slug]
    top, bottom, ink, ring = _tint(slug, kind)
    im = _gradient_plate(top, bottom)
    d = ImageDraw.Draw(im)
    layout = _title_layout(title, emoji)
    # Eyebrow defaults to a fixed baseline, but floats higher when a long title wraps to 3 lines so the
    # two never overlap (a 1- or 2-line title always leaves the default position clear).
    eyebrow_baseline = min(EYEBROW_BASELINE, layout["top"] - 30)
    _draw_eyebrow(d, EYEBROW[kind], ink, eyebrow_baseline)
    _draw_title(im, d, layout, ink)
    paw = Image.open(PAW).convert("RGBA").resize((110, 110), Image.LANCZOS)
    tinted = Image.new("RGBA", paw.size, _hex(ink))
    tinted.putalpha(paw.getchannel("A").point(lambda v: round(v * 0.9)))
    im.alpha_composite(tinted, (810, 80))
    if ring:
        d.rectangle([14, 14, W - 15, H - 15], outline=_hex(RING_COLOR), width=6)
    return im.convert("RGB")


def generate(out_dir) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for slug in CARDS:
        p = out_dir / f"{slug}.png"
        render(slug).save(p)
        paths.append(p)
    return sorted(paths)


# --- Step 5: upload cards we own to the matching Plex collections ------------------------------


def _clean_title(title: str) -> str:
    return title.rstrip(ZW_CHARS) if title else title


def _upload_prefixes() -> dict:
    """slug -> 'emoji title' prefix, for the rows we own (see UPLOAD_KINDS)."""
    return {slug: f"{emoji} {title}" for slug, (kind, emoji, title) in CARDS.items() if kind in UPLOAD_KINDS}


def upload_cards(plex, sections, cards_dir, cache_path, dry_run: bool = False) -> list[str]:
    """Upload generated cards to the Plex collections Kometa doesn't own (Shortlist's personal/popular
    rows, Maintainerr's leaving row, our new-arrivals row), matched by title prefix in each section.
    Idempotent via `cache_path` ({ratingKey: slug}): a collection is skipped once its current slug is
    cached and the card file hasn't changed since the cache was last written. `--dry-run` returns what
    it would upload without calling uploadPoster or touching the cache."""
    cards_dir = Path(cards_dir)
    cache_path = Path(cache_path)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    cache_mtime = cache_path.stat().st_mtime if cache_path.exists() else 0.0
    prefixes = _upload_prefixes()
    new_cache = dict(cache)
    actions = []
    for section in sections:
        for collection in section.collections():
            title = _clean_title(collection.title)
            slug = next((s for s, pre in prefixes.items() if title.startswith(pre)), None)
            if slug is None:
                continue
            card_file = cards_dir / f"{slug}.png"
            if not card_file.exists():
                continue
            key = str(collection.ratingKey)
            needs_upload = cache.get(key) != slug or card_file.stat().st_mtime > cache_mtime
            if not needs_upload:
                continue
            actions.append(f"{title} -> {slug}")
            if not dry_run:
                collection.uploadPoster(filepath=str(card_file))
                new_cache[key] = slug
    if not dry_run and new_cache != cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(new_cache, indent=2, sort_keys=True))
    return actions


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "cards"
    print(f"wrote {len(generate(dest))} files to {dest}")
