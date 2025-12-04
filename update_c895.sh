#!/bin/bash

# Define ANSI color codes for colorful logging
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run a show's update script and log the outcome
run_show_script() {
    local script_name="$1"
    local show_name="$2"
    local target_dir="$3"

    echo -e "${YELLOW}► Starting update for: ${show_name}...${NC}"

    # Check if the script exists and is executable
    if [ ! -f "$script_name" ]; then
        echo -e "${RED}✖ Error: Script '$script_name' not found.${NC}"
        echo
        return
    fi
    
    # Execute the script, capturing its output
    # The output is still printed to the console in real-time
    if bash "./${script_name}"; then
        # Exit code is 0 (success)
        echo -e "${GREEN}✔ Successfully updated ${show_name}!${NC}"
        echo -e "  ${GREEN}Final file location: ${target_dir}${NC}"
    else
        # Exit code is not 0 (error)
        echo -e "${RED}✖ An error occurred while updating ${show_name}.${NC}"
        echo -e "  ${RED}Review the script output above for specific errors.${NC}"
    fi
    echo # Add a blank line for better separation
}

# --- Main Script Execution ---
echo -e "${YELLOW}=======================================${NC}"
echo -e "${YELLOW} C89.5 Master Update Script ${NC}"
echo -e "${YELLOW}=======================================${NC}"
echo

# Define the shows and their corresponding scripts and directories
declare -A shows
shows["Cafe Chill"]="cafe_chill_simple.sh;/DATA/Media/Music/C895/c895_cafe_chill"
shows["Push The Tempo"]="push_the_tempo_simple.sh;/DATA/Media/Music/C895/c895_push_the_tempo"
shows["Powermix"]="powermix_simple.sh;/DATA/Media/Music/C895/c895_powermix"

# Loop through and run the script for each show
for show in "${!shows[@]}"; do
    script_and_dir=${shows[$show]}
    script=${script_and_dir%;*}
    dir=${script_and_dir#*;}
    run_show_script "$script" "$show" "$dir"
done

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN} All update scripts have been executed. ${NC}"
echo -e "${GREEN}=======================================${NC}"
