#!/usr/bin/env python3
"""Backfill synced chapters/tracklist onto each show's latest episode.

Run after update_c895.sh downloads (or skips) each show. Idempotent: skips
any file that already has embedded chapters, so it's cheap to run every
time. Exists mainly to cover files that were downloaded before Spinitron
had posted the playlist yet, or before this tracklist feature existed.
"""

import os
import re
from datetime import datetime, timedelta

from mutagen.id3 import ID3

from spinitron_tracklist import add_tracklist_to_show

BASE_DIR = "/DATA/Media/Music/C895"

SHOWS = {
    "Cafe Chill": dict(
        subdir="c895_cafe_chill", prefix="C895_Cafe_Chill_KNHC_",
        keyword="Cafe Chill", start_hour=6, duration_hours=4, air_date_offset=0,
    ),
    "Powermix": dict(
        subdir="c895_powermix", prefix="C895_Powermix_KNHC_",
        keyword="Powermix", start_hour=21, duration_hours=1, air_date_offset=-1,
    ),
    "Push The Tempo": dict(
        subdir="c895_push_the_tempo", prefix="C895_Push_The_Tempo_KNHC_",
        keyword="Push The Tempo", start_hour=22, duration_hours=2, air_date_offset=-1,
    ),
}


def has_chapters(mp3_path):
    try:
        return any(k.startswith("CHAP:") for k in ID3(mp3_path).keys())
    except Exception:
        return False


def newest_episode(show_dir, prefix):
    files = [f for f in os.listdir(show_dir) if f.startswith(prefix) and f.endswith(".mp3")]
    if not files:
        return None
    files.sort()
    return os.path.join(show_dir, files[-1])


def main():
    for show_name, cfg in SHOWS.items():
        show_dir = os.path.join(BASE_DIR, cfg["subdir"])
        if not os.path.isdir(show_dir):
            print(f"{show_name}: directory not found, skipping")
            continue

        mp3_path = newest_episode(show_dir, cfg["prefix"])
        if not mp3_path:
            print(f"{show_name}: no episodes found")
            continue

        match = re.search(r"KNHC_(\d{4}-\d{2}-\d{2})\.mp3$", mp3_path)
        if not match:
            continue

        if has_chapters(mp3_path):
            print(f"{show_name}: {os.path.basename(mp3_path)} already has chapters")
            continue

        file_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        air_date = file_date + timedelta(days=cfg["air_date_offset"])
        print(f"{show_name}: embedding tracklist into {os.path.basename(mp3_path)} (air date {air_date})")
        add_tracklist_to_show(
            mp3_path, cfg["keyword"], air_date,
            start_hour=cfg["start_hour"], duration_hours=cfg["duration_hours"],
        )


if __name__ == "__main__":
    main()
