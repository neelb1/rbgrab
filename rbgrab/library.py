"""The rekordbox XML file rbgrab appends to.

rekordbox reads it through Preferences > Advanced > Database > rekordbox xml.
New tracks appear after clicking refresh on the "rekordbox xml" node.
"""
import os
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

_lock = threading.Lock()
_SAFE = "/:()!,'&-_.~"
_TAG = "rbgrab:"  # stored in Comments so a song is never downloaded twice


def location_url(path) -> str:
    p = Path(path).resolve().as_posix()
    if not p.startswith("/"):
        p = "/" + p  # Windows drive paths: /D:/Music/...
    return "file://localhost" + urllib.parse.quote(p, safe=_SAFE)


def _load(xml_path) -> ET.ElementTree:
    if os.path.exists(xml_path):
        return ET.parse(xml_path)
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="7.0.0", Company="AlphaTheta")
    ET.SubElement(root, "COLLECTION", Entries="0")
    ET.SubElement(ET.SubElement(root, "PLAYLISTS"), "NODE", Type="0", Name="ROOT", Count="0")
    return ET.ElementTree(root)


def _playlist(root, name):
    top = root.find("PLAYLISTS/NODE")
    for node in top.findall("NODE"):
        if node.get("Name") == name:
            return node
    node = ET.SubElement(top, "NODE", Name=name, Type="1", KeyType="0", Entries="0")
    top.set("Count", str(len(top.findall("NODE"))))
    return node


def find_video(xml_path, video_id):
    """Return "Artist - Title" if this YouTube id is already in the library."""
    if not video_id or not os.path.exists(xml_path):
        return None
    with _lock:
        for t in _load(xml_path).getroot().iter("TRACK"):
            if t.get("Comments") == _TAG + video_id and os.path.exists(_path_from(t.get("Location", ""))):
                return f"{t.get('Artist')} - {t.get('Name')}"
    return None


def _path_from(location: str) -> str:
    p = urllib.parse.unquote(location.replace("file://localhost", "", 1))
    return p[1:] if len(p) > 2 and p[2] == ":" else p  # /D:/x -> D:/x


def add_track(xml_path, playlist, path, artist, title, duration=0, video_id=None) -> bool:
    """Add a track to the collection and playlist. False if it was already there."""
    with _lock:
        tree = _load(xml_path)
        root = tree.getroot()
        coll = root.find("COLLECTION")
        location = location_url(path)
        if any(t.get("Location") == location for t in coll.findall("TRACK")):
            return False
        track_id = str(max([int(t.get("TrackID")) for t in coll.findall("TRACK")] + [0]) + 1)
        attrs = dict(TrackID=track_id, Name=title, Artist=artist, Album="",
                     Kind=Path(path).suffix.lstrip(".").upper() + " File",
                     Size=str(os.path.getsize(path)), TotalTime=str(int(duration or 0)),
                     Location=location)
        if video_id:
            attrs["Comments"] = _TAG + video_id
        ET.SubElement(coll, "TRACK", **attrs)
        coll.set("Entries", str(len(coll.findall("TRACK"))))
        node = _playlist(root, playlist)
        ET.SubElement(node, "TRACK", Key=track_id)
        node.set("Entries", str(len(node.findall("TRACK"))))
        ET.indent(tree)
        os.makedirs(os.path.dirname(os.path.abspath(xml_path)), exist_ok=True)
        tmp = str(xml_path) + ".tmp"
        tree.write(tmp, encoding="UTF-8", xml_declaration=True)
        os.replace(tmp, xml_path)
        return True
