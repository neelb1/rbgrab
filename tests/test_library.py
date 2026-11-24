import xml.etree.ElementTree as ET

from rbgrab import library


def _song(tmp_path, name="Daft Punk - One More Time (Radio Edit).m4a"):
    f = tmp_path / name
    f.write_bytes(b"x" * 10)
    return f


def test_creates_xml_with_track_and_playlist(tmp_path):
    xml = tmp_path / "rekordbox.xml"
    song = _song(tmp_path)
    assert library.add_track(xml, "Live Grabs", song, "Daft Punk", "One More Time", 320, "abc123")
    root = ET.parse(xml).getroot()
    track = root.find("COLLECTION/TRACK")
    assert track.get("Name") == "One More Time"
    assert track.get("Kind") == "M4A File"
    assert track.get("Size") == "10"
    assert root.find("COLLECTION").get("Entries") == "1"
    node = root.find("PLAYLISTS/NODE/NODE[@Name='Live Grabs']")
    assert node.find("TRACK").get("Key") == track.get("TrackID")


def test_location_is_percent_encoded_file_url(tmp_path):
    url = library.location_url(_song(tmp_path))
    assert url.startswith("file://localhost/")
    assert "%20" in url and "(Radio%20Edit)" in url
    assert " " not in url


def test_location_handles_windows_and_posix_style(tmp_path):
    url = library.location_url(_song(tmp_path))
    path = library._path_from(url)
    assert path.replace("\\", "/").endswith("Daft Punk - One More Time (Radio Edit).m4a")


def test_duplicates_are_skipped_and_found_by_video_id(tmp_path):
    xml = tmp_path / "rekordbox.xml"
    song = _song(tmp_path)
    assert library.add_track(xml, "rbgrab", song, "A", "B", 1, "vid1")
    assert not library.add_track(xml, "rbgrab", song, "A", "B", 1, "vid1")
    assert library.find_video(xml, "vid1") == "A - B"
    assert library.find_video(xml, "other") is None


def test_deleted_file_is_not_reported_as_duplicate(tmp_path):
    xml = tmp_path / "rekordbox.xml"
    song = _song(tmp_path)
    library.add_track(xml, "rbgrab", song, "A", "B", 1, "vid1")
    song.unlink()
    assert library.find_video(xml, "vid1") is None


def test_appends_to_existing_xml_and_new_playlist(tmp_path):
    xml = tmp_path / "rekordbox.xml"
    library.add_track(xml, "Old", _song(tmp_path, "a.mp3"), "A", "a")
    library.add_track(xml, "New", _song(tmp_path, "b.mp3"), "B", "b")
    root = ET.parse(xml).getroot()
    ids = [t.get("TrackID") for t in root.findall("COLLECTION/TRACK")]
    assert ids == ["1", "2"]
    assert root.find("PLAYLISTS/NODE").get("Count") == "2"
    assert root.find("PLAYLISTS/NODE/NODE[@Name='New']/TRACK").get("Key") == "2"
