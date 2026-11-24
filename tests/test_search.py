from rbgrab import search


class FakeYT:
    def __init__(self, songs, everything):
        self.songs, self.everything = songs, everything

    def search(self, query, filter=None, limit=5):
        return self.songs if filter == "songs" else self.everything


def _r(vid, title, artist, kind="song"):
    return {"videoId": vid, "title": title, "artists": [{"name": artist}], "resultType": kind}


def test_remix_video_beats_unrelated_songs(monkeypatch):
    yt = FakeYT([_r("a", "open your eyes", "Aaron Hibell")],
                [_r("v", "Travis Scott - MY EYES [Altare Remix]", "Altare", "video"),
                 {"resultType": "artist", "artists": []}])
    monkeypatch.setattr(search, "_yt", lambda: yt)
    results = search.search("my eyes altare")
    assert results[0]["id"] == "v" and results[0]["kind"] == "video"
    assert [r["id"] for r in results] == ["v", "a"]


def test_song_wins_tie_and_duplicates_are_dropped(monkeypatch):
    yt = FakeYT([_r("s", "One More Time", "Daft Punk")],
                [_r("mv", "One More Time", "Daft Punk", "video"), _r("s", "One More Time", "Daft Punk")])
    monkeypatch.setattr(search, "_yt", lambda: yt)
    assert [r["id"] for r in search.search("daft punk one more time")] == ["s", "mv"]


def test_and_ampersand_variants_and_matching():
    assert search._variants("scream & shout gravagerz") == ["scream & shout gravagerz",
                                                           "scream and shout gravagerz"]
    assert search._variants("scream and shout") == ["scream and shout", "scream & shout"]
    assert search._variants("glue bicep") == ["glue bicep"]
    item = {"title": "Scream & Shout (Gravagerz Remix)", "artist": "will.i.am"}
    assert search._match(search._words("scream and shout gravagerz"), item) == 1.0
