import requests
from datetime import datetime, timedelta
from pydub import AudioSegment
import os

# Function to download a file from a given URL and save it with the specified filename
def download_file(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {filename}")

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
    output_filename = f"C:\\Users\\m_ren\\Downloads\\C895_Cafe_Chill_KNHC_{date_str}.mp3"
    if not os.path.exists(output_filename):
        for time_slot in time_slots:
            filename = f"KNHC_{date_str}{time_slot}.m4a"
            audio = AudioSegment.from_file(filename, format="m4a")
            combined += audio
        combined.export(output_filename, format="mp3")
        print(f"Combined file {output_filename} created")
        
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