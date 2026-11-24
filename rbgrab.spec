# PyInstaller build: `pyinstaller rbgrab.spec` -> dist/rbgrab (Windows) or dist/rbgrab.app (macOS).
# Run `python -m rbgrab.icon assets/icon.png` first.
import importlib.metadata
import os
import sys

from PyInstaller.utils.hooks import collect_data_files

mac = sys.platform == "darwin"
hidden = (["pystray._darwin", "pynput.keyboard._darwin", "pynput.mouse._darwin"] if mac
          else ["pystray._win32"])

# License texts of the libraries inside the build, shipped in its "licenses" folder.
LIBS = ["pillow", "pystray", "six", "requests", "urllib3", "idna", "certifi",
        "charset-normalizer", "ytmusicapi"]
LIBS += ["pynput", "pyobjc-core"] if mac else []
licenses = []
for lib in LIBS:
    for f in importlib.metadata.files(lib) or []:
        if any(w in f.name.upper() for w in ("LICENSE", "COPYING", "NOTICE")) and "info" in str(f):
            licenses.append((str(f.locate()), f"licenses/{lib}"))
licenses.append(("THIRD_PARTY.md", "licenses"))
licenses.append(("LICENSE", "licenses"))
python_license = os.path.join(sys.base_prefix, "LICENSE.txt")
if os.path.exists(python_license):
    licenses.append((python_license, "licenses/python"))  # also covers Tcl/Tk and OpenSSL on Windows

a = Analysis(
    ["scripts/launch.py"],
    pathex=["."],
    datas=collect_data_files("ytmusicapi") + licenses,
    hiddenimports=hidden,
    # yt-dlp comes from the installer as a self-updating program; the rest are optional
    # extras that Pillow/requests pick up if present and that rbgrab never uses.
    excludes=["yt_dlp", "mutagen", "defusedxml", "socks", "numpy", "cryptography", "PIL.ImageQt", "PyQt5", "PyQt6", "PySide6"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="rbgrab", console=False,
          icon="assets/icon.png")
coll = COLLECT(exe, a.binaries, a.datas, name="rbgrab")
if mac:
    app = BUNDLE(coll, name="rbgrab.app", icon="assets/icon.png",
                 bundle_identifier="com.rbgrab.app",
                 info_plist={"LSUIElement": True,  # menu bar app, no Dock icon
                             "CFBundleShortVersionString": "0.1.0"})
