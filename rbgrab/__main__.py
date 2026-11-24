"""Entry point.

rbgrab                 start the app (or show the search bar if it's already running)
rbgrab "artist song"   grab the top result without the UI
"""
import argparse
import logging
import os
import sys

from . import __version__, config


def main(argv=None):
    if sys.stdout is None:  # windowed builds have no console
        sys.stdout = sys.stderr = open(os.devnull, "w")
    parser = argparse.ArgumentParser(prog="rbgrab", description=__doc__.split("\n")[0])
    parser.add_argument("query", nargs="*", help="song to grab without opening the UI")
    parser.add_argument("--version", action="version", version=f"rbgrab {__version__}")
    args = parser.parse_args(argv)

    config.config_dir().mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=config.config_dir() / "rbgrab.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.query:
        from . import core
        from .libindex import LibraryIndex
        cfg = config.load()
        index = LibraryIndex()
        index.scan(config.library_folders(cfg))
        state, name = core.grab(cfg, " ".join(args.query),
                                lambda s, pct, text: s != "download" and print(f"{s}: {text}"), index)
        return 0

    from . import instance
    if instance.signal_running():
        return 0
    from .app import App
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
