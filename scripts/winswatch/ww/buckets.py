from datetime import date

VOTE_BUCKETS = ["10K", "20K", "50K"] + [f"{n}00K" for n in range(1, 10)] + [f"{x/2:.1f}M" for x in range(2, 15)]
# -> 10K 20K 50K 100K..900K 1.0M 1.5M ... 7.0M   (25 buckets)

def _value(b: str) -> int:
    return int(float(b[:-1]) * (1_000_000 if b.endswith("M") else 1_000))

def votes_bucket(n: int) -> str | None:
    """Nearest bucket; None under 10K; capped at 7.0M."""
    if n < 10_000:
        return None
    best = VOTE_BUCKETS[0]
    min_distance = abs(_value(best) - n)
    for b in VOTE_BUCKETS:
        distance = abs(_value(b) - n)
        if distance < min_distance:
            min_distance = distance
            best = b
    return best

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def tab_years(today: date | None = None) -> list[int]:
    """Years a Returns_<YYYY> tab/overlay is generated for: this year through +6 (airdate_label emits the air year)."""
    y = (today or date.today()).year
    return list(range(y, y + 7))
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def airdate_label(next_air: date | None, status: str, today: date) -> str | None:
    """Sonarr status: continuing|ended|upcoming|deleted. Ended/canceled shows get no label (Kometa uses tmdb_status)."""
    if status not in ("continuing", "upcoming"):
        return None
    if next_air is None:
        return "Returns_TBA"
    days = (next_air - today).days
    if days < 0:
        return "Returns_TBA"
    if days <= 7:
        return f"NewEp_{DOW[next_air.weekday()]}"
    if days <= 30:
        return f"ReturnsIn_{days}"
    if days <= 120:
        return f"Returns_{MON[next_air.month - 1]}"
    return f"Returns_{next_air.year}"
