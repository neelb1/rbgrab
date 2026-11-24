from rbgrab import core, libindex


def test_reads_video_id_from_file_tags(tmp_path):
    song = tmp_path / "a.mp3"
    for link in ("https://www.youtube.com/watch?v=lXc8EHmFXOM", "https://youtu.be/lXc8EHmFXOM",
                 "https://music.youtube.com/watch?si=x&v=lXc8EHmFXOM"):
        for encoding in ("utf-8", "utf-16"):
            tag = b"ID3" + link.encode(encoding)
            for data in (tag + b"\xff" * 100, b"\xff" * 9_000_000 + tag):  # tags first or last
                song.write_bytes(data)
                assert libindex.video_id_in(str(song)) == "lXc8EHmFXOM"
    song.write_bytes(b"no link here")
    assert libindex.video_id_in(str(song)) is None


def test_scan_finds_tagged_files_and_skips_others(tmp_path, monkeypatch):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.m4a").write_bytes(b"x")
    (tmp_path / "b.mp3").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    monkeypatch.setattr(libindex, "video_id_in", lambda p: "vidA" if p.endswith("a.m4a") else None)
    index = libindex.LibraryIndex(tmp_path / "cache.json")
    index.scan([str(tmp_path)])
    assert index.find("vidA").endswith("a.m4a")
    assert index.find("other") is None
    assert len(index._files) == 2  # the .txt is ignored


def test_grab_skips_songs_already_in_library(tmp_path):
    song = tmp_path / "Bicep - Glue.m4a"
    song.write_bytes(b"x")

    class Index:
        def find(self, vid):
            return str(song) if vid == "glue" else None

    cfg = {"download_dir": str(tmp_path), "playlist": "rbgrab"}
    state, name = core.grab(cfg, {"id": "glue", "title": "Glue", "artist": "Bicep"}, library_index=Index())
    assert (state, name) == ("dupe", "Bicep - Glue")


def test_tools_ignore_current_folder_and_empty_files(tmp_path, monkeypatch):
    from rbgrab import config, download
    ext = ".exe" if config.IS_WIN else ""
    (tmp_path / ("yt-dlp" + ext)).write_bytes(b"")  # the empty stray file that broke grabs
    good = tmp_path / "bin"
    good.mkdir()
    (good / ("yt-dlp" + ext)).write_bytes(b"MZ")
    (good / ("yt-dlp" + ext)).chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(good))
    monkeypatch.setattr(config, "bin_dir", lambda: tmp_path / "nope")
    assert download.ytdlp_command() == [str(good / ("yt-dlp" + ext))]
