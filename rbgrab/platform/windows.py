"""Windows backend: Win32 RegisterHotKey, DWM styling, Run-key autostart."""
import ctypes
import os
import subprocess
import threading
from ctypes import wintypes

from .. import hotkey

__all__ = ["HotkeyListener", "prepare_process", "make_borderless", "style_window", "dark_titlebar",
           "clip_reveal",
           "focus_window", "show_without_focus",
           "work_area", "notify", "set_start_at_login", "open_path", "needs_input_permission",
           "open_permission_settings"]

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_MODS = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "cmd": 0x8}
_MOD_NOREPEAT = 0x4000
_WM_HOTKEY, _WM_QUIT = 0x0312, 0x0012
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _vk(key: str) -> int:
    if len(key) == 1:
        return ord(key.upper())
    if key == "space":
        return 0x20
    return 0x6F + int(key[1:])  # f1..f12


class HotkeyListener:
    """Registers one global hotkey on a background thread with its own message loop."""

    def __init__(self, callback):
        self.callback = callback
        self._thread = None
        self._tid = None

    def set(self, combo: str) -> bool:
        self.stop()
        mods, key = hotkey.parse(combo)
        flags = sum(_MODS[m] for m in mods) | _MOD_NOREPEAT
        result, ready = {}, threading.Event()

        def run():
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # create the message queue
            self._tid = kernel32.GetCurrentThreadId()
            result["ok"] = bool(user32.RegisterHotKey(None, 1, flags, _vk(key)))
            ready.set()
            if not result["ok"]:
                return
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == _WM_HOTKEY:
                    self.callback()
            user32.UnregisterHotKey(None, 1)

        thread = threading.Thread(target=run, daemon=True, name="hotkey")
        thread.start()
        ready.wait(2)
        if result.get("ok"):
            self._thread = thread
            return True
        return False

    def stop(self):
        if self._thread:
            user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)
            self._thread.join(1)
            self._thread = None


def prepare_process():
    """Crisp text on high-DPI screens and rbgrab's own taskbar icon; must run before Tk starts."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    # Without this, windows group under python.exe and show the Python icon in the taskbar.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("rbgrab.app")


def make_borderless(win):
    win.overrideredirect(True)


def _hwnd(win):
    return user32.GetParent(win.winfo_id()) or win.winfo_id()


def style_window(win):
    """Windows 11 rounded corners and a subtle border (no-op on Windows 10)."""
    dwm = ctypes.windll.dwmapi
    hwnd = _hwnd(win)
    for attr, value in ((33, 2), (34, 0x00382E2E)):  # corner = round, border color (BGR)
        val = ctypes.c_int(value)
        dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))


def clip_reveal(win, edge) -> bool:
    """Show only the part of the window left of a curved edge; edge=None removes the clip.

    edge(y) takes a 0..1 height fraction and returns a 0..1 width fraction.
    """
    hwnd = _hwnd(win)
    if edge is None:
        user32.SetWindowRgn(hwnd, None, True)
        return True
    gdi32 = ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    steps = 32
    pts = [(0, 0)] + [(min(w, max(0, int(edge(i / steps) * w))), int(h * i / steps))
                      for i in range(steps + 1)] + [(0, h)]
    arr = (wintypes.POINT * len(pts))(*[wintypes.POINT(x, y) for x, y in pts])
    wave = gdi32.CreatePolygonRgn(arr, len(pts), 2)
    radius = int(16 * max(1.0, win.winfo_fpixels("1i") / 96))
    rounded = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius, radius)
    gdi32.CombineRgn(wave, wave, rounded, 1)  # keep the window's rounded corners
    gdi32.DeleteObject(rounded)
    user32.SetWindowRgn(hwnd, wave, True)  # the window takes ownership of the region
    return True


def dark_titlebar(win):
    """Dark title bar that matches the window, even with accent-colored title bars on."""
    win.update_idletasks()
    # immersive dark mode, caption color, caption text color (colors are 0x00BBGGRR)
    for attr, value in ((20, 1), (35, 0x00181414), (36, 0x00F1ECEC)):
        val = ctypes.c_int(value)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(_hwnd(win), attr, ctypes.byref(val), ctypes.sizeof(val))


def focus_window(win):
    win.deiconify()
    win.lift()
    win.attributes("-topmost", True)
    hwnd = _hwnd(win)
    if not user32.SetForegroundWindow(hwnd):
        # Windows blocks focus stealing; a synthetic Alt tap lifts the restriction.
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)
    win.focus_force()


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


def work_area(win):
    """Work area of the monitor under the mouse, so the bar opens where you're looking."""
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    user32.MonitorFromPoint.restype = wintypes.HMONITOR
    mon = user32.MonitorFromPoint(pt, 2)
    info = _MONITORINFO(cbSize=ctypes.sizeof(_MONITORINFO))
    if user32.GetMonitorInfoW(mon, ctypes.byref(info)):
        r = info.rcWork
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    return 0, 0, win.winfo_screenwidth(), win.winfo_screenheight()


def show_without_focus(win):
    """Show a window without activating it, so rekordbox keeps keyboard focus."""
    win.update_idletasks()
    hwnd = _hwnd(win)
    style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
    # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW (no taskbar button) | WS_EX_TOPMOST
    user32.SetWindowLongW(hwnd, -20, style | 0x08000000 | 0x00000080 | 0x00000008)
    user32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
    # Tell Tk it's mapped without calling deiconify (which would take focus).
    win.wm_attributes("-topmost", True)


def notify(title, message) -> bool:
    return False  # the tray icon shows notifications on Windows


def set_start_at_login(enabled: bool, command):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "rbgrab", 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, "rbgrab")
            except FileNotFoundError:
                pass


def open_path(path):
    os.startfile(path)


def needs_input_permission() -> bool:
    return False


def open_permission_settings():
    pass
