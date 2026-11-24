"""Settings window, also shown on first run with the rekordbox setup steps."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from . import config, hotkey, platform
from . import theme as t


class Settings:
    def __init__(self, app, welcome=False):
        self.app, self.cfg, self.welcome = app, app.cfg, welcome
        self.th = th = t.Theme(app.root)
        self.win = w = tk.Toplevel(app.root, bg=t.BG)
        w.withdraw()  # stay hidden until built and positioned, or a blank box flashes
        w.title("rbgrab")
        # Borderless like the search bar: a native title bar flashes white during the wave reveal.
        platform.make_borderless(w)
        w.attributes("-topmost", True)
        self.held = set()
        self.recording = False
        px = th.px
        self.box = tk.Frame(w, bg=t.BG, padx=px(22), pady=px(16))
        self.box.pack(fill="both", expand=True)

        shortcut = hotkey.display(self.cfg["hotkey"])
        self._header("Welcome to rbgrab" if welcome else "Settings")
        if welcome:
            self._label(f"Press {shortcut} anywhere to search. One-time setup below.", th.body, t.MUTED)
        w.bind("<Escape>", lambda e: self._finish_record(None) if self.recording else self.close())

        self._section("Shortcut")
        row = self._row()
        self.hk_label = tk.Label(row, text=shortcut, font=th.title, fg=t.ACCENT, bg=t.BG)
        self.hk_label.pack(side="left")
        t.button(row, "Change", self._record, font=th.body).pack(side="right")
        self.hk_msg = self._label("", th.small, t.MUTED)

        if platform.needs_input_permission():
            self._section("macOS permission")
            self._label("Allow rbgrab under Privacy & Security → Input Monitoring so the shortcut works.",
                        th.body, t.MUTED)
            t.button(self._row(), "Open Privacy settings", platform.open_permission_settings,
                     font=th.body).pack(side="left")

        self._section("Downloads")
        row = self._row()
        self.dir_label = tk.Label(row, font=th.body, fg=t.TEXT, bg=t.BG, anchor="w")
        self.dir_label.pack(side="left", fill="x", expand=True)
        t.button(row, "Change…", self._pick_dir, font=th.body).pack(side="right")
        row = self._row()
        self.fmt = tk.StringVar(value=self.cfg["format"])
        for value, text in (("m4a", "M4A  (original quality, faster)"), ("mp3", "MP3 320")):
            tk.Radiobutton(row, text=text, value=value, variable=self.fmt, command=self._save_fmt,
                           font=th.body, fg=t.TEXT, bg=t.BG, selectcolor=t.ROW, activebackground=t.BG,
                           activeforeground=t.TEXT, highlightthickness=0, bd=0).pack(side="left", padx=(0, px(16)))
        row = self._row()
        tk.Label(row, text="Playlist name", font=th.body, fg=t.MUTED, bg=t.BG).pack(side="left")
        self.playlist = t.entry(row, th.body, bg=t.ROW, width=22)
        self.playlist.insert(0, self.cfg["playlist"])
        self.playlist.pack(side="right", ipady=px(3))
        self.playlist.bind("<FocusOut>", self._save_playlist)
        self.playlist.bind("<Return>", self._save_playlist)

        self._section("Your library")
        self._label("Songs you already have show “✓ in library” and aren't downloaded again. "
                    "rbgrab checks the download folder plus these folders:", th.body, t.MUTED)
        row = self._row()
        self.lib_label = tk.Label(row, font=th.body, fg=t.TEXT, bg=t.BG, anchor="w", justify="left")
        self.lib_label.pack(side="left", fill="x", expand=True)
        t.button(row, "Clear", self._clear_library, font=th.body).pack(side="right", padx=(px(6), 0))
        t.button(row, "Add folder…", self._add_library, font=th.body).pack(side="right")

        self._section("rekordbox setup (once)")
        for step in ("1.  Preferences → Advanced → Database → rekordbox xml → Browse… and pick:",):
            self._label(step, th.body, t.TEXT)
        row = self._row()
        self.xml_label = tk.Label(row, font=th.small, fg=t.ACCENT, bg=t.BG, anchor="w")
        self.xml_label.pack(side="left", fill="x", expand=True, padx=(px(18), 0))
        self.copy_btn = t.button(row, "Copy path", self._copy, font=th.body)
        self.copy_btn.pack(side="right")
        self._label("2.  Preferences → View → Layout → tick “rekordbox xml”.", th.body, t.TEXT)
        self.steps3 = self._label("", th.body, t.TEXT)

        self._section("General")
        self.login = tk.BooleanVar(value=self.cfg["start_at_login"])
        self.autohide = tk.BooleanVar(value=self.cfg["hide_after_grab"])
        for var, text, cmd in ((self.login, "Start rbgrab when I log in", self._save_login),
                               (self.autohide, "Hide the search bar after grabbing", self._save_hide)):
            tk.Checkbutton(self.box, text=text, variable=var, command=cmd, font=th.body, fg=t.TEXT,
                           bg=t.BG, selectcolor=t.ROW, activebackground=t.BG, activeforeground=t.TEXT,
                           highlightthickness=0, bd=0, anchor="w").pack(fill="x", pady=px(2))
        row = self._row()
        t.button(row, "Update yt-dlp", self._update, font=th.body).pack(side="left")
        self.update_msg = tk.Label(row, font=th.small, fg=t.MUTED, bg=t.BG)
        self.update_msg.pack(side="left", padx=px(10))

        row = self._row(pady=(px(12), 0))
        t.button(row, "Done", self.close, accent=True, font=th.title).pack(side="right")
        self._refresh_paths()
        w.update_idletasks()
        x, y, sw, sh = platform.work_area(w)
        w.geometry(f"+{x + (sw - w.winfo_reqwidth()) // 2}+{y + max(0, (sh - w.winfo_reqheight()) // 3)}")
        platform.style_window(w)  # rounded corners + subtle border, same as the bar
        t.reveal(w)
        platform.focus_window(w)

    # ---------- small builders ----------
    def _header(self, title):
        """Title row that replaces the native title bar: drag to move, ✕ to close."""
        bar = tk.Frame(self.box, bg=t.BG, cursor="fleur")
        bar.pack(fill="x", pady=(0, self.th.px(4)))
        title_label = tk.Label(bar, text=title, font=self.th.big, fg=t.TEXT, bg=t.BG)
        title_label.pack(side="left")
        close = tk.Label(bar, text="✕", font=self.th.title, fg=t.MUTED, bg=t.BG, cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.close())
        close.bind("<Enter>", lambda e: close.config(fg=t.ERR))
        close.bind("<Leave>", lambda e: close.config(fg=t.MUTED))
        for widget in (bar, title_label):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag)

    def _drag_start(self, e):
        self._drag_from = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _drag(self, e):
        dx, dy = self._drag_from
        self.win.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")
    def _label(self, text, font, fg):
        label = tk.Label(self.box, text=text, font=font, fg=fg, bg=t.BG, anchor="w", justify="left",
                         wraplength=self.th.px(560))
        label.pack(fill="x", pady=self.th.px(1))
        return label

    def _section(self, title):
        if self.box.winfo_children():  # no divider above the first section
            tk.Frame(self.box, bg=t.LINE, height=1).pack(fill="x", pady=(self.th.px(10), self.th.px(6)))
        tk.Label(self.box, text=title.upper(), font=self.th.small, fg=t.FAINT, bg=t.BG,
                 anchor="w").pack(fill="x", pady=(0, self.th.px(4)))

    def _row(self, pady=None):
        row = tk.Frame(self.box, bg=t.BG)
        row.pack(fill="x", pady=pady if pady is not None else self.th.px(2))
        return row

    def _save(self):
        config.save(self.cfg)

    def _refresh_paths(self):
        extra = self.cfg.get("library_dirs") or []
        self.lib_label.config(text="\n".join(t.clip(d, 44) for d in extra) or "No extra folders yet",
                              fg=t.TEXT if extra else t.FAINT)
        self.dir_label.config(text=t.clip(self.cfg["download_dir"], 52))
        self.xml_label.config(text=t.clip(str(config.xml_path(self.cfg)), 60))
        self.steps3.config(text=f"3.  Grabs land in rekordbox xml → Playlists → {self.cfg['playlist']}. "
                                "Click the refresh icon on “rekordbox xml” to see new ones.")

    # ---------- actions ----------
    def _record(self):
        self.app.hotkey.stop()  # free the current shortcut so it can be pressed again
        self.held.clear()
        self.recording = True
        self.hk_label.config(text="Press a shortcut…")
        self.hk_msg.config(text="Esc to cancel", fg=t.MUTED)
        self.win.bind("<KeyPress>", self._key_down)
        self.win.bind("<KeyRelease>", lambda e: self.held.discard(e.keysym))
        self.win.focus_force()

    def _key_down(self, e):
        if e.keysym == "Escape":
            self._finish_record(None)
        elif hotkey.is_modifier(e.keysym):
            self.held.add(e.keysym)
        else:
            combo = hotkey.from_tk(self.held, e.keysym)
            if combo:
                self._finish_record(combo)
            else:
                self.hk_msg.config(text="Hold a modifier (Ctrl, Alt, Shift, Win/⌘) and press a letter, "
                                        "number, F-key or Space.", fg=t.WARN)
        return "break"

    def _finish_record(self, combo):
        self.recording = False
        self.win.unbind("<KeyPress>")
        self.win.unbind("<KeyRelease>")
        if combo and self.app.set_hotkey(combo):
            self.hk_msg.config(text="Saved.", fg=t.OK)
        else:
            self.app.set_hotkey(self.cfg["hotkey"])
            if combo:
                self.hk_msg.config(text=f"{hotkey.display(combo)} is taken by another app. Try another.",
                                   fg=t.ERR)
            else:
                self.hk_msg.config(text="")
        self.hk_label.config(text=hotkey.display(self.cfg["hotkey"]))

    def _pick_dir(self):
        chosen = filedialog.askdirectory(parent=self.win, initialdir=self.cfg["download_dir"])
        if chosen:
            self.cfg["download_dir"] = str(Path(chosen))
            self._save()
            self._refresh_paths()
            self.hk_msg.config(text="")
            self.update_msg.config(text="New folder: point rekordbox at the new XML path above.",
                                   fg=t.WARN)

    def _add_library(self):
        chosen = filedialog.askdirectory(parent=self.win, title="Folder with your music")
        if chosen:
            folders = list(self.cfg.get("library_dirs") or [])
            if str(Path(chosen)) not in folders:
                folders.append(str(Path(chosen)))
            self.cfg["library_dirs"] = folders
            self._save()
            self._refresh_paths()
            self.app.scan_library()

    def _clear_library(self):
        self.cfg["library_dirs"] = []
        self._save()
        self._refresh_paths()

    def _save_fmt(self):
        self.cfg["format"] = self.fmt.get()
        self._save()

    def _save_playlist(self, _=None):
        name = self.playlist.get().strip()
        if name and name != self.cfg["playlist"]:
            self.cfg["playlist"] = name
            self._save()
            self._refresh_paths()

    def _save_login(self):
        self.app.set_login(self.login.get())

    def _save_hide(self):
        self.cfg["hide_after_grab"] = self.autohide.get()
        self._save()

    def _copy(self):
        self.win.clipboard_clear()
        self.win.clipboard_append(str(config.xml_path(self.cfg)))
        self.copy_btn.config(text="Copied ✓")
        self.win.after(1500, lambda: self.copy_btn.config(text="Copy path"))

    def _update(self):
        self.update_msg.config(text="Updating…", fg=t.MUTED)
        from . import download

        def work():
            try:
                msg = download.update_ytdlp()
            except Exception as e:
                msg = f"Update failed: {e}"
            self.app.post(lambda: self.win.winfo_exists() and self.update_msg.config(text=t.clip(msg, 60)))

        threading.Thread(target=work, daemon=True).start()

    def close(self):
        self._save_playlist()
        if self.welcome:
            self.cfg["first_run_done"] = True
            self._save()
        self.win.destroy()
        self.app.settings = None
