import re
import requests
import time
from datetime import datetime, timedelta, timezone
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, TPOS, COMM, APIC, TRCK
import os
import glob

RETRY_INTERVAL_MINUTES = 20
MAX_RETRIES = 12  # up to 4 hours

# Base URL for the audio files
base_url = "https://dgk8fnvzp75ey.cloudfront.net/KNHC_"
# Push The Tempo airs Friday night, files available Saturday UTC
time_slots = ["T05", "T06"]

# Starting date (DST-proof: use UTC)
current_date = datetime.now(timezone.utc).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)

# If today is not Saturday, roll back to last Saturday
if current_date.weekday() != 5:
    current_date -= timedelta(days=(current_date.weekday() + 2) % 7)

days_to_download = 1
target_dir = "/DATA/Media/Music/C895/c895_push_the_tempo"
os.makedirs(target_dir, exist_ok=True)


def download_file(url, filename):
    """Download a file. Returns True on success."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
            return True
        else:
            print(f"File not available: {os.path.basename(filename)} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"Error downloading {os.path.basename(filename)}: {e}")
        return False


def download_slots_with_retry(date_str, slots):
    """Download all slots, retrying missing ones every RETRY_INTERVAL_MINUTES."""
    downloaded = []
    missing_slots = []

    for time_slot in slots:
        filename = f"KNHC_{date_str}{time_slot}.m4a"
        if os.path.exists(filename):
            print(f"{filename} already exists, skipping download")
            downloaded.append(filename)
            continue
        file_url = f"{base_url}{date_str}{time_slot}.m4a"
        if download_file(file_url, filename):
            downloaded.append(filename)
        else:
            missing_slots.append((time_slot, file_url, filename))

    if not missing_slots:
        return downloaded

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n⏳ {len(missing_slots)} slot(s) not posted yet for {date_str}:")
        for time_slot, _, fname in missing_slots:
            print(f"   - {os.path.basename(fname)}")
        print(f"   The show has not fully posted yet — please come back in {RETRY_INTERVAL_MINUTES} minutes.")
        print(f"   Retrying automatically... (attempt {attempt}/{MAX_RETRIES})")
        print(f"💤 Sleeping {RETRY_INTERVAL_MINUTES} minutes...")
        time.sleep(RETRY_INTERVAL_MINUTES * 60)

        still_missing = []
        for time_slot, file_url, filename in missing_slots:
            if os.path.exists(filename):
                downloaded.append(filename)
                continue
            if download_file(file_url, filename):
                downloaded.append(filename)
            else:
                still_missing.append((time_slot, file_url, filename))

        missing_slots = still_missing
        if not missing_slots:
            print("\n✅ All slots now downloaded!")
            break
    else:
        print(f"\n⚠️  Giving up after {MAX_RETRIES} retries. Still missing:")
        for time_slot, _, fname in missing_slots:
            print(f"   - {os.path.basename(fname)}")
        print("   The show may not have fully posted yet. Try again later.")

    return downloaded


def create_appealing_title(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)
        month_name = date_obj.strftime('%B')
        day_num = date_obj.strftime('%d').lstrip('0')
        year = date_obj.strftime('%Y')
        return f'Push The Tempo • {month_name} {day_num}, {year}'
    except Exception:
        return f'Push The Tempo • {date_str}'


def add_metadata(mp3_file_path, date_str, track_number=None):
    try:
        audio_file = MP3(mp3_file_path, ID3=ID3)
        if audio_file.tags is None:
            audio_file.add_tags()
        audio_file.tags.clear()

        appealing_title = create_appealing_title(date_str)
        audio_file.tags.add(TIT2(encoding=3, text=appealing_title))
        audio_file.tags.add(TPE1(encoding=3, text="C895 Radio"))
        audio_file.tags.add(TPE2(encoding=3, text="C895 Radio"))
        audio_file.tags.add(TALB(encoding=3, text="Push The Tempo"))
        audio_file.tags.add(TDRC(encoding=3, text=date_str))
        audio_file.tags.add(TCON(encoding=3, text="Electronic"))
        audio_file.tags.add(TPOS(encoding=3, text="1/1"))
        if track_number is not None:
            audio_file.tags.add(TRCK(encoding=3, text=str(track_number)))
        audio_file.tags.add(COMM(encoding=3, lang='eng', desc='desc',
            text=f"Push The Tempo radio show recorded from C895 Radio on {date_str}."))

        album_art_path = os.path.join(os.path.dirname(__file__), "c895_push_the_tempo.png")
        if not os.path.exists(album_art_path):
            album_art_path = os.path.join(os.path.dirname(__file__), "c895.png")
        if os.path.exists(album_art_path):
            with open(album_art_path, 'rb') as album_art:
                audio_file.tags.add(APIC(
                    encoding=3, mime='image/png', type=3,
                    desc='Album cover', data=album_art.read()
                ))
            print(f"Added album art from {album_art_path}")

        audio_file.save(v2_version=3)
        print(f"Added metadata to {mp3_file_path}")
        print(f"Title: {appealing_title}")
        if track_number is not None:
            print(f"Track Number: {track_number}")
    except Exception as e:
        print(f"Error adding metadata to {mp3_file_path}: {e}")


def update_track_numbers():
    print("\nUpdating track numbers for existing files...")
    pattern = os.path.join(target_dir, "C895_Push_The_Tempo_KNHC_*.mp3")
    existing_files = glob.glob(pattern)
    if not existing_files:
        print("No existing files found to update")
        return
    existing_files.sort(
        key=lambda x: re.search(r"KNHC_(\d{4}-\d{2}-\d{2})", x).group(1),
        reverse=True
    )
    print(f"Found {len(existing_files)} existing files. Updating track numbers...")
    for track_num, file_path in enumerate(existing_files):
        try:
            audio_file = MP3(file_path, ID3=ID3)
            if audio_file.tags is None:
                audio_file.add_tags()
            if 'TRCK' in audio_file.tags:
                del audio_file.tags['TRCK']
            audio_file.tags.add(TRCK(encoding=3, text=str(track_num)))
            audio_file.save(v2_version=3)
            print(f"Updated track number {track_num} for: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error updating track number for {file_path}: {e}")
    print("Track number update completed!")
    print("Most recent file: Track 0")
    print("Older files: Track 1, 2, 3, etc.")


# ── Main ──────────────────────────────────────────────────────────────────────

newly_created_files = []

for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")

    # Download with retry for missing slots
    download_slots_with_retry(date_str, time_slots)

    output_filename = os.path.join(target_dir, f"C895_Push_The_Tempo_KNHC_{date_str}.mp3")
    if not os.path.exists(output_filename):
        combined = AudioSegment.empty()
        any_added = False
        for time_slot in time_slots:
            filename = f"KNHC_{date_str}{time_slot}.m4a"
            if os.path.exists(filename):
                audio = AudioSegment.from_file(filename, format="m4a")
                combined += audio
                any_added = True

        if any_added and combined.duration_seconds > 0:
            combined.export(output_filename, format="mp3", bitrate="192k")
            print(f"Combined file {output_filename} created")
            newly_created_files.append((output_filename, date_str))
            add_metadata(output_filename, date_str)
        else:
            print(f"No audio segments available to combine for {date_str}, skipping.")
    else:
        print(f"{output_filename} already exists, skipping combination")

# Cleanup raw .m4a files
for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")
    for time_slot in time_slots:
        filename = f"KNHC_{date_str}{time_slot}.m4a"
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Removed {filename}")

if newly_created_files:
    print(f"\nNew files created: {len(newly_created_files)}")
    update_track_numbers()
else:
    print("\nNo new files were created during this run.")
    update_track_numbers()
