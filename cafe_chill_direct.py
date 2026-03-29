import re
import requests
import subprocess
import sys
import time
import threading
from datetime import datetime, timedelta, timezone
import concurrent.futures
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, TPOS, COMM, APIC, TRCK
import os
import glob
from zoneinfo import ZoneInfo
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    DownloadColumn, TransferSpeedColumn, TimeRemainingColumn,
    TimeElapsedColumn, TaskProgressColumn,
)

console = Console()

RETRY_INTERVAL_MINUTES = 20
MAX_RETRIES = 12  # up to 4 hours of retrying

# Starting date (DST-proof: use UTC)
current_date = datetime.now(timezone.utc).replace(
    tzinfo=None, hour=0, minute=0, second=0, microsecond=0
)

# If today is not Sunday, roll back to last Sunday
if current_date.weekday() != 6:
    current_date -= timedelta(days=(current_date.weekday() + 1) % 7)


def get_cafe_chill_timeslots(date_obj):
    """Returns the correct UTC T-codes for the 4 Café Chill hours, DST-aware."""
    pacific = ZoneInfo("America/Los_Angeles")
    utc = ZoneInfo("UTC")
    slots = []
    for hour in [6, 7, 8, 9]:  # Café Chill airs 6–10am Pacific
        local_dt = datetime(
            date_obj.year, date_obj.month, date_obj.day,
            hour, 0, 0, tzinfo=pacific
        )
        utc_dt = local_dt.astimezone(utc)
        slots.append(f"T{utc_dt.hour:02d}")
    return slots


def file_exists_on_server(url):
    """Check if a file exists on the CDN without downloading it."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def download_file(url, filename):
    """Download a file with a live progress bar. Returns True on success."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            total = int(response.headers.get('content-length', 0))
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                transient=True,
            ) as progress:
                task = progress.add_task(
                    os.path.basename(filename), total=total or None
                )
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
            console.print(f"  [green]✔[/green] [bold]{os.path.basename(filename)}[/bold]")
            return True
        else:
            console.print(f"  [yellow]✖[/yellow] Not available: [bold]{os.path.basename(filename)}[/bold] (HTTP {response.status_code})")
            return False
    except Exception as e:
        console.print(f"  [red]✖[/red] Error downloading [bold]{os.path.basename(filename)}[/bold]: {e}")
        return False


def download_all_slots_with_retry(date_str, time_slots):
    """
    Download all time slots. For any that are missing, retry every
    RETRY_INTERVAL_MINUTES until all are present or MAX_RETRIES exceeded.
    Returns list of successfully downloaded filenames.
    """
    base_url = "https://dgk8fnvzp75ey.cloudfront.net/KNHC_"
    downloaded = []
    missing_slots = []

    # First pass: download what's available, note what's missing
    for time_slot in time_slots:
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

    # Retry loop for missing slots
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n⏳ {len(missing_slots)} hour(s) not posted yet for {date_str}:")
        for time_slot, _, filename in missing_slots:
            print(f"   - {os.path.basename(filename)}")
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
            print("\n✅ All hours now downloaded!")
            break
    else:
        print(f"\n⚠️  Giving up after {MAX_RETRIES} retries. Still missing:")
        for time_slot, _, filename in missing_slots:
            print(f"   - {os.path.basename(filename)}")
        print("   The show may not have fully posted yet. Try again later.")

    return downloaded


def ffprobe_duration(filepath):
    """Return duration of an audio file in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _encode_one(m4a_file, mp3_file, duration, progress, task_id):
    """Encode one M4A → MP3, streaming progress updates."""
    cmd = [
        "ffmpeg", "-y", "-i", m4a_file,
        "-b:a", "128k",
        "-progress", "pipe:1", "-nostats",
        mp3_file,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stderr_buf = []
    stderr_thread = threading.Thread(target=lambda: stderr_buf.append(proc.stderr.read()))
    stderr_thread.start()
    for line in proc.stdout:
        if line.startswith("out_time="):
            try:
                h, m, s = line.split("=", 1)[1].strip().split(":")
                progress.update(task_id, completed=int(h) * 3600 + int(m) * 60 + float(s))
            except Exception:
                pass
    stderr_thread.join()
    proc.wait()
    stderr_out = stderr_buf[0] if stderr_buf else ""
    if proc.returncode != 0:
        return False, stderr_out
    return True, ""


def combine_with_ffmpeg(input_files, concat_list_path, output_file, label):
    """Encode each M4A → MP3 in parallel (max 2 at a time), then losslessly concatenate."""
    durations = [ffprobe_duration(f) for f in input_files]
    temp_mp3s = [f + ".tmp.mp3" for f in input_files]

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=True,
    ) as progress:
        task_ids = [
            progress.add_task(os.path.basename(f), total=dur)
            for f, dur in zip(input_files, durations)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, len(input_files))) as ex:
            futs = [
                ex.submit(_encode_one, m4a, mp3, dur, progress, tid)
                for m4a, mp3, dur, tid in zip(input_files, temp_mp3s, durations, task_ids)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futs)]

    ok = all(success for success, _ in results)
    if not ok:
        for success, stderr_out in results:
            if not success and stderr_out:
                console.print(f"  [red]ffmpeg error:[/red] {stderr_out[-500:]}")
        console.print("  [red]✖[/red] One or more encoding jobs failed")
        for tmp in temp_mp3s:
            if os.path.exists(tmp): os.remove(tmp)
        return False

    # Lossless MP3 concat (instant — no re-encode)
    with open(concat_list_path, "w") as f:
        for mp3 in temp_mp3s:
            f.write(f"file '{os.path.abspath(mp3)}'\n")
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", concat_list_path, "-c:a", "copy", output_file],
        capture_output=True, text=True,
    )
    os.remove(concat_list_path)
    for tmp in temp_mp3s:
        if os.path.exists(tmp): os.remove(tmp)
    if result.returncode != 0:
        console.print(f"  [red]ffmpeg concat error:[/red] {result.stderr[-500:]}")
    return result.returncode == 0


def create_appealing_title(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%A')
        month_name = date_obj.strftime('%B')
        day_num = date_obj.strftime('%d').lstrip('0')
        year = date_obj.strftime('%Y')
        titles = {
            'Sunday':    f'Sunday Serenity • Cafe Chill Mix • {month_name} {day_num}, {year}',
            'Monday':    f'Monday Morning Mellow • Cafe Chill Sessions • {month_name} {day_num}, {year}',
            'Tuesday':   f'Tranquil Tuesday • Cafe Chill Vibes • {month_name} {day_num}, {year}',
            'Wednesday': f'Midweek Mellow • Cafe Chill Sounds • {month_name} {day_num}, {year}',
            'Thursday':  f'Thursday Chill • Smooth Cafe Beats • {month_name} {day_num}, {year}',
            'Friday':    f'Friday Flow • Cafe Chill Wind-Down • {month_name} {day_num}, {year}',
            'Saturday':  f'Saturday Smooth • Weekend Cafe Chill • {month_name} {day_num}, {year}',
        }
        return titles.get(day_name, f'Cafe Chill • {day_name} Sessions • {month_name} {day_num}, {year}')
    except Exception:
        return f'Cafe Chill Sessions • {date_str}'


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
        audio_file.tags.add(TALB(encoding=3, text="Cafe Chill"))
        audio_file.tags.add(TDRC(encoding=3, text=date_str))
        audio_file.tags.add(TCON(encoding=3, text="Chill/Lounge"))
        audio_file.tags.add(TPOS(encoding=3, text="1/1"))
        if track_number is not None:
            audio_file.tags.add(TRCK(encoding=3, text=str(track_number)))
        audio_file.tags.add(COMM(encoding=3, lang='eng', desc='desc',
            text=f"Cafe Chill radio show recorded from C895 Radio on {date_str}. "
                 "A chill and relaxing music experience perfect for work, study, or unwinding."))

        album_art_path = os.path.join(os.path.dirname(__file__), "c895.png")
        if os.path.exists(album_art_path):
            with open(album_art_path, 'rb') as album_art:
                audio_file.tags.add(APIC(
                    encoding=3, mime='image/png', type=3,
                    desc='Album cover', data=album_art.read()
                ))

        audio_file.save(v2_version=3)
        print(f"Added metadata to {mp3_file_path}")
        print(f"Title: {appealing_title}")
        if track_number is not None:
            print(f"Track Number: {track_number}")
    except Exception as e:
        print(f"Error adding metadata to {mp3_file_path}: {e}")


def update_track_numbers():
    print("\nUpdating track numbers for existing files...")
    existing_files = glob.glob(os.path.join(target_dir, "C895_Cafe_Chill_KNHC_*.mp3"))
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


# ── Main ──────────────────────────────────────────────────────────────────────

time_slots = get_cafe_chill_timeslots(current_date)
print("Using time slots:", time_slots)

days_to_download = 1
target_dir = "/DATA/Media/Music/C895/c895_cafe_chill"
os.makedirs(target_dir, exist_ok=True)

newly_created_files = []

for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")

    # Download with retry logic for missing hours
    download_all_slots_with_retry(date_str, time_slots)

    # Combine downloaded audio files
    output_filename = os.path.join(target_dir, f"C895_Cafe_Chill_KNHC_{date_str}.mp3")
    if not os.path.exists(output_filename):
        input_files = []
        for time_slot in time_slots:
            filename = f"KNHC_{date_str}{time_slot}.m4a"
            if os.path.exists(filename):
                input_files.append(filename)

        if input_files:
            console.print(f"\n[bold]Encoding[/bold] {len(input_files)} hour(s) → [cyan]{os.path.basename(output_filename)}[/cyan]")
            success = combine_with_ffmpeg(
                input_files, "/tmp/cafe_chill_concat.txt",
                output_filename, f"Encoding Cafe Chill {date_str}",
            )
            if success:
                console.print(f"  [green]✔[/green] Created [bold]{os.path.basename(output_filename)}[/bold]")
                newly_created_files.append((output_filename, date_str))
                add_metadata(output_filename, date_str)
            else:
                console.print(f"  [red]✖[/red] ffmpeg encoding failed")
        else:
            console.print(f"  [yellow]⚠[/yellow]  No audio segments available for {date_str}, skipping.")
    else:
        print(f"{output_filename} already exists, skipping combination")

# Clean up raw .m4a files
for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")
    for time_slot in time_slots:
        filename = f"KNHC_{date_str}{time_slot}.m4a"
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Removed {filename}")

# Update track numbers
if newly_created_files:
    print(f"\nNew files created: {len(newly_created_files)}")
    update_track_numbers()
else:
    print("\nNo new files were created during this run.")
    update_track_numbers()
