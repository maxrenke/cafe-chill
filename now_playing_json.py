#!/usr/bin/env python3
"""Write the live C89.5 now-playing track to a JSON sidecar for the web app.

Polls Spinitron (via fetch_now_playing) and writes
/DATA/Media/Music/C895/now_playing.json, which the lofi-radio app fetches
while the C89.5 live stream is playing. On a transient failure it leaves the
existing file in place (so the UI keeps the last known track).
"""
import json
import os
import subprocess
import sys
import time

from spinitron_tracklist import fetch_now_playing

OUT = "/DATA/Media/Music/C895/now_playing.json"
CONTAINER = "lofi-radio-app"


def recently_requested(window=75):
    """True if the web app polled now_playing.json in the last `window` seconds.

    The app only polls while the live stream is actively playing, so this lets
    us scrape Spinitron on demand instead of 24/7. Fails open (scrape) if the
    container log can't be read.
    """
    try:
        out = subprocess.run(
            ["docker", "logs", "--since", f"{window}s", CONTAINER],
            capture_output=True, text=True, timeout=10,
        )
        return "now_playing.json" in (out.stdout + out.stderr)
    except Exception:
        return True


def main():
    # With --if-requested, skip the scrape unless the app is actively polling.
    if "--if-requested" in sys.argv and not recently_requested():
        return
    try:
        result = fetch_now_playing()
    except Exception:
        result = None
    if not result:
        return  # keep the last good file
    time_text, artist, title, release = result
    text = " - ".join(p for p in (artist, title) if p)
    payload = {
        "artist": artist or "",
        "title": title or "",
        "release": release or "",
        "time": time_text or "",
        "text": text,
        "updated": int(time.time()),
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, OUT)  # atomic


if __name__ == "__main__":
    main()
