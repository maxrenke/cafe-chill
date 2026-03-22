#!/usr/bin/env python3
"""
update_push_the_tempo_art.py

Downloads the latest Push The Tempo album art from c895.org and replaces
the APIC tag on every existing C895_Push_The_Tempo_KNHC_*.mp3 file.

Also saves art locally so future downloads use it.

Usage:
    python3 update_push_the_tempo_art.py
"""

import glob
import os
import sys
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

ART_URL = "https://www.c895.org/wp-content/uploads/2024/01/Push-The-Tempo-Logo-Impact-Prod-New-Logo-Jan-2024.png"
TARGET_DIR = "/DATA/Media/Music/C895/c895_push_the_tempo"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ART_PATH = os.path.join(SCRIPT_DIR, "c895_push_the_tempo.png")

print(f"Downloading album art from {ART_URL} ...")
try:
    resp = requests.get(ART_URL, timeout=30)
    resp.raise_for_status()
    art_data = resp.content
    mime = "image/png"
    print(f"  Downloaded {len(art_data):,} bytes  ({mime})")
except Exception as e:
    print(f"ERROR: Could not download art: {e}")
    sys.exit(1)

with open(LOCAL_ART_PATH, "wb") as f:
    f.write(art_data)
print(f"  Saved to {LOCAL_ART_PATH}")

pattern = os.path.join(TARGET_DIR, "C895_Push_The_Tempo_KNHC_*.mp3")
files = sorted(glob.glob(pattern))

if not files:
    print(f"\nNo files found matching {pattern}")
    sys.exit(0)

print(f"\nFound {len(files)} file(s) to update:")

ok = 0
errors = 0
for path in files:
    name = os.path.basename(path)
    try:
        audio = MP3(path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("APIC")
        audio.tags.add(APIC(
            encoding=3,
            mime=mime,
            type=3,
            desc="Album cover",
            data=art_data,
        ))
        audio.save(v2_version=3)
        print(f"  ✔  {name}")
        ok += 1
    except Exception as e:
        print(f"  ✖  {name}  — {e}")
        errors += 1

print(f"\nDone. {ok} updated, {errors} errors.")
