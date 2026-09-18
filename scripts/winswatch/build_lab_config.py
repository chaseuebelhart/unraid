"""Build lab.yml from the production config.yml: copy plex/tmdb/mdblist, substitute lab library names. Refuses production library names."""
import sys
from pathlib import Path
import yaml

PROD_LIBS = {"Movies", "TV Shows"}

def build(prod_config: Path, template: Path, movie_lib: str, show_lib: str) -> str:
    if movie_lib in PROD_LIBS or show_lib in PROD_LIBS:
        raise SystemExit("refusing to build a lab config for a production library")
    prod = yaml.safe_load(Path(prod_config).read_text())
    text = Path(template).read_text()
    for key in ("plex", "tmdb", "mdblist"):
        text = text.replace(f"__{key.upper()}__", yaml.safe_dump(prod[key], default_flow_style=True).strip())
    return text.replace("__MOVIE_LIB__", movie_lib).replace("__SHOW_LIB__", show_lib)

if __name__ == "__main__":
    prod, out = Path(sys.argv[1]), Path(sys.argv[2])
    tpl = Path(__file__).resolve().parents[2] / "kometa/lab.yml.template"
    out.write_text(build(prod, tpl, "Wins Watch Lab", "Wins Watch Lab TV")); print(f"wrote {out}")
