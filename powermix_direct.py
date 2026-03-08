import requests
from datetime import datetime, timedelta, timezone
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, TPOS, COMM, APIC, TRCK
import os
import glob

# -----------------------------
# CONFIGURATION
# -----------------------------

BASE_URL = "https://dgk8fnvzp75ey.cloudfront.net/KNHC_"
TIME_SLOTS = ["T05"]  # Powermix hour
TARGET_DIR = "/DATA/Media/Music/C895/c895_powermix"
os.makedirs(TARGET_DIR, exist_ok=True)

# -----------------------------
# UTILITIES
# -----------------------------

def download_file(url, filename):
    """Download a file from URL."""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
            return True
        else:
            print(f"Failed to download {filename} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False


def create_appealing_title(date_str):
    """Create a nice title using the FRIDAY date (show airs Friday night)."""
    try:
        utc_date = datetime.strptime(date_str, "%Y-%m-%d")
        friday_date = utc_date - timedelta(days=1)
        return f"Powermix • {friday_date.strftime('%B')} {friday_date.day}, {friday_date.year}"
    except:
        return f"Powermix • {date_str}"


def add_metadata(mp3_file_path, date_str, track_number=None):
    """Add ID3 metadata to MP3."""
    try:
        audio = MP3(mp3_file_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        audio.tags.clear()

        title = create_appealing_title(date_str)

        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text="C895 Radio"))
        audio.tags.add(TPE2(encoding=3, text="C895 Radio"))
        audio.tags.add(TALB(encoding=3, text="Powermix"))
        audio.tags.add(TDRC(encoding=3, text=date_str))
        audio.tags.add(TCON(encoding=3, text="Dance/Electronic"))
        audio.tags.add(TPOS(encoding=3, text="1/1"))

        if track_number is not None:
            audio.tags.add(TRCK(encoding=3, text=str(track_number)))

        # Album art
        art_path = os.path.join(os.path.dirname(__file__), "c895.png")
        if os.path.exists(art_path):
            with open(art_path, "rb") as img:
                audio.tags.add(APIC(
                    encoding=3,
                    mime="image/png",
                    type=3,
                    desc="Cover",
                    data=img.read()
                ))
            print("Added album art")

        audio.save()
        print(f"Metadata added to {mp3_file_path}")

    except Exception as e:
        print(f"Metadata error: {e}")


def update_track_numbers():
    """Newest file = track 0."""
    pattern = os.path.join(TARGET_DIR, "C895_Powermix_KNHC_*.mp3")
    files = glob.glob(pattern)

    if not files:
        print("No files to update.")
        return

    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    for i, fpath in enumerate(files):
        try:
            audio = MP3(fpath, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            if "TRCK" in audio.tags:
                del audio.tags["TRCK"]
            audio.tags.add(TRCK(encoding=3, text=str(i)))
            audio.save()
            print(f"Track {i} → {os.path.basename(fpath)}")
        except Exception as e:
            print(f"Track update error: {e}")


# -----------------------------
# DATE HANDLING (DST-PROOF)
# -----------------------------

# Powermix airs Friday night (local), but files are posted early Saturday UTC.
# So we ALWAYS want "yesterday in UTC".
utc_now = datetime.now(timezone.utc)
target_date = (utc_now - timedelta(days=1)).strftime("%Y-%m-%d")

print(f"Using UTC date: {target_date}")

# -----------------------------
# DOWNLOAD FILES
# -----------------------------

downloaded_files = []

for slot in TIME_SLOTS:
    url = f"{BASE_URL}{target_date}{slot}.m4a"
    fname = f"KNHC_{target_date}{slot}.m4a"

    if not os.path.exists(fname):
        if download_file(url, fname):
            downloaded_files.append(fname)
    else:
        print(f"{fname} already exists")


# -----------------------------
# COMBINE AUDIO
# -----------------------------

output_mp3 = os.path.join(TARGET_DIR, f"C895_Powermix_KNHC_{target_date}.mp3")

if not os.path.exists(output_mp3):
    combined = AudioSegment.empty()

    for fname in downloaded_files:
        audio = AudioSegment.from_file(fname, format="m4a")
        combined += audio

    if combined.duration_seconds > 0:
        combined.export(output_mp3, format="mp3", bitrate="192k")
        print(f"Created {output_mp3}")
        add_metadata(output_mp3, target_date)
else:
    print(f"{output_mp3} already exists")


# -----------------------------
# CLEANUP
# -----------------------------

for fname in downloaded_files:
    os.remove(fname)
    print(f"Removed {fname}")

# -----------------------------
# TRACK NUMBERING
# -----------------------------

update_track_numbers()
print("Done.")
