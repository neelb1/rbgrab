# Third-party software

rbgrab is MIT licensed. Its release builds include these libraries, unmodified:

| Library | License |
|---|---|
| [Python](https://www.python.org) and Tcl/Tk | PSF, Tcl/Tk |
| [Pillow](https://github.com/python-pillow/Pillow) | MIT-CMU |
| [pystray](https://github.com/moses-palmer/pystray) | LGPL-3.0 |
| [pynput](https://github.com/moses-palmer/pynput) (macOS) | LGPL-3.0 |
| [PyObjC](https://github.com/ronaldoussoren/pyobjc) (macOS) | MIT |
| [ytmusicapi](https://github.com/sigma67/ytmusicapi), [six](https://github.com/benjaminp/six), [charset-normalizer](https://github.com/jawah/charset_normalizer), [urllib3](https://github.com/urllib3/urllib3) | MIT |
| [requests](https://github.com/psf/requests) | Apache-2.0 |
| [idna](https://github.com/kjd/idna) | BSD-3-Clause |
| [certifi](https://github.com/certifi/python-certifi) | MPL-2.0 |
| [PyInstaller](https://pyinstaller.org) bootloader | GPL-2.0 with an exception allowing any license for built apps |

To use a modified LGPL library, install it and rebuild from source with `pyinstaller rbgrab.spec`.

yt-dlp and ffmpeg are **not** included. The install scripts download them from their own
projects, or use copies you already have.
