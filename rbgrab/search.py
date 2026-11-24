"""YouTube Music search (ytmusicapi, in-process) with a yt-dlp fallback."""
import json
import re
import subprocess
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from . import download

_client = None
_client_lock = threading.Lock()


def _yt():
    global _client
    with _client_lock:
        if _client is None:
            from ytmusicapi import YTMusic
            _client = YTMusic()
        return _client


def warm():
    """Import and create the client in the background so the first search is quick."""
    threading.Thread(target=lambda: _safe(_yt), daemon=True).start()


def _safe(fn):
    try:
        fn()
    except Exception:
        pass


def is_url(text: str) -> bool:
    return bool(re.match(r"https?://", text.strip(), re.I))


def video_id(url: str):
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname and parsed.hostname.endswith("youtu.be"):
        return parsed.path.strip("/") or None
    return urllib.parse.parse_qs(parsed.query).get("v", [None])[0]


def label(item: dict) -> str:
    return f"{item['artist']} - {item['title']}" if item.get("artist") else item["title"]


def _item(r: dict) -> dict:
    return {
        "id": r["videoId"],
        "title": r.get("title") or "",
        "artist": ", ".join(a["name"] for a in r.get("artists") or [] if a.get("name")),
        "duration": r.get("duration") or "",
        "kind": r.get("resultType") or "song",
    }


def _words(text: str) -> set:
    return set(re.findall(r"\w+", text.lower().replace("&", " and ")))


def _variants(query: str) -> list:
    """The query plus its &/and twin: YouTube ranks "scream & shout" and
    "scream and shout" very differently, so search both spellings."""
    out = [query]
    if "&" in query:
        out.append(re.sub(r"\s*&\s*", " and ", query))
    elif re.search(r"\band\b", query, re.I):
        out.append(re.sub(r"\band\b", "&", query, flags=re.I))
    return out


def _match(query_words: set, item: dict) -> float:
    """Share of the typed words found in the title and artist."""
    if not query_words:
        return 0.0
    return len(query_words & _words(item["title"] + " " + item["artist"])) / len(query_words)


def search(query: str, limit: int = 5) -> list:
    """Best playable results: [{id, title, artist, duration, kind}].

    Runs a songs-only search and all-results searches side by side. Official songs
    are preferred, but remixes and edits are often uploaded as videos ("Covers and
    remixes"), which only the all-results search finds. Results are ranked by how many
    of the typed words they match; ties keep songs first.
    """
    try:
        yt = _yt()
        variants = _variants(query)
        with ThreadPoolExecutor(1 + len(variants)) as pool:
            songs = pool.submit(yt.search, query, filter="songs", limit=limit)
            everything = [pool.submit(yt.search, v, limit=limit) for v in variants]
            candidates = [_item(r) for r in songs.result() if r.get("videoId")]
            for future in everything:
                candidates += [_item(r) for r in future.result()
                               if r.get("videoId") and r.get("resultType") in ("song", "video")]
    except Exception:
        return _ytdlp_search(query, limit)
    seen, unique = set(), []
    for c in candidates:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique.append(c)
    words = _words(query)
    unique.sort(key=lambda c: (-_match(words, c), c["kind"] != "song"))  # stable sort
    return unique[:limit]


def _ytdlp_search(query: str, limit: int) -> list:
    cmd = download.ytdlp_command()
    if not cmd:
        raise RuntimeError("yt-dlp not found")
    out = subprocess.run(cmd + ["--flat-playlist", "-J", f"ytsearch{limit}:{query}"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         timeout=30, creationflags=download.NO_WINDOW, env=download.env())
    entries = json.loads(out.stdout or "{}").get("entries") or []
    return [{
        "id": e["id"],
        "title": e.get("title") or "",
        "artist": e.get("channel") or e.get("uploader") or "",
        "duration": _fmt(e.get("duration")),
        "kind": "video",
    } for e in entries if e.get("id")]


def _fmt(seconds) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"
