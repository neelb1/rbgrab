"""One grab: resolve a query or link to a song, download it, add it to the XML."""
import os

from . import config, download, library, search


def grab(cfg: dict, target, update=lambda state, pct, text: None, library_index=None):
    """target is a search result dict, a search query, or a link.

    update(state, pct, text) reports "search", "download", "done" or "dupe".
    library_index (optional) also skips songs already in your music folders.
    Returns (state, "Artist - Title").
    """
    if isinstance(target, str):
        if search.is_url(target):
            item = {"id": search.video_id(target), "url": target, "title": target, "artist": ""}
        else:
            update("search", 0, target)
            results = search.search(target, 1)
            if not results:
                raise LookupError(f'No songs found for "{target}"')
            item = results[0]
    else:
        item = target

    xml = config.xml_path(cfg)
    existing = library.find_video(xml, item.get("id"))
    owned = library_index.find(item.get("id")) if library_index and item.get("id") else None
    if existing or owned:
        name = existing or os.path.splitext(os.path.basename(owned))[0]
        update("dupe", 1, name)
        return "dupe", name

    name = search.label(item)
    update("download", 0, name)
    info = download.download(item.get("url") or download.video_url(item["id"]), cfg,
                             lambda pct: update("download", pct, name))
    library.add_track(xml, cfg["playlist"], info["path"], info["artist"], info["title"],
                      info["duration"], info["id"])
    if library_index and info["id"]:
        library_index.add(info["id"], info["path"])
    name = f"{info['artist']} - {info['title']}" if info["artist"] else info["title"]
    update("done", 1, name)
    return "done", name
