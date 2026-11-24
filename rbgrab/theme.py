"""Colors, fonts and sizing shared by the windows."""
import math
import time
import tkinter as tk
import tkinter.font as tkfont

from .config import IS_WIN

BG = "#141418"
ROW = "#1E1E25"
SEL = "#262631"
LINE = "#2A2A34"
TEXT = "#ECECF1"
MUTED = "#8B8B9A"
FAINT = "#5C5C6B"
ACCENT = "#4CC2FF"
OK = "#4ADE80"
WARN = "#FBBF24"
ERR = "#F87171"

_FAMILIES = ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", ".AppleSystemUIFont",
             "Helvetica Neue", "Helvetica")


class Theme:
    def __init__(self, root):
        available = set(tkfont.families(root))
        family = next((f for f in _FAMILIES if f in available), "TkDefaultFont")
        size = 1 if IS_WIN else 1.25  # macOS points render smaller
        self.big = (family, round(15 * size))
        self.title = (family, round(11 * size), "bold")
        self.body = (family, round(10 * size))
        self.small = (family, round(9 * size))
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96) if IS_WIN else 1.0

    def px(self, n) -> int:
        return int(n * self.scale)


REVEAL_SECONDS = 0.6


def _wave_edge(p: float, t: float):
    """Leading edge of the reveal at progress p: a forward bulge with a rippling wave
    that calms down and flattens as it reaches the right side."""
    calm = (1 - p) ** 1.2
    bulge, ripple = 0.16 * calm, 0.09 * calm     # fractions of the window width
    lead = bulge + ripple
    base = -lead + (1 + 2 * lead) * (1 - (1 - p) ** 3)  # ease-out sweep, fully off-screen at both ends
    phase = t * 22

    def edge(y):
        return (base + bulge * (1 - (2 * y - 1) ** 2)
                + ripple * math.sin(2 * math.pi * 2.2 * y + phase))

    return edge


def reveal(win):
    """Sweep the window in from the left behind a liquid, wavy edge while it fades up.

    The window paints while fully transparent first, so no white frame ever flashes.
    """
    from . import platform

    win.attributes("-alpha", 0.0)
    win.deiconify()
    win.lift()
    win.update()
    clips = platform.clip_reveal(win, _wave_edge(0.0, 0.0))
    start = time.perf_counter()
    token = win._reveal = object()  # a newer reveal of this window cancels this one

    def frame():
        if not win.winfo_exists() or win._reveal is not token:
            return
        t = time.perf_counter() - start
        p = min(1.0, t / REVEAL_SECONDS)
        if clips:
            platform.clip_reveal(win, _wave_edge(p, t) if p < 1 else None)
        win.attributes("-alpha", 1 - (1 - min(1.0, p * 1.6)) ** 2)  # materializes as it flows in
        if p < 1:
            win.after(8, frame)

    frame()


def entry(parent, font, **kw):
    """Text box with a visible blinking caret and Ctrl+Backspace / Ctrl+Delete word deletion."""
    box = tk.Entry(parent, font=font, fg=TEXT, insertbackground=ACCENT, insertwidth=2,
                   insertontime=530, insertofftime=530, relief="flat", bd=0, highlightthickness=0,
                   selectbackground=SEL, selectforeground=TEXT, **kw)
    box.bind("<Control-BackSpace>", lambda e: _delete_word(box, back=True))
    box.bind("<Control-Delete>", lambda e: _delete_word(box, back=False))
    return box


def _delete_word(box, back: bool):
    if box.selection_present():
        box.delete("sel.first", "sel.last")
        return "break"
    text, pos = box.get(), box.index("insert")
    if back:
        start = pos
        while start > 0 and text[start - 1].isspace():
            start -= 1
        while start > 0 and not text[start - 1].isspace():
            start -= 1
        box.delete(start, pos)
    else:
        end = pos
        while end < len(text) and text[end].isspace():
            end += 1
        while end < len(text) and not text[end].isspace():
            end += 1
        box.delete(pos, end)
    return "break"  # stop Tk from also inserting a stray character


def clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def button(parent, text, command, accent=False, font=None):
    return tk.Button(parent, text=text, command=command, font=font, relief="flat", bd=0,
                     bg=ACCENT if accent else ROW, fg=BG if accent else TEXT,
                     activebackground=SEL if not accent else "#7BD3FF",
                     activeforeground=TEXT if not accent else BG,
                     padx=12, pady=5, cursor="hand2", highlightthickness=0)
