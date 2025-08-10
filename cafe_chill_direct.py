import requests
from datetime import datetime, timedelta
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, TPOS, COMM, APIC, TRCK
import os
import glob

# Function to download a file from a given URL and save it with the specified filename
def download_file(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {filename}")

# Function to create appealing title
def create_appealing_title(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%A')
        month_name = date_obj.strftime('%B')
        day_num = date_obj.strftime('%d').lstrip('0')
        year = date_obj.strftime('%Y')
        
        # Create different appealing titles based on the day
        titles = {
            'Sunday': f'Sunday Serenity • Cafe Chill Mix • {month_name} {day_num}, {year}',
            'Monday': f'Monday Morning Mellow • Cafe Chill Sessions • {month_name} {day_num}, {year}',
            'Tuesday': f'Tranquil Tuesday • Cafe Chill Vibes • {month_name} {day_num}, {year}',
            'Wednesday': f'Midweek Mellow • Cafe Chill Sounds • {month_name} {day_num}, {year}',
            'Thursday': f'Thursday Chill • Smooth Cafe Beats • {month_name} {day_num}, {year}',
            'Friday': f'Friday Flow • Cafe Chill Wind-Down • {month_name} {day_num}, {year}',
            'Saturday': f'Saturday Smooth • Weekend Cafe Chill • {month_name} {day_num}, {year}'
        }
        
        return titles.get(day_name, f'Cafe Chill • {day_name} Sessions • {month_name} {day_num}, {year}')
    except:
        return f'Cafe Chill Sessions • {date_str}'

# Function to add metadata to MP3 file
def add_metadata(mp3_file_path, date_str, track_number=None):
    try:
        # Load the MP3 file
        audio_file = MP3(mp3_file_path, ID3=ID3)
        
        # Add ID3 tag if it doesn't exist
        if audio_file.tags is None:
            audio_file.add_tags()
        
        # Clear existing tags to avoid conflicts
        audio_file.tags.clear()
        
        # Create appealing title
        appealing_title = create_appealing_title(date_str)
        
        # Set metadata
        audio_file.tags.add(TIT2(encoding=3, text=appealing_title))  # Title
        audio_file.tags.add(TPE1(encoding=3, text="C895 Radio"))  # Artist
        audio_file.tags.add(TPE2(encoding=3, text="C895 Radio"))  # Album Artist
        audio_file.tags.add(TALB(encoding=3, text="Cafe Chill"))  # Album
        audio_file.tags.add(TDRC(encoding=3, text=date_str))  # Date
        audio_file.tags.add(TCON(encoding=3, text="Chill/Lounge"))  # Genre
        audio_file.tags.add(TPOS(encoding=3, text="1/1"))  # Part of set
        
        # Add track number if provided
        if track_number is not None:
            audio_file.tags.add(TRCK(encoding=3, text=str(track_number)))  # Track number
        
        audio_file.tags.add(COMM(encoding=3, lang='eng', desc='desc', 
                                text=f"Cafe Chill radio show recorded from C895 Radio on {date_str}. A chill and relaxing music experience perfect for work, study, or unwinding."))  # Comment
        
        # Add album art if it exists
        album_art_path = os.path.join(os.path.dirname(__file__), "cafe_chill_album_art.jpg")
        if os.path.exists(album_art_path):
            with open(album_art_path, 'rb') as album_art:
                audio_file.tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,  # Cover (front)
                    desc=u'Album cover',
                    data=album_art.read()
                ))
            print(f"Added album art from {album_art_path}")
        
        # Save the changes
        audio_file.save()
        print(f"Added metadata to {mp3_file_path}")
        print(f"Title: {appealing_title}")
        if track_number is not None:
            print(f"Track Number: {track_number}")
        
    except Exception as e:
        print(f"Error adding metadata to {mp3_file_path}: {e}")

# Function to update track numbers for existing files
def update_track_numbers():
    """Update track numbers for all existing MP3 files in the target directory"""
    print("\nUpdating track numbers for existing files...")
    
    # Get all existing MP3 files in the target directory
    pattern = os.path.join(target_dir, "C895_Cafe_Chill_KNHC_*.mp3")
    existing_files = glob.glob(pattern)
    
    if not existing_files:
        print("No existing files found to update")
        return
    
    # Sort files by modification time (newest first)
    existing_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    print(f"Found {len(existing_files)} existing files. Updating track numbers...")
    
    # Update track numbers starting from 0 for the newest file
    for track_num, file_path in enumerate(existing_files):
        try:
            # Load the MP3 file
            audio_file = MP3(file_path, ID3=ID3)
            
            # Add ID3 tag if it doesn't exist
            if audio_file.tags is None:
                audio_file.add_tags()
            
            # Remove existing track number tag if it exists
            if 'TRCK' in audio_file.tags:
                del audio_file.tags['TRCK']
            
            # Add new track number
            audio_file.tags.add(TRCK(encoding=3, text=str(track_num)))
            audio_file.save()
            
            filename = os.path.basename(file_path)
            print(f"Updated track number {track_num} for: {filename}")
            
        except Exception as e:
            print(f"Error updating track number for {file_path}: {e}")
    
    print("Track number update completed!")
    print(f"Most recent file: Track 0")
    print(f"Older files: Track 1, 2, 3, etc.")

# Base URL for the audio files
base_url = "https://dgk8fnvzp75ey.cloudfront.net/KNHC_"
# Time slots for the audio files
# Adjust for daylight savings time if applicable
if datetime.today().timetuple().tm_isdst:
    time_slots = ["T13", "T14", "T15", "T16"]
else:
    time_slots = ["T14", "T15", "T16", "T17"]

# Starting date for downloading files
current_date = datetime.today().strftime("%Y-%m-%d")
current_date = datetime.strptime(current_date, "%Y-%m-%d")

# Check if today is Sunday, if not, set to the last Sunday
if datetime.today().weekday() != 6:
    current_date -= timedelta(days=(datetime.today().weekday() + 1) % 7)

# Number of days to download files for
days_to_download = 1

# Target directory for saving files
target_dir = "/DATA/Media/Music/C895"
os.makedirs(target_dir, exist_ok=True)

# Track newly created files for track numbering
newly_created_files = []

# Loop through each day to download files
for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")
    for time_slot in time_slots:
        file_url = f"{base_url}{date_str}{time_slot}.m4a"
        filename = f"KNHC_{date_str}{time_slot}.m4a"
        if not os.path.exists(filename):
            download_file(file_url, filename)
        else:
            print(f"{filename} already exists, skipping download")

# Loop through each day to combine downloaded audio files
for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")
    combined = AudioSegment.empty()
    output_filename = os.path.join(target_dir, f"C895_Cafe_Chill_KNHC_{date_str}.mp3")
    if not os.path.exists(output_filename):
        for time_slot in time_slots:
            filename = f"KNHC_{date_str}{time_slot}.m4a"
            if os.path.exists(filename):
                audio = AudioSegment.from_file(filename, format="m4a")
                combined += audio
        
        # Export with higher quality settings
        combined.export(output_filename, format="mp3", bitrate="192k")
        print(f"Combined file {output_filename} created")
        
        # Add to newly created files list
        newly_created_files.append((output_filename, date_str))
        
        # Add metadata to the combined MP3 file (track number will be added later)
        add_metadata(output_filename, date_str)
        
    else:
        print(f"{output_filename} already exists, skipping combination")

# Loop through each day to remove the original downloaded files
for day in range(days_to_download):
    date_str = (current_date - timedelta(days=day)).strftime("%Y-%m-%d")
    for time_slot in time_slots:
        filename = f"KNHC_{date_str}{time_slot}.m4a"
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Removed {filename}")

# Update track numbers for all files in the target directory
# This ensures proper track numbering based on file modification time (newest = 0)
if newly_created_files:
    print(f"\nNew files created: {len(newly_created_files)}")
    update_track_numbers()
else:
    print("\nNo new files were created during this run.")
    # Still update track numbers for existing files if any exist
    update_track_numbers()