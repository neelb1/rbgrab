"""Tray icon (Windows) / menu bar icon (macOS)."""
import threading

from . import hotkey
from .config import IS_MAC
from .icon import draw


def start(app):
    import pystray

    item = pystray.MenuItem
    menu = pystray.Menu(
        item(lambda _: f"Search    {hotkey.display(app.cfg['hotkey'])}", lambda: app.post(app.show),
             default=True),
        item("Open downloads folder", lambda: app.post(app.open_folder)),
        item("Settings", lambda: app.post(app.open_settings)),
        item("Update yt-dlp", lambda: app.post(app.update_ytdlp)),
        pystray.Menu.SEPARATOR,
        item("Quit rbgrab", lambda: app.post(app.quit)),
    )
    icon = pystray.Icon("rbgrab", draw(64), "rbgrab", menu)
    if IS_MAC:
        icon.run_detached()  # macOS: shares the main thread's event loop with Tk
    else:
        threading.Thread(target=icon.run, daemon=True, name="tray").start()
    return icon
