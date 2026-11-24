"""The resident app: hidden search bar, global hotkey, tray icon, download jobs."""
import logging
import queue
import threading
import time
import tkinter as tk
from pathlib import Path

from . import config, core, download, hotkey, instance, library, platform, search
from .libindex import LibraryIndex

log = logging.getLogger("rbgrab")


class Job:
    def __init__(self, text):
        self.text, self.state, self.pct, self.updated = text, "search", 0.0, time.time()


class App:
    def __init__(self):
        platform.prepare_process()
        self.cfg = config.load()
        self.jobs, self.settings, self.tray = [], None, None
        self._queue = queue.Queue()
        self.library = LibraryIndex()
        self.scan_library()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("rbgrab")
        from PIL import ImageTk

        from .icon import draw
        # Several sizes so the taskbar and title bar each get a crisp one.
        self.icon_photos = [ImageTk.PhotoImage(draw(s)) for s in (256, 64, 32, 16)]
        self.icon_photo = self.icon_photos[1]
        self.root.iconphoto(True, *self.icon_photos)

        from .theme import Theme
        from .toast import Toasts
        from .ui import SearchBar
        self.toasts = Toasts(self.root, Theme(self.root))
        self.bar = SearchBar(self)
        self.hotkey = platform.HotkeyListener(lambda: self.post(self.show))
        hotkey_ok = self.hotkey.set(self.cfg["hotkey"])
        try:
            from . import tray
            self.tray = tray.start(self)
        except Exception:
            log.exception("tray icon unavailable")
        instance.serve(lambda: self.post(self.show))
        search.warm()
        if config.FROZEN:
            self._apply_login()
        threading.Thread(target=self._auto_update_ytdlp, daemon=True).start()

        if not self.cfg["first_run_done"]:
            self.post(self.open_settings, True)
        elif not hotkey_ok:
            self.notify("Shortcut unavailable",
                        f"{hotkey.display(self.cfg['hotkey'])} is used by another app. Pick another in Settings.")
            self.post(self.open_settings)
        self.root.after(30, self._pump)

    # Background threads hand work to the Tk thread through this queue.
    def post(self, fn, *args):
        self._queue.put((fn, args))

    def _pump(self):
        while True:
            try:
                fn, args = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception:
                log.exception("UI task failed")
        self.root.after(30, self._pump)

    def run(self):
        self.root.mainloop()

    def show(self):
        if self.settings is None:
            if not self.bar.visible():
                self.scan_library()  # cheap: only new or changed files are read
            self.bar.toggle()
        else:
            self.settings.win.lift()

    # ---------- grabbing ----------
    def grab(self, target):
        job = Job(target if isinstance(target, str) else search.label(target))
        self.jobs.insert(0, job)
        del self.jobs[20:]
        self.bar.refresh_jobs()
        cfg = dict(self.cfg)

        def update(state, pct, text):
            self.post(self._job_update, job, state, pct, text)

        def work():
            try:
                state, name = core.grab(cfg, target, update, self.library)
                if state == "done":
                    self.post(self.notify, "Ready in rekordbox", f"{name}\nRefresh “rekordbox xml” to load it.", "done")
                elif state == "dupe":
                    self.post(self.notify, "Already in your library", name, "dupe")
            except Exception as e:
                log.exception("grab failed")
                update("error", 0, f"{job.text}  -  {e}")
                self.post(self.notify, "Couldn't grab song", str(e)[:200], "error")

        threading.Thread(target=work, daemon=True).start()

    def scan_library(self):
        self.library.scan_async(config.library_folders(self.cfg))

    def owned(self, video_id) -> bool:
        """True if this YouTube video is already in your music folders or rbgrab's XML."""
        if not video_id:
            return False
        return bool(self.library.find(video_id)
                    or library.find_video(config.xml_path(self.cfg), video_id))

    def _job_update(self, job, state, pct, text):
        job.state, job.pct, job.text, job.updated = state, pct, text, time.time()
        self.bar.refresh_jobs()

    def notify(self, title, message, kind="info"):
        if self.bar.visible() and kind in ("done", "dupe", "error"):
            return  # the open bar already shows this job's result
        try:
            self.toasts.show(title, message, kind)
            return
        except Exception:
            log.exception("toast failed")
        if platform.notify(title, message):
            return
        if self.tray is not None:
            try:
                self.tray.notify(message, title)
            except Exception:
                log.exception("notification failed")

    # ---------- menu actions ----------
    def open_settings(self, welcome=False):
        self.bar.hide()
        if self.settings is not None:
            self.settings.win.lift()
            self.settings.win.focus_force()
            return
        from .settings import Settings
        self.settings = Settings(self, welcome)

    def open_folder(self):
        path = Path(self.cfg["download_dir"])
        path.mkdir(parents=True, exist_ok=True)
        self.bar.hide()
        platform.open_path(path)

    def set_hotkey(self, combo) -> bool:
        if not self.hotkey.set(combo):
            return False
        self.cfg["hotkey"] = combo
        config.save(self.cfg)
        if self.tray is not None:
            self.tray.update_menu()
        return True

    def set_login(self, enabled: bool):
        self.cfg["start_at_login"] = enabled
        config.save(self.cfg)
        self._apply_login()

    def _apply_login(self):
        try:
            platform.set_start_at_login(self.cfg["start_at_login"], config.launch_command())
        except Exception:
            log.exception("could not change start-at-login")

    def update_ytdlp(self):
        def work():
            msg = download.update_ytdlp()
            self.post(self.notify, "yt-dlp", msg)

        threading.Thread(target=work, daemon=True).start()

    def _auto_update_ytdlp(self):
        """yt-dlp needs regular updates to keep up with YouTube; check weekly."""
        if time.time() - self.cfg.get("ytdlp_checked", 0) < 7 * 86400 or not download.updatable():
            return
        try:
            log.info("yt-dlp update: %s", download.update_ytdlp())
        except Exception:
            log.exception("yt-dlp update failed")
        self.cfg["ytdlp_checked"] = time.time()
        self.post(config.save, self.cfg)

    def quit(self):
        self.hotkey.stop()
        if self.tray is not None:
            self.tray.stop()
        self.root.destroy()
