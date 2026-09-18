"""Codec chip rows: which video/HDR/audio combinations exist, how each is detected, and how they rank.
One pre-rendered PNG + one Kometa overlay per combination, all in one group so the best match wins."""

VIDEO = {  # key -> Plex resolution regex (Kometa's own resolution default uses the same patterns)
    "k4": r"(?i)2160|4k", "p1080": r"(?i)1080|2k", "p720": r"(?i)720|hd", "sd": r"(?i)576|480|sd",
}
HDR_FLAVORS = ["dvhdr", "dv", "hdrp", "hdr"]          # best -> worst; None = SDR
HDR_PATH = {"dvhdr": r"\bdv[ ._-]?hdr(10)?(\+|p(lus)?)?\b", "hdrp": r"\bhdr10(\+|p(lus)?\b)"}   # filename token required for these two
AUDIO = [  # best -> worst: (key, core regex without (?i)/^ — applied to audio track titles OR the file path)
    ("truehdatmos", r"(?=.*\btrue[ ._-]?hd(\b|\d))(?=.*\batmos(\b|\d))"),
    ("dtsx", r"\b(dts[-_. ]?x7?)\b(?![-_. ]?(26[456]))"),
    ("ddpatmos", r"(?=.*\b((dd[p+])|(dolby[ ._-]digital[ ._-]plus)|(e[ ._-]?ac3))\b)(?=.*\batmos(\b|\d))"),
    ("atmos", r"\batmos(\b|\d)"),
    ("truehd", r"\btrue[ ._-]?hd(\b|\d)"),
    ("dtshd", r"\bdts[ ._-]?(hd[ ._-])?(ma|xll|hd)(\b|\d)(?![ ._-]hra)"),
    ("flac", r"\bflac(\b|\d)"),
    ("pcm", r"\bl?pcm(\b|\d)"),
    ("ddp", r"\b(dd[p+])|(dolby[ ._-]digital[ ._-]plus)|(e[ ._-]?ac3)\b"),
    ("dts", r"\bdts(\b|\d)"),
    ("dd", r"\b(dd)|(ac3)|(dolby)(\b|\d)"),
    ("aac", r"\b(aac|stereo|2\.0)\b"),
    ("opus", r"\b(?<!-)OPUS(\b|\d)"),
]
AUDIO_RE = dict(AUDIO)

def chip_combos():
    """(video, hdr|None, audio|None) for every row we render. HDR flavors only on 4K/1080p."""
    for v in VIDEO:
        for h in (HDR_FLAVORS + [None] if v in ("k4", "p1080") else [None]):
            for a in [k for k, _ in AUDIO] + [None]:
                yield (v, h, a)

def weight(v, h, a) -> int:
    vr = 4 - list(VIDEO).index(v)
    hr = 0 if h is None else 4 - HDR_FLAVORS.index(h)
    ar = 0 if a is None else len(AUDIO) - [k for k, _ in AUDIO].index(a)
    return vr * 1000 + hr * 100 + ar

def _look(core: str) -> str:
    return f"(?=.*(?:{core}))"

def conditions(v, h, a) -> dict:
    """Kometa builder attrs that detect this combination. Everything is a post-filter (no library-level validation
    of tag values); only the boolean `hdr` flag needs plex_search."""
    common = {"resolution.regex": VIDEO[v]}
    out = {}
    if h in ("hdrp", "hdr"):
        out["plex_search"] = {"all": {"hdr": True}}
    elif h is None:
        out["plex_search"] = {"all": {"hdr": False}}; common["has_dolby_vision"] = False
    else:
        out["plex_all"] = True; common["has_dolby_vision"] = True
    path_req = HDR_PATH.get(h)
    if a is None:
        f = dict(common)
        if path_req: f["filepath.regex"] = f"(?i){path_req}"
        out["filters"] = f
        return out
    core = AUDIO_RE[a]
    by_title = dict(common, **{"audio_track_title.regex": f"(?i)^{_look(core)}"})
    if path_req: by_title["filepath.regex"] = f"(?i){path_req}"
    by_path = dict(common, **{"filepath.regex": f"(?i)^{_look(path_req) if path_req else ''}{_look(core)}"})
    out["filters"] = [by_title, by_path]
    return out
