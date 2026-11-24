"""OS-specific pieces. Both modules expose the same names:

HotkeyListener(callback) with .set(hotkey) -> bool and .stop()
prepare_process(), make_borderless(win), style_window(win), dark_titlebar(win), focus_window(win),
show_without_focus(win) (show a toast without taking focus from other apps)
clip_reveal(win, edge) -> bool (edge(y)->x fractions or None; False if the OS cannot clip)
work_area(win) -> (x, y, w, h), notify(title, message) -> bool
set_start_at_login(enabled, command), open_path(path)
needs_input_permission() -> bool, open_permission_settings()
"""
import sys

if sys.platform == "darwin":
    from .macos import *  # noqa: F401,F403
else:
    from .windows import *  # noqa: F401,F403
