"""promote_config.py --phase home: collection_files rewrite (textual, idempotent, everything else untouched)."""
import textwrap
import promote_config as pc

PROD = textwrap.dedent("""\
    plex:
      url: http://192.168.0.20:32400/
    libraries:                         # This is called out once within the config.yml file
      Movies:                                           # Must match a library name in your Plex
        report_path: config/missing/Movies_report.yml
        remove_overlays: false
        template_variables:
          sep_style: gray                               # use the gray separators globally for this library
        collection_files:                               # These files contain collections: and/or dynamic_collections attributes
        - url: https://raw.githubusercontent.com/chaseuebelhart/unraid/refs/heads/main/kometa/collections/seasonal_christmas.yml
        - url: https://raw.githubusercontent.com/chaseuebelhart/unraid/refs/heads/main/kometa/collections/trending_movies.yml
        - url: https://raw.githubusercontent.com/chaseuebelhart/unraid/refs/heads/main/kometa/collections/movies_leaving_soon.yml
        # - default: oscars                               # The Oscars
        #   template_variables:                           # based on when the award show started
        #     use_year_collections: false
        - default: separator_chart                      # An "index card"
        - default: imdb                                 # IMDb Charts (Popular, Trending, etc.)
        - default: tmdb                                 # TMDb Charts (Popular, Trending, etc.)
        - default: basic                                # Some basic chart collections based on recently released media in your library
        - default: collectionless                       # Collectionless collection to help Show/Hide Movies/Shows properly in your library
        - default: genre                                # Action, Comedy, Drama, etc.
        # - default: studio                               # DreamWorks Studios, Lucasfilm Ltd, etc.
        - default: franchise                            # https://kometa.wiki/en/latest/defaults/movie/franchise
          template_variables:
            collection_section: '035'                   # Set to "035" to be right before universe. Should be the same here and above
        - default: streaming                            # Streaming on Disney+, Netflix, etc.
          template_variables:
            originals_only: true
        - default: universe                             # Marvel Cinematic Universe, Wizarding World, etc.
    # .--------------------------------------------------------.
    # | overlays banner                                          |
    # '--------------------------------------------------------'
        overlay_files:                                  # Wins Watch (scripts/winswatch, kometa/overlays/winswatch)
        - file: config/winswatch/movies.yml
        operations:
          delete_collections:
            managed: true
          # mass_user_rating_update: (winswatch scores.py owns this slot)
          mass_critic_rating_update: mdb_metacritic
          mass_audience_rating_update: mdb_letterboxd
      TV Shows:                                         # Must match a library name in your Plex
        report_path: config/missing/TV_report.yml
        remove_overlays: false
        collection_files:                               # These files contain collections: and/or dynamic_collections attributes
        - url: https://raw.githubusercontent.com/chaseuebelhart/unraid/refs/heads/main/kometa/collections/shows_trending.yml
        - url: https://raw.githubusercontent.com/chaseuebelhart/unraid/refs/heads/main/kometa/collections/shows_leaving_soon.yml
        - default: imdb                                 # IMDb Charts (Popular, Trending, etc.)
        - default: tmdb                                 # TMDb Charts (Popular, Trending, etc.)
        - default: collectionless                       # Collectionless collection to help Show/Hide Movies/Shows properly in your library
        # - file: /config/metadata/both/birthday          # Actor birthdays
        - default: genre                                # Action, Comedy, Drama, etc.
        - default: network                              # ABC, CBC, NBC, FOX, etc.
        - default: streaming                            # Streaming on Disney+, Netflix, etc.
          template_variables:
            originals_only: true
        - default: universe                             # Marvel Cinematic Universe, Wizarding World, etc.
    # .--------------------------------------------------------.
        overlay_files:                                  # Wins Watch (scripts/winswatch, kometa/overlays/winswatch)
        - file: config/winswatch/shows.yml
        operations:
          # mass_user_rating_update: (winswatch scores.py owns this slot)
          mass_critic_rating_update: mdb_metacritic
          mass_audience_rating_update: mdb_trakt
    settings:
      run_order:
      - collections
""")


def _block(text, lib):
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith(f"  {lib}:"))
    k = next(i for i in range(start, len(lines)) if lines[i].startswith("    collection_files:"))
    e = next(i for i in range(k + 1, len(lines)) if lines[i].startswith("    overlay_files:"))
    return lines[k:e]


def test_home_movies_block():
    out = pc.rewrite(PROD, "home")
    block = _block(out, "Movies")
    files = [l.strip() for l in block if l.strip().startswith("- file:")]
    assert files == ["- file: config/winswatch/collections/home_movies.yml",
                     "- file: config/winswatch/collections/trending_movies.yml",
                     "- file: config/winswatch/collections/movies_leaving_soon.yml"]
    assert not any("- url:" in l for l in block)
    defaults = [l.split("default:")[1].split("#")[0].strip() for l in block if l.lstrip().startswith("- default:")]
    assert defaults == ["separator_chart", "collectionless", "genre", "franchise", "streaming", "universe"]
    # every kept default is off Home
    text = "\n".join(block)
    assert text.count("visible_home: false") == 6 and text.count("visible_shared: false") == 6
    # existing template variables survive, and the commented-out entries stay
    assert any(l.startswith("        collection_section: '035'") for l in block) and "        originals_only: true" in block
    assert any(l.startswith("    # - default: oscars") for l in block) and any(l.startswith("    # - default: studio") for l in block)
    # structure: the visibility lines sit under a template_variables map of the same entry
    i = block.index(next(l for l in block if l.startswith("    - default: genre")))
    assert block[i + 1] == "      template_variables:" and block[i + 2] == "        visible_home: false" and block[i + 3] == "        visible_shared: false"
    j = block.index(next(l for l in block if l.startswith("    - default: franchise")))
    assert block[j + 1] == "      template_variables:" and "collection_section" in block[j + 2] and block[j + 3:j + 5] == ["        visible_home: false", "        visible_shared: false"]


def test_home_tv_block_and_rest_untouched():
    out = pc.rewrite(PROD, "home")
    block = _block(out, "TV Shows")
    files = [l.strip() for l in block if l.strip().startswith("- file:")]
    assert files == ["- file: config/winswatch/collections/home_shows.yml",
                     "- file: config/winswatch/collections/shows_trending.yml",
                     "- file: config/winswatch/collections/shows_leaving_soon.yml"]
    defaults = [l.split("default:")[1].split("#")[0].strip() for l in block if l.lstrip().startswith("- default:")]
    assert defaults == ["collectionless", "genre", "network", "streaming", "universe"]
    assert any(l.startswith("    # - file: /config/metadata/both/birthday") for l in block)
    # everything outside the two collection_files blocks is byte-identical
    strip = lambda t: [l for l in t.split("\n") if not l.startswith(("    - ", "      ", "        ")) and not l.startswith("    collection_files:")]
    assert strip(out) == strip(PROD)
    assert "overlay_files:                                  # Wins Watch" in out and "mass_audience_rating_update: mdb_trakt" in out


def test_home_is_idempotent_and_parses():
    import yaml
    once = pc.rewrite(PROD, "home")
    assert pc.rewrite(once, "home") == once
    doc = yaml.safe_load(once)
    movies = doc["libraries"]["Movies"]["collection_files"]
    assert movies[0] == {"file": "config/winswatch/collections/home_movies.yml"}
    assert {"default": "genre", "template_variables": {"visible_home": False, "visible_shared": False}} in movies
    assert {"default": "franchise", "template_variables": {"collection_section": "035", "visible_home": False, "visible_shared": False}} in movies
    assert not any(e.get("default") in {"imdb", "tmdb", "basic"} for e in movies)
    tv = doc["libraries"]["TV Shows"]["collection_files"]
    assert {"default": "network", "template_variables": {"visible_home": False, "visible_shared": False}} in tv


def test_steady_still_works_and_leaves_collections_alone():
    out = pc.rewrite(PROD, "steady")
    assert _block(out, "Movies") == _block(PROD, "Movies")
    assert "    overlay_files:                                  # Wins Watch" in out
