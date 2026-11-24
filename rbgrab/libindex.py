"""Which YouTube videos you already have, found by scanning your music folders.

yt-dlp's --embed-metadata stores the source link (youtube.com/watch?v=ID) in each
file's comment/purl tag, so any song downloaded with yt-dlp can be recognized,
wherever it lives. Results are cached by file path + modified time, so only new or
changed files are read on later scans.
"""
import json
import logging
import os
import re
import threading

from . import config

log = logging.getLogger("rbgrab")

AUDIO = {".mp3", ".m4a", ".aac", ".mp4", ".flac", ".wav", ".aif", ".aiff", ".ogg", ".opus", ".webm"}
_LINK = re.compile(rb"(?:youtube\.com/watch\?(?:[\w=&%-]*&)?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})")
_CHUNK = 4 * 1024 * 1024  # tags sit at the start or end of a file, around the cover art


def video_id_in(path: str):
    """The YouTube id stored in a file's tags, or None.

    Looks for the link text directly rather than parsing every tag format.
    """
    try:
        with open(path, "rb") as f:
            size = os.fstat(f.fileno()).st_size
            data = f.read(_CHUNK)
            if size > _CHUNK:
                f.seek(max(_CHUNK, size - _CHUNK))
                data += b"\n" + f.read()
    except OSError:
        return None
    # UTF-16 tags have a null after each letter. yt-dlp writes the song's own link more than
    # once (comment and purl), so it outnumbers links in the video's description.
    ids = _LINK.findall(data.replace(b"\0", b" ")) + _LINK.findall(data.replace(b"\0", b""))
    return max(ids, key=ids.count).decode() if ids else None


class LibraryIndex:
    def __init__(self, cache_path=None):
        self.cache_path = cache_path or (config.config_dir() / "library-cache-2.json")
        self._files = {}   # path -> [mtime, video id or None]
        self._ids = {}     # video id -> path
        self._lock = threading.Lock()
        self._scanning = False
        try:
            self._files = json.loads(open(self.cache_path, encoding="utf-8").read())
        except (OSError, ValueError):
            pass
        self._rebuild_ids()

    def _rebuild_ids(self):
        self._ids = {vid: path for path, (_, vid) in self._files.items() if vid}

    def find(self, video_id):
        """Path of the file holding this video, if it still exists."""
        with self._lock:
            path = self._ids.get(video_id)
        return path if path and os.path.exists(path) else None

    def add(self, video_id, path):
        with self._lock:
            self._ids[video_id] = path

    def scan_async(self, folders):
        if self._scanning:
            return
        self._scanning = True
        threading.Thread(target=self._scan, args=(list(folders),), daemon=True).start()

    def scan(self, folders):
        self._scanning = True
        self._scan(list(folders))

    def _scan(self, folders):
        try:
            seen, files = set(), dict(self._files)
            for folder in folders:
                for root, _, names in os.walk(folder):
                    for name in names:
                        if os.path.splitext(name)[1].lower() not in AUDIO:
                            continue
                        path = os.path.join(root, name)
                        seen.add(path)
                        try:
                            mtime = os.path.getmtime(path)
                        except OSError:
                            continue
                        cached = files.get(path)
                        if not cached or cached[0] != mtime:
                            files[path] = [mtime, video_id_in(path)]
            files = {p: v for p, v in files.items() if p in seen}
            with self._lock:
                self._files = files
                self._rebuild_ids()
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(files, f)
        except Exception:
            log.exception("library scan failed")
        finally:
            self._scanning = False
