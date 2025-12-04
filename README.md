# C895 On Demand Downloaders

A collection of Python scripts that automatically download and combine C89.5's on demand shows into a single MP3 file for offline listening.

## 📋 Table of Contents
- [What It Does](#-what-it-does)
- [Getting Started](#-getting-started)
- [Running the Scripts](#running-the-scripts)
- [Script Details](#-script-details)
- [How to Create a Script for a New Show](#-how-to-create-a-script-for-a-new-show)
- [Output](#-output)
- [Acknowledgments](#-acknowledgments)

## ✨ What It Does

This script:
- Downloads the latest show segments from C89.5 (KNHC)
- Automatically handles daylight saving time adjustments
- Combines multiple audio segments into one seamless MP3 file
- Adds rich metadata with appealing, day-specific titles
- Embeds album art for a complete music library experience
- Exports high-quality 192k bitrate MP3 files
- Saves the final file to a specified directory
- Cleans up temporary files after processing

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- Required packages: `requests`, `pydub`, `mutagen`

### Installation

```bash
pip install requests pydub mutagen
```

## Running the Scripts

### Cafe Chill
```bash
python cafe_chill_direct.py
./cafe_chill_simple.sh
```

### Powermix
```bash
python powermix_direct.py
./powermix_simple.sh
```

### Push the Tempo
```bash
python push_the_tempo_direct.py
./push_the_tempo_simple.sh
```

### Server
```bash
python cafe_chill_direct_server.py
```

### Update
```bash
./update_c895.sh
```

## 📁 Script Details

All `_direct.py` scripts are designed to be run on a Linux/Unix system and save files to a specific directory. The `_simple.sh` scripts are bash wrappers that run the corresponding python script.

### Cafe Chill
- **Show:** Cafe Chill
- **Genre:** Chill/Lounge
- **Schedule:** Sunday
- **Output Directory:** `/DATA/Media/Music/C895/c895_cafe_chill`

### Powermix
- **Show:** Powermix
- **Genre:** Dance/Electronic
- **Schedule:** Friday Night (files available Saturday UTC)
- **Output Directory:** `/DATA/Media/Music/C895/c895_powermix`

### Push the Tempo
- **Show:** Push the Tempo
- **Genre:** Dance/Electronic
- **Schedule:** Saturday Night (files available Sunday UTC)
- **Output Directory:** `/DATA/Media/Music/C895/c895_push_the_tempo`

### Cafe Chill Server
- **`cafe_chill_direct_server.py`**: A python script that runs a web server to serve the latest Cafe Chill episode.

### Update Script
- **`update_c895.sh`**: A shell script to update the album art for the shows.

## How to Create a Script for a New Show

To create a downloader for a new show, you can copy one of the existing `_direct.py` scripts and modify it. Here are the key variables and functions you'll need to change, based on the differences between `cafe_chill_direct.py` and `powermix_direct.py`:

1.  **`create_appealing_title(date_str)` function:**
    *   Update the logic to create a title specific to the new show. For example, in `powermix_direct.py`, it's simply `f'Powermix • {month_name} {day_num}, {year}'`.

2.  **`add_metadata(mp3_file_path, date_str, track_number=None)` function:**
    *   **`TALB` (Album):** Change the album name to the name of the show.
    *   **`TCON` (Genre):** Update the genre.
    *   **`COMM` (Comment):** Update the comment to describe the new show.

3.  **`update_track_numbers()` function:**
    *   Update the `pattern` variable to match the new output filename.

4.  **`time_slots` variable:**
    *   This is the most important part. You need to find the correct time slots for the show you want to download. You can do this by inspecting the network requests on the C89.5 website when you play the on-demand show. The files are usually in the format `https://dgk8fnvzp75ey.cloudfront.net/KNHC_YYYY-MM-DDTHH.m4a`. The `HH` is the hour in UTC. The `time_slots` variable should be a list of strings, where each string is `T` followed by the hour. For example, if the files are `...T14.m4a`, `...T15.m4a`, etc., then `time_slots` would be `["T14", "T15", "T16", "T17"]`.

5.  **Date Logic:**
    *   You'll need to adjust the logic that determines which date to download. Find the day of the week the show airs and adjust the `current_date` variable accordingly. For example, Cafe Chill is on Sunday, so the script checks if the current day is Sunday and adjusts if it's not. Powermix is on Friday night, but the files are available on Saturday morning UTC, so the script looks for the last Saturday.

6.  **`target_dir` variable:**
    *   Change this to the directory where you want to save the downloaded files.

7.  **Output Filename:**
    *   In the second to last loop, update the `output_filename` to reflect the new show name.

## 📁 Output

The scripts create MP3 files with the format:
`C895_[ShowName]_KNHC_YYYY-MM-DD.mp3`

**File Locations:**
- Direct versions: `/DATA/Media/Music/C895/`

## 🙏 Acknowledgments

- **Huge shoutout to [C89.5](https://www.c895.org)** for providing absolutely incredible music!
- Thanks to the amazing DJs and staff who curate these shows.

---

*Made with ❤️ for fellow C89.5 lovers!*