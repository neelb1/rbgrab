"""macOS backend: pynput hotkey, borderless Tk window, LaunchAgent autostart."""
import plistlib
import subprocess
from pathlib import Path

from .. import hotkey

__all__ = ["HotkeyListener", "prepare_process", "make_borderless", "style_window", "dark_titlebar",
           "clip_reveal",
           "focus_window", "show_without_focus",
           "work_area", "notify", "set_start_at_login", "open_path", "needs_input_permission",
           "open_permission_settings"]

_AGENT = Path.home() / "Library" / "LaunchAgents" / "com.rbgrab.app.plist"
_PYNPUT_MODS = {"ctrl": "<ctrl>", "alt": "<alt>", "shift": "<shift>", "cmd": "<cmd>"}


class HotkeyListener:
    """Global hotkey through pynput. Needs Input Monitoring permission."""

    def __init__(self, callback):
        self.callback = callback
        self._listener = None

    def set(self, combo: str) -> bool:
        from pynput import keyboard
        self.stop()
        mods, key = hotkey.parse(combo)
        key = f"<{key}>" if len(key) > 1 else key
        spec = "+".join([_PYNPUT_MODS[m] for m in hotkey.MODS if m in mods] + [key])
        self._listener = keyboard.GlobalHotKeys({spec: self.callback})
        self._listener.start()
        return True

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def trusted(self) -> bool:
        return bool(getattr(self._listener, "IS_TRUSTED", True))


def prepare_process():
    pass


def make_borderless(win):
    try:
        win.tk.call("::tk::unsupported::MacWindowStyle", "style", win._w, "plain", "none")
    except Exception:
        win.overrideredirect(True)


def style_window(win):
    pass


def clip_reveal(win, edge) -> bool:
    return False  # Tk can't clip windows on macOS; reveal() just fades in


def dark_titlebar(win):
    try:
        win.tk.call("::tk::unsupported::MacWindowStyle", "appearance", win._w, "darkaqua")
    except Exception:
        pass


def focus_window(win):
    win.deiconify()
    win.lift()
    win.attributes("-topmost", True)
    try:
        from AppKit import NSApp  # comes with pystray's pyobjc dependency
        NSApp.activateIgnoringOtherApps_(True)
    except Exception:
        pass
    win.focus_force()


def work_area(win):
    return 0, 25, win.winfo_screenwidth(), win.winfo_screenheight() - 25


def show_without_focus(win):
    win.deiconify()  # overrideredirect windows don't take key focus on macOS


def notify(title, message) -> bool:
    script = f"display notification {_q(message)} with title {_q(title)}"
    subprocess.Popen(["osascript", "-e", script])
    return True


def _q(text) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_start_at_login(enabled: bool, command):
    if enabled:
        _AGENT.parent.mkdir(parents=True, exist_ok=True)
        _AGENT.write_bytes(plistlib.dumps({
            "Label": "com.rbgrab.app", "ProgramArguments": list(command), "RunAtLoad": True}))
    else:
        _AGENT.unlink(missing_ok=True)


def open_path(path):
    subprocess.Popen(["open", str(path)])


def needs_input_permission() -> bool:
    return True


def open_permission_settings():
    subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"])
