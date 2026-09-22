from plexapi.server import PlexServer

class PlexLib:
    def __init__(self, url: str, token: str):
        self.server = PlexServer(url, token)

    def section(self, section_id: int):
        return self.server.library.sectionByID(int(section_id))

    def items(self, section_id: int):
        return self.section(section_id).all()

    @staticmethod
    def _guid(item, prefix):
        for g in getattr(item, "guids", []) or []:
            if g.id.startswith(prefix):
                return g.id[len(prefix):]
        return None

    def tmdb_id(self, item): return self._guid(item, "tmdb://")
    def tvdb_id(self, item): return self._guid(item, "tvdb://")

    def set_labels(self, item, add: set, remove_prefixes: tuple) -> bool:
        current = {l.tag for l in item.labels}
        stale = {l for l in current if l.startswith(remove_prefixes) and l not in add}
        missing = add - current
        if stale: item.removeLabel(list(stale))
        if stale and missing: item.reload()   # plexapi rebuilds the tag list from item.labels; without a reload addLabel re-adds the stale ones
        if missing: item.addLabel(list(missing))
        return bool(stale or missing)

    def set_user_rating(self, item, value: float) -> bool:
        if item.userRating is not None and abs(item.userRating - value) < 0.05:
            return False
        # Metadata edit (what Kometa's mass_user_rating_update does), not /:/rate: rating through /:/rate fires a
        # media.rate webhook and a plex.tv ViewStateSync round-trip that echoes the value back rounded to a whole
        # number (7.3 -> 7.0) a few seconds later. The edit path keeps the decimal.
        item.editField("userRating", value, locked=True)
        return True

    # --- collections (per-user Home rows) ---------------------------------------------------------------------------
    ZW = "​‌"     # zero-width suffix alphabet of per-user titles (home.row_title)

    def _create_collection(self, title, section, items):
        from plexapi.collection import Collection
        return Collection.create(self.server, title, section, items)

    def upsert_collection(self, section, title: str, items: list, label: str, sort: str = "custom"):
        """Create the collection if missing, else make its items exactly `items` in that order (add missing, drop stale,
        move the rest — never recreate, so the poster and hub survive); sort custom; `label` added. Matches an existing
        collection by exact title, else by `label` + same title minus the zero-width suffix (suffix scheme changed).
        Empty `items`: Plex collections cannot be empty, so an existing one is deleted; returns None."""
        base = title.rstrip(self.ZW)
        cols = section.collections()
        existing = [c for c in cols if c.title == title] or \
                   [c for c in cols if c.title.rstrip(self.ZW) == base and label.lower() in {l.tag.lower() for l in c.labels}]
        col = existing[0] if existing else None
        if not items:
            if col: col.delete()
            return None
        if col is None:
            col = self._create_collection(title, section, items).reload()
        want = [i.ratingKey for i in items]
        have = [i.ratingKey for i in col.items()]
        if set(have) != set(want):
            current = {i.ratingKey: i for i in col.items()}
            stale = [current[k] for k in have if k not in want]
            missing = [i for i in items if i.ratingKey not in current]
            if stale: col.removeItems(stale)
            if missing: col.addItems(missing)
            col.reload()                                       # items() is cached until reload
        if col.collectionSort != {"release": 0, "alpha": 1, "custom": 2}[sort]:
            col.sortUpdate(sort)                               # before the moves: a fresh collection lists children by sort title
        if [i.ratingKey for i in col.items()] != want:         # (also right after create: the POST does not keep insertion order)
            prev = None
            for i in items:
                col.moveItem(i, after=prev)
                prev = i
        if label.lower() not in {l.tag.lower() for l in col.labels}:   # Plex title-cases new tags
            col.addLabel(label)
        return col.reload()
