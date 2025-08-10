#!/bin/bash

# Simple bash script to run cafe_chill_direct.py
# This version saves files directly to /DATA/Media/Music/C895
# Track numbering is now handled within the Python script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/cafe_chill_direct.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: cafe_chill_direct.py not found in $SCRIPT_DIR"
    exit 1
fi

# Create the target directory if it doesn't exist
TARGET_DIR="/DATA/Media/Music/C895"
mkdir -p "$TARGET_DIR"

# Check if we have write permissions to the target directory
if [ ! -w "$TARGET_DIR" ]; then
    echo "Error: No write permission to $TARGET_DIR"
    echo "You may need to run this script with sudo or adjust permissions"
    exit 1
fi

echo "Running cafe_chill_direct.py..."
echo "Files will be saved directly to: $TARGET_DIR"
echo "Track numbering will be applied automatically (newest file = track 0)"

# Run the Python script
python3 "$PYTHON_SCRIPT"

# Check if the Python script ran successfully
if [ $? -eq 0 ]; then
    echo "Script completed successfully!"
    echo "Check $TARGET_DIR for your files with track numbers applied."
else
    echo "Error: Python script failed to execute properly"
    exit 1
fi