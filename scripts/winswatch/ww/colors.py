BRAND = "#5ac8fa"; INK = "#06131c"; DEEP = "#1b5e8a"
GOLD = "#f5c518"; LEAVE_GOLD = "#e8b84a"; LEAVE_INK = "#1a1200"
RED = "#c62828"; GRAY = "#5f6b7a"; WHITE = "#ffffff"; LOW = "#8a94a6"

def band(score: int) -> str:
    if score >= 85: return GOLD
    if score >= 73: return BRAND
    if score >= 65: return WHITE
    return LOW

# key -> (label, hex)
CODEC = {
    "k4": ("4K", WHITE), "p1080": ("1080p", WHITE), "p720": ("720p", WHITE), "sd": ("SD", WHITE),
    "dv": ("DV", "#a78bfa"), "dvhdr": ("DV·HDR", "#c084fc"), "hdrp": ("HDR10+", "#fbbf24"), "hdr": ("HDR", "#e8b84a"),
    "truehdatmos": ("ATMOS", "#60a5fa"), "atmos": ("ATMOS", "#60a5fa"), "ddpatmos": ("DD+", "#7dd3fc"), "truehd": ("TRUEHD", "#2dd4bf"),
    "dtsx": ("DTS:X", "#f87171"), "dtshd": ("DTS-HD", "#fb923c"), "dts": ("DTS", "#ef4444"),
    "ddp": ("DD+", "#4ade80"), "dd": ("DD", "#a3a3a3"), "aac": ("AAC", "#9ca3af"),
    "flac": ("FLAC", "#9ca3af"), "pcm": ("PCM", "#9ca3af"), "opus": ("OPUS", "#9ca3af"),
}

# display name -> hex ; Plex `network` values that map to each name are in SERVICE_NETWORKS
SERVICE = {
    "Netflix": "#e50914", "Prime Video": "#00a8e1", "Apple TV+": "#f5f5f7", "HBO": "#ffffff", "Max": "#b535f6",
    "Hulu": "#1ce783", "Disney+": "#5b9bff", "Paramount+": "#0064ff", "Peacock": "#ffcf00", "FX": "#ffffff",
    "Showtime": "#ff2a2a", "AMC": "#ffcc00", "CBS": "#3b82f6", "NBC": "#f37021", "ABC": "#ffffff", "FOX": "#3b82f6",
    "BBC": "#ffffff", "Comedy Central": "#ffc800", "Crunchyroll": "#f47521", "Bravo": "#8b5cf6", "Syfy": "#a855f7",
    "The CW": "#22c55e", "MGM+": "#f5c518", "Lionsgate+": "#ff8a00", "Adult Swim": "#ffffff", "Starz": "#ffffff",
    "USA Network": "#3b82f6",
}
SERVICE_NETWORKS = {
    "Netflix": ["Netflix"], "Prime Video": ["Prime Video", "Amazon", "Amazon Prime Video", "Freevee"],
    "Apple TV+": ["Apple TV+", "Apple TV"], "HBO": ["HBO"], "Max": ["Max", "HBO Max"], "Hulu": ["Hulu"],
    "Disney+": ["Disney+"], "Paramount+": ["Paramount+", "Paramount Network"], "Peacock": ["Peacock"],
    "FX": ["FX", "FXX"], "Showtime": ["Showtime"], "AMC": ["AMC", "AMC+"], "CBS": ["CBS"], "NBC": ["NBC"],
    "ABC": ["ABC"], "FOX": ["FOX"], "BBC": ["BBC One", "BBC Two", "BBC", "BBC Three"], "Comedy Central": ["Comedy Central"],
    "Crunchyroll": ["Crunchyroll"], "Bravo": ["Bravo"], "Syfy": ["Syfy"], "The CW": ["The CW"], "MGM+": ["MGM+"],
    "Lionsgate+": ["Lionsgate+", "Starz"], "Adult Swim": ["Adult Swim"], "Starz": ["Starz"], "USA Network": ["USA Network"],
}
