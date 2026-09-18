import yaml, textwrap
from pathlib import Path
import build_lab_config

def test_build_fills_blocks_and_libraries(tmp_path: Path):
    prod = tmp_path / "config.yml"
    prod.write_text(textwrap.dedent("""
      plex: {url: http://192.168.0.20:32400, token: abc, timeout: 60}
      tmdb: {apikey: tkey, language: en}
      mdblist: {apikey: mkey}
      libraries:
        Movies: {collection_files: []}
    """))
    tpl = Path(__file__).resolve().parents[3] / "kometa/lab.yml.template"
    out = yaml.safe_load(build_lab_config.build(prod, tpl, "Wins Watch Lab", "Wins Watch Lab TV"))
    assert out["plex"]["token"] == "abc" and out["tmdb"]["apikey"] == "tkey" and out["mdblist"]["apikey"] == "mkey"
    assert set(out["libraries"]) == {"Wins Watch Lab", "Wins Watch Lab TV"}
    assert "Movies" not in out["libraries"] and "TV Shows" not in out["libraries"]
    files = [f["file"] for f in out["libraries"]["Wins Watch Lab"]["overlay_files"]]
    assert files == ["config/winswatch/movies.yml", "config/winswatch/generated/gauge.yml", "config/winswatch/generated/topedge.yml"]
