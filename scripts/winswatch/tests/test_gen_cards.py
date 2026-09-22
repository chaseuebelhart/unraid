import json
from pathlib import Path
import gen_cards
import gen_home


def test_every_slug_renders_correct_size():
    for slug in gen_cards.CARDS:
        im = gen_cards.render(slug)
        assert im.size == (1000, 1500), slug


def test_personal_ring():
    im = gen_cards.render("for-you-movies").convert("RGB")
    assert im.getpixel((14, 750)) == (0x5A, 0xC8, 0xFA)


def test_popular_gradient_bottom():
    im = gen_cards.render("popular-movies").convert("RGB")
    r, g, b = im.getpixel((500, 1499))
    target = (0xE8, 0xB8, 0x4A)
    assert all(abs(r - g2) <= 12 for r, g2 in zip((r, g, b), target))


def test_generate_writes_every_card(tmp_path: Path):
    files = gen_cards.generate(tmp_path)
    assert len(files) == len(gen_cards.CARDS)
    names = {f.name for f in files}
    for slug in gen_cards.CARDS:
        assert f"{slug}.png" in names


def test_non_personal_has_no_ring():
    im = gen_cards.render("popular-movies").convert("RGB")
    assert im.getpixel((14, 750)) != (0x5A, 0xC8, 0xFA)


def test_every_gen_home_card_slug_exists():
    """Parity with Task 1: every theme/extra gen_home.py knows about must have a card."""
    slugs = {t["card"] for t in gen_home.THEMES.values()} | {t["card"] for t in gen_home.EXTRAS.values()}
    missing = slugs - set(gen_cards.CARDS)
    assert not missing, f"gen_cards.CARDS is missing slugs gen_home references: {missing}"


# --- Step 5: upload_cards ---

class FakeCollection:
    def __init__(self, ratingKey, title):
        self.ratingKey = ratingKey
        self.title = title
        self.uploads = []

    def uploadPoster(self, filepath):
        self.uploads.append(filepath)


class FakeSection:
    def __init__(self, collections):
        self._collections = collections

    def collections(self):
        return self._collections


def _make_cards_dir(tmp_path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    for slug in gen_cards.CARDS:
        (cards_dir / f"{slug}.png").write_bytes(b"fake")
    return cards_dir


def test_upload_cards_matches_by_prefix_and_skips_kometa_rows(tmp_path):
    cards_dir = _make_cards_dir(tmp_path)
    cache_path = tmp_path / "cache" / "cards.json"
    for_you = FakeCollection(1, "✨ Movies for you")               # Shortlist, ours to upload
    byw = FakeCollection(2, "\U0001F3AF Because you watched Dune​")  # trailing zero-width char
    trending = FakeCollection(3, "\U0001F525 Trending Movies")           # Kometa-owned: must be skipped
    unrelated = FakeCollection(4, "Some Random Collection")
    section = FakeSection([for_you, byw, trending, unrelated])

    uploaded = gen_cards.upload_cards(None, [section], cards_dir, cache_path, dry_run=False)

    assert any("for-you-movies" in u for u in uploaded)
    assert any("byw" in u for u in uploaded)
    assert for_you.uploads == [str(cards_dir / "for-you-movies.png")]
    assert byw.uploads == [str(cards_dir / "byw.png")]
    assert trending.uploads == []
    assert unrelated.uploads == []
    assert cache_path.exists()
    cache = json.loads(cache_path.read_text())
    assert cache["1"] == "for-you-movies"
    assert cache["2"] == "byw"


def test_upload_cards_is_idempotent(tmp_path):
    cards_dir = _make_cards_dir(tmp_path)
    cache_path = tmp_path / "cache" / "cards.json"
    col = FakeCollection(10, "\U0001F465 Popular Movies on Wins Watch")
    section = FakeSection([col])

    first = gen_cards.upload_cards(None, [section], cards_dir, cache_path, dry_run=False)
    assert len(first) == 1
    assert len(col.uploads) == 1

    second = gen_cards.upload_cards(None, [section], cards_dir, cache_path, dry_run=False)
    assert second == []
    assert len(col.uploads) == 1   # not re-uploaded


def test_upload_cards_reuploads_when_card_file_changes(tmp_path):
    import os, time
    cards_dir = _make_cards_dir(tmp_path)
    cache_path = tmp_path / "cache" / "cards.json"
    col = FakeCollection(11, "⏳ Movies Leaving Wins Watch")
    section = FakeSection([col])

    gen_cards.upload_cards(None, [section], cards_dir, cache_path, dry_run=False)
    assert len(col.uploads) == 1

    # regenerate the card file with a newer mtime than the cache
    time.sleep(0.05)
    card_file = cards_dir / "leaving-movies.png"
    card_file.write_bytes(b"new-fake")
    newer = time.time() + 5
    os.utime(card_file, (newer, newer))

    again = gen_cards.upload_cards(None, [section], cards_dir, cache_path, dry_run=False)
    assert len(again) == 1
    assert len(col.uploads) == 2


def test_upload_cards_dry_run_does_not_upload(tmp_path):
    cards_dir = _make_cards_dir(tmp_path)
    cache_path = tmp_path / "cache" / "cards.json"
    col = FakeCollection(20, "✨ Shows for you")
    section = FakeSection([col])

    would = gen_cards.upload_cards(None, [section], cards_dir, cache_path, dry_run=True)
    assert len(would) == 1
    assert col.uploads == []
    assert not cache_path.exists()
