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
        if missing: item.addLabel(list(missing))
        return bool(stale or missing)

    def set_user_rating(self, item, value: float) -> bool:
        if item.userRating is not None and abs(item.userRating - value) < 0.05:
            return False
        item.rate(value)
        return True
