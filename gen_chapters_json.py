#!/usr/bin/env python3
"""Write a sidecar `<show>/latest.chapters.json` for each show's latest.mp3,
extracted from the embedded ID3 chapters, so the lofi-radio web app can fetch
and display the tracklist (browsers don't expose ID3 chapters from <audio>).

Run after the latest.mp3 symlinks are updated. Idempotent.
"""
import json
import os
import subprocess

BASE = "/DATA/Media/Music/C895"
SHOWS = ["c895_cafe_chill", "c895_powermix", "c895_push_the_tempo"]


def read_chapters(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_chapters", "-print_format", "json", path],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout or "{}")
    ch = []
    for c in data.get("chapters", []):
        try:
            ch.append({
                "start": round(float(c["start_time"]), 3),
                "end": round(float(c["end_time"]), 3),
                "title": (c.get("tags", {}).get("title", "") or "").strip(),
            })
        except (KeyError, ValueError):
            pass
    ch.sort(key=lambda x: x["start"])
    return ch


def main():
    for show in SHOWS:
        mp3 = os.path.join(BASE, show, "latest.mp3")
        out = os.path.join(BASE, show, "latest.chapters.json")
        if not os.path.exists(mp3):
            continue
        chapters = read_chapters(mp3)
        if chapters:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(chapters, f, ensure_ascii=False)
            print(f"  {show}: {len(chapters)} chapters -> latest.chapters.json")
        else:
            if os.path.exists(out):
                os.remove(out)  # drop stale sidecar so the app shows none
            print(f"  {show}: no chapters")


if __name__ == "__main__":
    main()
