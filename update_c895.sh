#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Always run from the script's own directory so relative paths work
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

run_show_script() {
    local script_name="$1"
    local show_name="$2"
    local target_dir="$3"

    echo -e "${YELLOW}► Starting update for: ${show_name}...${NC}"

    if [ ! -f "$script_name" ]; then
        echo -e "${RED}✖ Error: Script '$script_name' not found in $(pwd).${NC}"
        echo
        return 1
    fi

    if bash "./${script_name}"; then
        echo -e "${GREEN}✔ Successfully updated ${show_name}!${NC}"
        echo -e "  ${GREEN}Files in: ${target_dir}${NC}"
    else
        echo -e "${RED}✖ Error updating ${show_name}. See output above.${NC}"
    fi
    echo
}

echo -e "${YELLOW}=======================================${NC}"
echo -e "${YELLOW} C89.5 Master Update Script            ${NC}"
echo -e "${YELLOW} $(date -u '+%Y-%m-%d %H:%M UTC')      ${NC}"
echo -e "${YELLOW}=======================================${NC}"
echo

# Explicit ordering: Cafe Chill -> Push The Tempo -> Powermix
CAFE_DIR="/DATA/Media/Music/C895/c895_cafe_chill"
run_show_script "cafe_chill_simple.sh" "Cafe Chill" "$CAFE_DIR"

PTT_DIR="/DATA/Media/Music/C895/c895_push_the_tempo"
run_show_script "push_the_tempo_simple.sh" "Push The Tempo" "$PTT_DIR"

PM_DIR="/DATA/Media/Music/C895/c895_powermix"
run_show_script "powermix_simple.sh" "Powermix" "$PM_DIR"

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN} Done.                                 ${NC}"
echo -e "${GREEN}=======================================${NC}"

