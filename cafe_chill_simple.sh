#!/bin/bash

# Simple bash script to run cafe_chill_direct.py
# This version saves files directly to /DATA/Media/Music/C895

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

# Run the Python script
python3 "$PYTHON_SCRIPT"

echo "Script completed. Check $TARGET_DIR for your files."
