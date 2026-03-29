import re
import requests
import subprocess
import time
from datetime import datetime, timedelta, timezone
import concurrent.futures
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, TPOS, COMM, APIC, TRCK
import os
import glob
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    DownloadColumn, TransferSpeedColumn, TimeRemainingColumn,
    TimeElapsedColumn, TaskProgressColumn,
)

console = Console()

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
    for line in proc.stdout:
        if line.startswith("out_time="):
            try:
                h, m, s = line.split("=", 1)[1].strip().split(":")
                progress.update(task_id, completed=int(h) * 3600 + int(m) * 60 + float(s))
            except Exception:
                pass
    stderr_out = proc.stderr.read()
    proc.wait()
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
                audio.tags.add(APIC(encoding=3, mime="image/png", type=3,
                                    desc="Cover", data=img.read()))

        audio.save(v2_version=3)
        print(f"Metadata added to {mp3_file_path}")
    except Exception as e:
        print(f"Metadata error: {e}")


def update_track_numbers():
    """Newest file = track 0."""
    files = glob.glob(os.path.join(TARGET_DIR, "C895_Powermix_KNHC_*.mp3"))
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
    if downloaded_files:
        console.print(f"\n[bold]Encoding[/bold] {len(downloaded_files)} file(s) → [cyan]{os.path.basename(output_mp3)}[/cyan]")
        success = combine_with_ffmpeg(
            downloaded_files, "/tmp/powermix_concat.txt",
            output_mp3, f"Encoding Powermix {target_date}",
        )
        if success:
            console.print(f"  [green]✔[/green] Created [bold]{os.path.basename(output_mp3)}[/bold]")
            add_metadata(output_mp3, target_date)
        else:
            console.print(f"  [red]✖[/red] ffmpeg encoding failed")
    else:
        console.print("[yellow]⚠[/yellow]  No audio to combine, skipping.")
else:
    console.print(f"  [cyan]✔[/cyan] {os.path.basename(output_mp3)} already exists")

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
