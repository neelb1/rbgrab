"""Small corner toasts ("Added to rekordbox") that never take focus from your DJ software."""
import time
import tkinter as tk

from . import platform
from . import theme as t

WIDTH = 340
COLORS = {"done": t.OK, "dupe": t.WARN, "error": t.ERR, "info": t.ACCENT}
ICONS = {"done": "✓", "dupe": "•", "error": "!", "info": "i"}
SECONDS = {"error": 7.0}
FADE_IN, FADE_OUT, DEFAULT_SECONDS = 0.18, 0.3, 4.5


class Toasts:
    def __init__(self, root, th):
        self.root, self.th = root, th
        self.live = []  # newest last; stacked upwards from the bottom-right corner

    def show(self, title, message="", kind="info"):
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)
        win.configure(bg=t.LINE)

        px = self.th.px
        card = tk.Frame(win, bg=t.BG, padx=px(14), pady=px(11))
        card.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(card, bg=COLORS.get(kind, t.ACCENT), width=px(3)).pack(side="left", fill="y", padx=(0, px(12)))
        tk.Label(card, text=ICONS.get(kind, "i"), font=self.th.title, fg=COLORS.get(kind, t.ACCENT), width=2,
                 bg=t.BG).pack(side="left", anchor="n", padx=(0, px(10)))
        text = tk.Frame(card, bg=t.BG)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=t.clip(title, 44), font=self.th.title, fg=t.TEXT, bg=t.BG,
                 anchor="w", justify="left").pack(fill="x")
        if message:
            tk.Label(text, text=message, font=self.th.small, fg=t.MUTED, bg=t.BG, anchor="w",
                     justify="left", wraplength=px(WIDTH - 90)).pack(fill="x", pady=(px(2), 0))

        win.update_idletasks()
        toast = {"win": win, "h": win.winfo_reqheight(), "y": None, "closing": False}
        for w in [win, card, text, *card.winfo_children(), *text.winfo_children()]:
            w.bind("<Button-1>", lambda e, toast=toast: self._close(toast))

        self.live.append(toast)
        self._layout()
        platform.show_without_focus(win)
        platform.style_window(win)
        self._animate(toast, FADE_IN, 0.0, 0.97)
        self.root.after(int(SECONDS.get(kind, DEFAULT_SECONDS) * 1000), lambda: self._close(toast))

    def _layout(self):
        """Stack toasts bottom-up; each one glides to its slot."""
        x, y, w, h = platform.work_area(self.root)
        px = self.th.px
        bottom = y + h - px(16)
        for toast in reversed(self.live):
            bottom -= toast["h"]
            target = bottom
            bottom -= px(10)
            start = toast["y"] if toast["y"] is not None else target + px(18)  # new ones rise in
            toast["y"] = target
            self._glide(toast, x + w - px(WIDTH) - px(16), start, target)

    def _glide(self, toast, x, y0, y1, ms=180):
        win, began = toast["win"], time.perf_counter()
        token = toast["glide"] = object()

        def step():
            if not win.winfo_exists() or toast["glide"] is not token:
                return
            p = min(1.0, (time.perf_counter() - began) * 1000 / ms)
            ease = 1 - (1 - p) ** 3
            win.geometry(f"{self.th.px(WIDTH)}x{toast['h']}+{x}+{int(y0 + (y1 - y0) * ease)}")
            if p < 1:
                self.root.after(8, step)

        step()

    def _animate(self, toast, seconds, a0, a1, done=None):
        win, began = toast["win"], time.perf_counter()

        def step():
            if not win.winfo_exists():
                return
            p = min(1.0, (time.perf_counter() - began) / seconds)
            win.attributes("-alpha", a0 + (a1 - a0) * p)
            if p < 1:
                self.root.after(10, step)
            elif done:
                done()

        step()

    def _close(self, toast):
        if toast["closing"] or not toast["win"].winfo_exists():
            return
        toast["closing"] = True

        def gone():
            toast["win"].destroy()
            if toast in self.live:
                self.live.remove(toast)
                self._layout()

        self._animate(toast, FADE_OUT, float(toast["win"].attributes("-alpha")), 0.0, gone)
