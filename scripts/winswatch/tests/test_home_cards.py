from types import SimpleNamespace as NS
import home
import gen_cards


def test_cmd_cards_dry_run_wires_upload_cards(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("PLEX_URL=http://example\nPLEX_TOKEN=tok\n")

    fake_plex = NS(section=lambda sid: NS(id=sid))
    monkeypatch.setattr(home, "plex", lambda env: fake_plex)

    calls = {}

    def fake_upload(plex, sections, cards_dir, cache_path, dry_run=False):
        calls["plex"] = plex
        calls["sections"] = sections
        calls["cards_dir"] = cards_dir
        calls["cache_path"] = cache_path
        calls["dry_run"] = dry_run
        return ["would upload X -> some-slug"]

    monkeypatch.setattr(gen_cards, "upload_cards", fake_upload)

    home.main(["cards", "--sections", "4", "--dry-run", "--env", str(env_file)])

    assert calls["dry_run"] is True
    assert calls["plex"] is fake_plex
    assert [s.id for s in calls["sections"]] == [4]
    assert str(calls["cards_dir"]).replace("\\", "/").endswith("winswatch/cards")
    assert capsys.readouterr().out.strip() == "would upload X -> some-slug"
