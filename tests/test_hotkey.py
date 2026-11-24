import pytest

from rbgrab import hotkey


def test_normalize_orders_and_aliases():
    assert hotkey.normalize("S + Alt + Control") == "ctrl+alt+s"
    assert hotkey.normalize("option+command+f5") == "alt+cmd+f5"


@pytest.mark.parametrize("bad", ["s", "ctrl+alt", "ctrl+s+d", "ctrl+é", "ctrl+enter", ""])
def test_rejects_invalid(bad):
    with pytest.raises(ValueError):
        hotkey.parse(bad)


def test_display_per_platform():
    assert hotkey.display("ctrl+alt+s", mac=False) == "Ctrl+Alt+S"
    assert hotkey.display("ctrl+alt+s", mac=True) == "⌃⌥S"
    assert hotkey.display("shift+cmd+space", mac=False) == "Shift+Win+Space"


def test_from_tk_events():
    assert hotkey.from_tk({"Control_L", "Alt_L"}, "s") == "ctrl+alt+s"
    assert hotkey.from_tk({"Meta_L", "Shift_R"}, "F2") == "shift+cmd+f2"
    assert hotkey.from_tk(set(), "s") is None
    assert hotkey.from_tk({"Control_L"}, "Return") is None
