"""Downloads through the yt-dlp program, so it can update itself when YouTube changes."""
import importlib.util
import os
import subprocess
import sys

from . import config

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_EXE = ".exe" if config.IS_WIN else ""


def env() -> dict:
    e = dict(os.environ)
    e.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return e


def _usable(path) -> bool:
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def _bundled(name: str):
    path = config.bin_dir() / (name + _EXE)
    return str(path) if _usable(path) else None


def _on_path(name: str):
    """Like shutil.which, but only searches PATH. On Windows, Python's which() also
    looks in the current folder first, so a stray or empty yt-dlp.exe there would win."""
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not folder or not os.path.isabs(folder):
            continue
        candidate = os.path.join(folder, name + _EXE)
        if _usable(candidate) and (config.IS_WIN or os.access(candidate, os.X_OK)):
            return candidate
    return None


def ytdlp_command():
    """The installer's copy first, then PATH, then the Python module (when running from source)."""
    for exe in (_bundled("yt-dlp"), _on_path("yt-dlp")):
        if exe:
            return [exe]
    if not config.FROZEN and importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    return None


def ffmpeg_dir():
    exe = _bundled("ffmpeg") or _on_path("ffmpeg")
    return os.path.dirname(exe) if exe else None


def video_url(video_id: str) -> str:
    return f"https://music.youtube.com/watch?v={video_id}"


_FORMATS = {
    "m4a": ["-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "m4a"],
    "mp3": ["-f", "bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "0"],
}


def download(url: str, cfg: dict, on_progress=lambda pct: None) -> dict:
    """Download one song. Returns {path, artist, title, duration, id}."""
    try:
        return _download(url, cfg, on_progress)
    except RuntimeError as e:
        if "403" not in str(e):
            raise
        return _download(url, cfg, on_progress)  # YouTube sometimes 403s a first request


def _download(url: str, cfg: dict, on_progress) -> dict:
    cmd = ytdlp_command()
    if not cmd:
        raise RuntimeError("yt-dlp isn't installed - run the rbgrab installer again")
    ffmpeg = ffmpeg_dir()
    if not ffmpeg:
        raise RuntimeError("ffmpeg isn't installed - run the rbgrab installer again")
    os.makedirs(cfg["download_dir"], exist_ok=True)
    cmd = cmd + [
        url, "--no-playlist", "--newline", "--color", "never", "--quiet", "--progress",
        "--no-warnings", "--no-overwrites", "--embed-metadata", "--embed-thumbnail",
        "--ffmpeg-location", ffmpeg,
        "-P", cfg["download_dir"], "-o", "%(artist,uploader)s - %(track,title)s.%(ext)s",
        "--progress-template",
        "download:RBGP %(progress.downloaded_bytes)s %(progress.total_bytes,progress.total_bytes_estimate)s",
        "--print", "after_move:RBGF\t%(filepath)s\t%(artist,uploader)s\t%(track,title)s\t%(duration)s\t%(id)s",
    ] + _FORMATS.get(cfg.get("format"), _FORMATS["m4a"])

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", creationflags=NO_WINDOW, env=env())
    result, errors = None, []
    for line in proc.stdout:
        line = line.rstrip("\r\n")
        if line.startswith("RBGP "):
            done, _, total = line[5:].partition(" ")
            try:
                on_progress(min(int(done) / float(total), 1.0))
            except (ValueError, ZeroDivisionError):
                pass
        elif line.startswith("RBGF\t"):
            path, artist, title, duration, vid = (line.split("\t") + [""] * 6)[1:6]
            result = {"path": path, "artist": artist if artist != "NA" else "",
                      "title": title, "id": vid,
                      "duration": int(float(duration)) if duration.replace(".", "").isdigit() else 0}
        elif line.startswith("ERROR"):
            errors.append(line)
    proc.wait()
    if proc.returncode or not result:
        raise RuntimeError(_short(errors[-1]) if errors else "yt-dlp failed")
    return result


def _short(error: str) -> str:
    error = error.removeprefix("ERROR:").strip()
    if "] " in error[:40]:
        error = error.split("] ", 1)[1]
    return error[:140]


def updatable() -> bool:
    return _bundled("yt-dlp") is not None


def update_ytdlp() -> str:
    exe = _bundled("yt-dlp")
    if not exe:
        return "yt-dlp wasn't installed by rbgrab; update it the way you installed it"
    out = subprocess.run([exe, "-U"], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=180, creationflags=NO_WINDOW, env=env())
    lines = [l for l in (out.stdout + out.stderr).splitlines() if l.strip()]
    return lines[-1] if lines else "yt-dlp is up to date"
