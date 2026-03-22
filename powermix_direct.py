import re
import requests
import time
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
TIME_SLOTS = ["T04"]  # Powermix hour
TARGET_DIR = "/DATA/Media/Music/C895/c895_powermix"
os.makedirs(TARGET_DIR, exist_ok=True)

RETRY_INTERVAL_MINUTES = 20
MAX_RETRIES = 12  # up to 4 hours

# -----------------------------
# UTILITIES
# -----------------------------

def download_file(url, filename):
    """Download a file from URL. Returns True on success."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
            return True
        else:
            print(f"File not available: {os.path.basename(filename)} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False


def download_slots_with_retry(date_str, time_slots):
    """Download all slots, retrying missing ones every RETRY_INTERVAL_MINUTES."""
    downloaded = []
    missing_slots = []

    for slot in time_slots:
        fname = f"KNHC_{date_str}{slot}.m4a"
        if os.path.exists(fname):
            print(f"{fname} already exists")
            downloaded.append(fname)
            continue
        url = f"{BASE_URL}{date_str}{slot}.m4a"
        if download_file(url, fname):
            downloaded.append(fname)
        else:
            missing_slots.append((slot, url, fname))

    if not missing_slots:
        return downloaded

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n⏳ {len(missing_slots)} slot(s) not posted yet for {date_str}:")
        for slot, _, fname in missing_slots:
            print(f"   - {os.path.basename(fname)}")
        print(f"   The show has not fully posted yet — please come back in {RETRY_INTERVAL_MINUTES} minutes.")
        print(f"   Retrying automatically... (attempt {attempt}/{MAX_RETRIES})")
        print(f"💤 Sleeping {RETRY_INTERVAL_MINUTES} minutes...")
        time.sleep(RETRY_INTERVAL_MINUTES * 60)

        still_missing = []
        for slot, url, fname in missing_slots:
            if os.path.exists(fname):
                downloaded.append(fname)
                continue
            if download_file(url, fname):
                downloaded.append(fname)
            else:
                still_missing.append((slot, url, fname))

        missing_slots = still_missing
        if not missing_slots:
            print("\n✅ All slots now downloaded!")
            break
    else:
        print(f"\n⚠️  Giving up after {MAX_RETRIES} retries. Still missing:")
        for slot, _, fname in missing_slots:
            print(f"   - {os.path.basename(fname)}")
        print("   The show may not have fully posted yet. Try again later.")

    return downloaded


def create_appealing_title(date_str):
    """Create a nice title using the FRIDAY date (show airs Friday night)."""
    try:
        utc_date = datetime.strptime(date_str, "%Y-%m-%d")
        friday_date = utc_date - timedelta(days=1)
        return f"Powermix • {friday_date.strftime('%B')} {friday_date.day}, {friday_date.year}"
    except Exception:
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

        art_path = os.path.join(os.path.dirname(__file__), "c895_powermix.png")
        if not os.path.exists(art_path):
            art_path = os.path.join(os.path.dirname(__file__), "c895.png")
        if os.path.exists(art_path):
            with open(art_path, "rb") as img:
                audio.tags.add(APIC(
                    encoding=3, mime="image/png", type=3,
                    desc="Cover", data=img.read()
                ))
            print("Added album art")

        audio.save(v2_version=3)
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
    files.sort(key=lambda x: re.search(r"KNHC_(\d{4}-\d{2}-\d{2})", x).group(1), reverse=True)
    for i, fpath in enumerate(files):
        try:
            audio = MP3(fpath, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            if "TRCK" in audio.tags:
                del audio.tags["TRCK"]
            audio.tags.add(TRCK(encoding=3, text=str(i)))
            audio.save(v2_version=3)
            print(f"Track {i} → {os.path.basename(fpath)}")
        except Exception as e:
            print(f"Track update error: {e}")


# -----------------------------
# DATE HANDLING (DST-PROOF)
# -----------------------------

# Powermix airs Friday night (local), files are posted Saturday UTC.
utc_now = datetime.now(timezone.utc)
days_since_saturday = (utc_now.weekday() - 5) % 7  # Monday=0, Saturday=5
last_saturday = utc_now - timedelta(days=days_since_saturday)
target_date = last_saturday.strftime("%Y-%m-%d")
print(f"Using UTC date: {target_date}")

# -----------------------------
# DOWNLOAD FILES (with retry)
# -----------------------------

downloaded_files = download_slots_with_retry(target_date, TIME_SLOTS)

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
        print("No audio to combine, skipping.")
else:
    print(f"{output_mp3} already exists")

# -----------------------------
# CLEANUP
# -----------------------------

for fname in downloaded_files:
    if os.path.exists(fname):
        os.remove(fname)
        print(f"Removed {fname}")

# -----------------------------
# TRACK NUMBERING
# -----------------------------

update_track_numbers()
print("Done.")
