import lab_media

def test_symlink_script():
    s = lab_media.symlink_script({"Dune: Part Two": "/data/media/movies/Dune Part Two (2024)", "Reacher": "/data/media/tv/Reacher (2022)"})
    assert "mkdir -p '/mnt/user/data/media/_winswatch-lab/movies' '/mnt/user/data/media/_winswatch-lab/tv'" in s
    assert "ln -sfn '/data/media/movies/Dune Part Two (2024)' '/mnt/user/data/media/_winswatch-lab/movies/Dune Part Two (2024)'" in s
    assert "ln -sfn '/data/media/tv/Reacher (2022)' '/mnt/user/data/media/_winswatch-lab/tv/Reacher (2022)'" in s
    assert "rm -rf" not in s
