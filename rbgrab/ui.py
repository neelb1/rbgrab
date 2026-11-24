"""The search bar: type, pick a song, Enter."""
import threading
import time
import tkinter as tk

from . import hotkey, platform, search
from . import theme as t

MAX_RESULTS = 5
MAX_JOBS = 3
JOB_TTL = 120  # seconds a finished grab stays listed


class SearchBar:
    def __init__(self, app):
        self.app = app
        self.th = t.Theme(app.root)
        self.width = self.th.px(640)
        self.win = tk.Toplevel(app.root, bg=t.BG)
        self.win.withdraw()
        platform.make_borderless(self.win)
        self.win.attributes("-topmost", True)
        self.results, self.results_for, self.sel = [], None, 0
        self.status_text = ""
        self.seq = 0
        self._pending = None
        self._last = ""
        self._pos = None
        self._styled = False
        self._build()

    # ---------- layout ----------
    def _build(self):
        px, th = self.th.px, self.th
        self.outer = outer = tk.Frame(self.win, bg=t.BG, padx=px(16), pady=px(14))
        outer.pack(fill="both", expand=True)

        top = tk.Frame(outer, bg=t.BG)
        top.pack(fill="x")
        tk.Label(top, text="♫", font=th.big, fg=t.ACCENT, bg=t.BG).pack(side="left")
        self.hint = tk.Label(top, font=th.small, fg=t.FAINT, bg=t.BG)
        self.hint.pack(side="right")
        self.var = tk.StringVar()
        self.entry = t.entry(top, th.big, textvariable=self.var, bg=t.BG)
        self.entry.pack(side="left", fill="x", expand=True, padx=px(10), ipady=px(4))
        self.placeholder = tk.Label(top, text="Search YouTube Music or paste a link",
                                    font=th.big, fg=t.FAINT, bg=t.BG)
        self.placeholder.bind("<Button-1>", lambda e: self.entry.focus_set())

        self.sep = tk.Frame(outer, bg=t.LINE, height=1)
        self.body = tk.Frame(outer, bg=t.BG)
        self.status = tk.Label(self.body, font=th.body, fg=t.MUTED, bg=t.BG, anchor="w")
        self.rows = [self._make_row(i) for i in range(MAX_RESULTS)]

        self.jobs_sep = tk.Frame(outer, bg=t.LINE, height=1)
        self.jobs_frame = tk.Frame(outer, bg=t.BG)
        self.job_rows = [self._make_job_row() for _ in range(MAX_JOBS)]

        self.footer = footer = tk.Frame(outer, bg=t.BG)
        tk.Label(footer, text="↑↓ choose    Enter grab    Esc close", font=th.small,
                 fg=t.FAINT, bg=t.BG).pack(side="left")
        for text, action in (("Settings", self.app.open_settings), ("Open folder", self.app.open_folder)):
            link = tk.Label(footer, text=text, font=th.small, fg=t.MUTED, bg=t.BG, cursor="hand2")
            link.pack(side="right", padx=(px(12), 0))
            link.bind("<Button-1>", lambda e, a=action: a())
            link.bind("<Enter>", lambda e, w=link: w.config(fg=t.ACCENT))
            link.bind("<Leave>", lambda e, w=link: w.config(fg=t.MUTED))

        self.var.trace_add("write", self._on_text)
        self.entry.bind("<Return>", self._enter)
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Escape>", lambda e: self.hide())
        self.win.bind("<FocusOut>", lambda e: self.win.after(150, self._check_focus))
        self._show_placeholder()

    def _make_row(self, i):
        px, th = self.th.px, self.th
        row = tk.Frame(self.body, bg=t.BG, cursor="hand2")
        bar = tk.Frame(row, bg=t.BG, width=px(3))
        bar.pack(side="left", fill="y")
        dur = tk.Label(row, font=th.small, fg=t.FAINT, bg=t.BG)
        dur.pack(side="right", padx=px(10))
        text = tk.Frame(row, bg=t.BG)
        text.pack(side="left", fill="x", expand=True, padx=px(10), pady=px(5))
        title = tk.Label(text, font=th.title, fg=t.TEXT, bg=t.BG, anchor="w")
        title.pack(fill="x")
        sub = tk.Label(text, font=th.small, fg=t.MUTED, bg=t.BG, anchor="w")
        sub.pack(fill="x")
        for w in (row, bar, text, title, sub, dur):
            w.bind("<Enter>", lambda e: self._select(i))
            w.bind("<Button-1>", lambda e: self._pick(i))
        return {"row": row, "bar": bar, "paint": (row, text, title, sub, dur),
                "title": title, "sub": sub, "dur": dur}

    def _make_job_row(self):
        px, th = self.th.px, self.th
        row = tk.Frame(self.jobs_frame, bg=t.BG)
        line = tk.Frame(row, bg=t.BG)
        line.pack(fill="x")
        icon = tk.Label(line, font=th.title, bg=t.BG, width=2)
        icon.pack(side="left")
        right = tk.Label(line, font=th.small, fg=t.MUTED, bg=t.BG)
        right.pack(side="right")
        text = tk.Label(line, font=th.body, fg=t.TEXT, bg=t.BG, anchor="w")
        text.pack(side="left", fill="x", expand=True)
        track = tk.Frame(row, bg=t.LINE, height=px(2))
        fill = tk.Frame(track, bg=t.ACCENT)
        return {"row": row, "icon": icon, "text": text, "right": right, "track": track, "fill": fill}

    def _layout(self):
        px = self.th.px
        for w in (self.sep, self.body, self.jobs_sep, self.jobs_frame, self.footer):
            w.pack_forget()
        if self.results or self.status_text:
            self.sep.pack(fill="x", pady=(px(12), px(6)))
            self.body.pack(fill="x")
        if self._visible_jobs():
            self.jobs_sep.pack(fill="x", pady=(px(8), px(6)))
            self.jobs_frame.pack(fill="x")
        self.footer.pack(fill="x", pady=(px(12), 0))
        self._resize()

    def _resize(self):
        self.win.update_idletasks()
        height = self.outer.winfo_reqheight()
        if self._pos is None:
            x, y, w, h = platform.work_area(self.win)
            self._pos = (x + (w - self.width) // 2, y + h // 4)
        self.win.geometry(f"{self.width}x{height}+{self._pos[0]}+{self._pos[1]}")

    # ---------- show / hide ----------
    def visible(self) -> bool:
        return bool(self.win.winfo_viewable())

    def toggle(self):
        if self.visible():
            self.hide()
        else:
            self.show()

    def show(self):
        self.hint.config(text=hotkey.display(self.app.cfg["hotkey"]))
        self._pos = None
        self._render_jobs()
        self._layout()
        self.win.attributes("-alpha", 0.0)  # invisible until t.reveal() wipes it in
        platform.focus_window(self.win)
        if not self._styled:
            platform.style_window(self.win)
            self._styled = True
        self.entry.focus_force()
        self.entry.icursor("end")
        self.entry.select_range(0, "end")
        t.reveal(self.win)

    def hide(self):
        self.win.withdraw()

    def _check_focus(self):
        if self.visible() and self.win.focus_displayof() is None:
            self.hide()

    # ---------- typing / searching ----------
    def _show_placeholder(self):
        if self.var.get():
            self.placeholder.place_forget()
        else:
            self.placeholder.place(in_=self.entry, x=self.th.px(6), rely=0.5, anchor="w")  # leave room for the caret

    def _on_text(self, *_):
        self._show_placeholder()
        text = self.var.get().strip()
        if text == self._last:
            return
        self._last = text
        if self._pending:
            self.win.after_cancel(self._pending)
            self._pending = None
        self.seq += 1
        if not text:
            self._set_results([], None, "")
        elif search.is_url(text):
            self._set_results([], None, "Link detected  -  press Enter to grab it")
        else:
            if not self.results:
                self._set_results([], None, "Searching…")
            seq = self.seq
            self._pending = self.win.after(220, lambda: self._start_search(text, seq))

    def _start_search(self, text, seq):
        self._pending = None

        def work():
            try:
                found, err = search.search(text, MAX_RESULTS), None
            except Exception as e:  # network down, etc.
                found, err = [], e
            self.app.post(self._got_results, seq, text, found, err)

        threading.Thread(target=work, daemon=True).start()

    def _got_results(self, seq, text, found, err):
        if seq != self.seq:
            return  # the user kept typing
        status = "" if found else ("Search failed  -  check your connection" if err else "No songs found")
        self._set_results(found, text, status)

    def _set_results(self, results, query, status):
        self.results, self.results_for, self.sel = results, query, 0
        self.status_text = status
        if status:
            self.status.config(text=status)
            self.status.pack(fill="x", padx=self.th.px(4), pady=self.th.px(4))
        else:
            self.status.pack_forget()
        for i, r in enumerate(self.rows):
            if i < len(results):
                item = results[i]
                r["title"].config(text=t.clip(item["title"], 62))
                sub = item["artist"] + ("  ·  video" if item.get("kind") == "video" else "")
                r["sub"].config(text=t.clip(sub, 70))
                if self.app.owned(item["id"]):
                    owned = "✓ in library" + (f"  ·  {item['duration']}" if item["duration"] else "")
                    r["dur"].config(text=owned, fg=t.OK)
                else:
                    r["dur"].config(text=item["duration"], fg=t.FAINT)
                r["row"].pack(fill="x")
            else:
                r["row"].pack_forget()
        self._paint()
        if self.visible():
            self._layout()

    def _paint(self):
        for i, r in enumerate(self.rows):
            bg = t.SEL if i == self.sel else t.BG
            for w in r["paint"]:
                w.config(bg=bg)
            r["bar"].config(bg=t.ACCENT if i == self.sel else bg)

    def _select(self, i):
        if i < len(self.results) and i != self.sel:
            self.sel = i
            self._paint()

    def _move(self, step):
        if self.results:
            self.sel = (self.sel + step) % len(self.results)
            self._paint()
        return "break"

    # ---------- grabbing ----------
    def _enter(self, _=None):
        text = self.var.get().strip()
        if not text:
            return "break"
        if self.results and self.results_for == text:
            self._submit(self.results[self.sel])
        else:
            self._submit(text)  # not searched yet: grab the top result
        return "break"

    def _pick(self, i):
        if i < len(self.results):
            self._submit(self.results[i])

    def _submit(self, target):
        self.app.grab(target)
        self.var.set("")
        if self.app.cfg["hide_after_grab"]:
            self.hide()

    # ---------- download queue ----------
    def _visible_jobs(self):
        now = time.time()
        return [j for j in self.app.jobs
                if j.state not in ("done", "dupe", "error") or now - j.updated < JOB_TTL][:MAX_JOBS]

    def refresh_jobs(self):
        if self.visible():
            self._render_jobs()
            self._layout()

    def _render_jobs(self):
        jobs = self._visible_jobs()
        styles = {"search": ("…", t.MUTED), "download": ("↓", t.ACCENT), "done": ("✓", t.OK),
                  "dupe": ("•", t.WARN), "error": ("✕", t.ERR)}
        for i, r in enumerate(self.job_rows):
            if i >= len(jobs):
                r["row"].pack_forget()
                continue
            job = jobs[i]
            icon, color = styles[job.state]
            right = {"search": "searching", "download": f"{int(job.pct * 100)}%",
                     "done": "added", "dupe": "already in library", "error": "failed"}[job.state]
            r["icon"].config(text=icon, fg=color)
            r["text"].config(text=t.clip(job.text, 58), fg=t.ERR if job.state == "error" else t.TEXT)
            r["right"].config(text=right)
            if job.state == "download":
                r["track"].pack(fill="x", padx=(self.th.px(26), 0), pady=(self.th.px(2), self.th.px(4)))
                r["fill"].place(x=0, y=0, relheight=1, relwidth=max(job.pct, 0.01))
            else:
                r["track"].pack_forget()
            r["row"].pack(fill="x", pady=self.th.px(2))
