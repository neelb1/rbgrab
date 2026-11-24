"""Print where rbgrab finds its tools and settings (for bug reports): python scripts/diagnose.py"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rbgrab import config, download  # noqa: E402

print("python      ", sys.executable)
print("config      ", config.config_path(), "exists" if config.config_path().exists() else "MISSING")
print("bin dir     ", config.bin_dir(), os.listdir(config.bin_dir()) if config.bin_dir().exists() else "MISSING")
print("which yt-dlp", shutil.which("yt-dlp"))
print("which ffmpeg", shutil.which("ffmpeg"))
print("yt-dlp cmd  ", download.ytdlp_command())
print("ffmpeg dir  ", download.ffmpeg_dir())
print("PATHEXT     ", os.environ.get("PATHEXT"))
