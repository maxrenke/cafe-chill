#!/usr/bin/env python3
"""
Sync Navidrome albums/playlists to Z:\_Playlists M3U files.
Runs on CasaOS; writes to /DATA/Media/Music/_Playlists/
which Spotify sees as Z:\_Playlists via SMB.
"""

import requests
from pathlib import Path

NAVIDROME_URL = "http://localhost:4533"
ND_USER = "admin"
ND_PASS = "gT8*tbQa"

PLAYLIST_DIR = Path("/DATA/Media/Music/_Playlists")
WINDOWS_MUSIC_ROOT = "Z:\\"
SKIP_ALBUMS = {"[Unknown Album]", "NA"}


def nd_login():
    resp = requests.post(f"{NAVIDROME_URL}/auth/login",
                         json={"username": ND_USER, "password": ND_PASS})
    resp.raise_for_status()
    return resp.json()["token"]


def nd_get_all_song_paths(token):
    headers = {"X-ND-Authorization": f"Bearer {token}"}
    paths = {}
    start = 0
    batch = 500
    while True:
        resp = requests.get(f"{NAVIDROME_URL}/api/song", headers=headers,
                            params={"_start": start, "_end": start + batch})
        resp.raise_for_status()
        songs = resp.json()
        if not songs:
            break
        for s in songs:
            paths[s["id"]] = s["path"]
        start += batch
        if len(songs) < batch:
            break
    return paths


def nd_request(endpoint, **params):
    resp = requests.get(f"{NAVIDROME_URL}/rest/{endpoint}", params={
        "u": ND_USER, "p": ND_PASS, "v": "1.16.1",
        "c": "nd-spotify-sync", "f": "json", **params
    })
    resp.raise_for_status()
    return resp.json()["subsonic-response"]


def get_nd_albums():
    return nd_request("getAlbumList2", type="alphabeticalByName",
                      size=500)["albumList2"].get("album", [])


def get_nd_album_tracks(album_id):
    return nd_request("getAlbum", id=album_id)["album"].get("song", [])


def get_nd_playlists():
    data = nd_request("getPlaylists").get("playlists", {})
    return data.get("playlist", []) if data else []


def get_nd_playlist_tracks(playlist_id):
    return nd_request("getPlaylist", id=playlist_id)["playlist"].get("entry", [])


def to_windows_path(relative_path):
    return WINDOWS_MUSIC_ROOT + relative_path.replace("/", "\\")


def safe_filename(name):
    for ch in '\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


def write_m3u(filename, tracks, song_paths):
    out = PLAYLIST_DIR / filename
    lines = ["#EXTM3U", ""]
    missing = 0
    for t in tracks:
        rel = song_paths.get(t["id"])
        if not rel:
            missing += 1
            continue
        display = f"{t.get('artist', '')} - {t['title']}" if t.get("artist") else t["title"]
        lines.append(f"#EXTINF:{int(t.get('duration', -1))},{display}")
        lines.append(to_windows_path(rel))
        lines.append("")
    out.write_bytes("\r\n".join(lines).encode("utf-8"))
    return len(tracks) - missing, missing


def sync():
    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching song paths...")
    token = nd_login()
    song_paths = nd_get_all_song_paths(token)
    print(f"  {len(song_paths)} songs indexed.")

    albums = [a for a in get_nd_albums() if a["name"] not in SKIP_ALBUMS]
    print(f"Writing {len(albums)} album playlists...")
    for album in albums:
        tracks = get_nd_album_tracks(album["id"])
        if not tracks:
            continue
        filename = safe_filename(f"{album['name']} - {album['artist']}.m3u")
        found, missing = write_m3u(filename, tracks, song_paths)
        suffix = f" ({missing} missing)" if missing else ""
        print(f"  {filename} ({found} tracks{suffix})")

    nd_playlists = get_nd_playlists()
    if nd_playlists:
        print("Writing Navidrome playlists...")
        for pl in nd_playlists:
            tracks = get_nd_playlist_tracks(pl["id"])
            if not tracks:
                continue
            filename = safe_filename(f"ND - {pl['name']}.m3u")
            found, missing = write_m3u(filename, tracks, song_paths)
            suffix = f" ({missing} missing)" if missing else ""
            print(f"  {filename} ({found} tracks{suffix})")

    print("Spotify playlists updated.")


if __name__ == "__main__":
    sync()
