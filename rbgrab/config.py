"""Settings stored as JSON in the user's app-data folder."""
import json
import os
import sys
from pathlib import Path

APP = "rbgrab"
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
FROZEN = getattr(sys, "frozen", False)

DEFAULTS = {
    "hotkey": "ctrl+alt+s",
    "download_dir": str(Path.home() / "Music" / APP),
    "format": "m4a",  # "m4a" keeps the original audio; "mp3" re-encodes
    "playlist": APP,
    "start_at_login": True,
    "hide_after_grab": True,
    "first_run_done": False,
    "ytdlp_checked": 0,
    "library_dirs": [],  # extra folders checked for songs you already have
}


def config_dir() -> Path:
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / APP
    return Path(os.environ.get("APPDATA", Path.home())) / APP


def bin_dir() -> Path:
    """Where the installers put yt-dlp and ffmpeg."""
    if IS_MAC:
        return config_dir() / "bin"
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP / "bin"


def config_path() -> Path:
    return config_dir() / "config.json"


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        cfg.update(json.loads(config_path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def library_folders(cfg: dict) -> list:
    """The download folder plus any extra library folders, existing ones only."""
    folders = []
    for f in [cfg["download_dir"]] + list(cfg.get("library_dirs") or []):
        if os.path.isdir(f) and f not in folders:
            folders.append(f)
    return folders


def xml_path(cfg: dict) -> Path:
    return Path(cfg["download_dir"]) / "rekordbox.xml"


def launch_command() -> list:
    """Command that starts the app, used for start-at-login."""
    if FROZEN:
        return [sys.executable]
    python = sys.executable
    if IS_WIN and python.lower().endswith("python.exe"):
        python = python[:-10] + "pythonw.exe"
    return [python, "-m", APP]
