# 🎵 Cafe Chill Downloader

A collection of Python scripts and utilities that automatically download and combine C89.5's "Cafe Chill" show segments into a single MP3 file for offline listening.

## 📋 Table of Contents
- [What It Does](#-what-it-does)
- [Why I Created This](#-why-i-created-this)
- [Getting Started](#-getting-started)
- [Running the Scripts](#running-the-scripts)
- [Script Details](#-script-details)
- [Output](#-output)
- [Acknowledgments](#-acknowledgments)

## ✨ What It Does

This script:
- Downloads the latest "Cafe Chill" show segments from C89.5 (KNHC)
- Automatically handles daylight saving time adjustments
- Combines multiple audio segments into one seamless MP3 file
- Adds rich metadata with appealing, day-specific titles
- Embeds album art for a complete music library experience
- Exports high-quality 192k bitrate MP3 files
- Saves the final file to your Downloads folder (or specified directory)
- Cleans up temporary files after processing

## 🎧 Why I Created This

I developed this script because I absolutely love listening to [C89.5](https://www.c895.org) - it's the perfect station to relax and jam out to! The "Cafe Chill" show has the most amazing vibes, and I wanted a way to download and enjoy these sessions offline whenever I need that perfect background music for coding, studying, or just chilling.

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- Required packages: `requests`, `pydub`, `mutagen`

### Installation

```bash
pip install requests pydub mutagen
```

### Running the Scripts

**Cafe Chill Main Script**
- **Python Execution**
```bash
python cafe_chill.py
```
- **Batch File (Windows)**
```bash
cafe_chill.bat
```
- **Direct Python Execution with Metadata on Server Version**
```bash
python cafe_chill_direct_server.py
```

**Additional Scripts**

- **cafe_chill_simple.sh** - A simplified bash script that downloads and saves directly. Requires permissions for `/DATA/Media/Music/C895`.
```bash
./cafe_chill_simple.sh
```

## 📁 Script Details

### cafe_chill.py & cafe_chill.bat
The main Windows version that saves files to your Downloads folder. Now includes:
- Rich metadata with day-specific appealing titles
- Embedded album art (`cafe_chill_album_art.jpg`)
- High-quality 192k bitrate MP3 output
- Better error handling for missing files

### cafe_chill_direct.py & cafe_chill_direct_server.py
Linux/Unix versions that save directly to `/DATA/Media/Music/C895` directory. Features:
- Same metadata and album art functionality as the Windows version
- Appealing titles based on the day of the week
- Higher quality 192k bitrate MP3 output
- Better error handling for missing files

### cafe_chill_simple.sh
A bash wrapper script that:
- Runs `cafe_chill_direct.py` on Linux/Unix systems
- Checks for write permissions
- Creates target directory if needed

## 📁 Output

The scripts create MP3 files with the format:
`C895_Cafe_Chill_KNHC_YYYY-MM-DD.mp3`

**File Locations:**
- Original script: `%USERPROFILE%\Downloads\`
- Direct versions: `/DATA/Media/Music/C895/`

## 🙏 Acknowledgments

- **Huge shoutout to [C89.5](https://www.c895.org)** for providing absolutely incredible music that makes every day better!
- Thanks to the amazing DJs and staff who curate these perfect chill vibes
- This project exists because C89.5's "Cafe Chill" is just *that* good 🎶

---

*Made with ❤️ for fellow C89.5 lovers who can't get enough of those chill vibes!*
