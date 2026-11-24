"""Hotkey strings like "ctrl+alt+s": parsing, display, and capture from Tk key events."""
from .config import IS_MAC

MODS = ("ctrl", "alt", "shift", "cmd")  # cmd = the Windows key on Windows, ⌘ on macOS
_ALIASES = {"control": "ctrl", "option": "alt", "opt": "alt", "win": "cmd",
            "super": "cmd", "command": "cmd", "meta": "cmd"}
_NAMED = {"space"} | {f"f{i}" for i in range(1, 13)}
_MAC_SYMBOLS = {"ctrl": "⌃", "alt": "⌥", "shift": "⇧", "cmd": "⌘"}
_WIN_NAMES = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Win"}

_TK_MODS = {
    "Control_L": "ctrl", "Control_R": "ctrl",
    "Alt_L": "alt", "Alt_R": "alt", "Option_L": "alt", "Option_R": "alt",
    "Shift_L": "shift", "Shift_R": "shift",
    "Win_L": "cmd", "Win_R": "cmd", "Super_L": "cmd", "Super_R": "cmd",
    "Meta_L": "cmd", "Meta_R": "cmd", "Command": "cmd",
}


def _valid_key(key: str) -> bool:
    return (len(key) == 1 and key.isascii() and key.isalnum()) or key in _NAMED


def parse(text: str):
    """Return (mods, key) or raise ValueError. Needs at least one modifier and one key."""
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    mods, keys = set(), []
    for p in parts:
        p = _ALIASES.get(p, p)
        (mods.add if p in MODS else keys.append)(p)
    if not mods or len(keys) != 1 or not _valid_key(keys[0]):
        raise ValueError(f"not a valid shortcut: {text!r}")
    return frozenset(mods), keys[0]


def normalize(text: str) -> str:
    mods, key = parse(text)
    return "+".join([m for m in MODS if m in mods] + [key])


def display(text: str, mac: bool = IS_MAC) -> str:
    mods, key = parse(text)
    ordered = [m for m in MODS if m in mods]
    key = key.upper() if len(key) == 1 or key.startswith("f") else key.capitalize()
    if mac:
        return "".join(_MAC_SYMBOLS[m] for m in ordered) + key
    return "+".join([_WIN_NAMES[m] for m in ordered] + [key])


def is_modifier(keysym: str) -> bool:
    return keysym in _TK_MODS


def from_tk(held_keysyms, keysym: str):
    """Build a hotkey string from held modifier keysyms + the pressed key, or None."""
    mods = {_TK_MODS[k] for k in held_keysyms if k in _TK_MODS}
    key = keysym.lower()
    if not mods or not _valid_key(key):
        return None
    return normalize("+".join(sorted(mods) + [key]))
