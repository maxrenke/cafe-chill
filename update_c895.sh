#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Always run from the script's own directory so relative paths work
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# ---------------------------------------------------------------------------
# Returns the date (YYYY-MM-DD) of the most recent occurrence of a given
# weekday in UTC. dow: 0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat 6=Sun.
# Includes today if today matches.
# File names on the CDN are keyed to the UTC date the show posts, so all
# date math here must use UTC to stay consistent with the Python downloaders.
# ---------------------------------------------------------------------------
last_weekday_date() {
    local target_dow=$1
    local today_dow=$(( $(date -u +%u) - 1 ))
    local days_back=$(( (today_dow - target_dow + 7) % 7 ))
    date -u -d "${days_back} days ago" +%Y-%m-%d
}

# ---------------------------------------------------------------------------
# Decides whether to run a show's download.
# Returns 0 = go ahead, 1 = skip.
#   available_dow: UTC weekday when files become available (0=Mon..6=Sun)
# ---------------------------------------------------------------------------
should_run() {
    local show_name="$1"
    local target_dir="$2"
    local expected_file="$3"
    local available_dow="$4"

    local dow=$(( $(date -u +%u) - 1 ))

    # Day before available_dow
    local day_before=$(( (available_dow + 6) % 7 ))

    # If today is the day before the show is available → skip
    if [ "$dow" -eq "$day_before" ]; then
        echo -e "${YELLOW}⏭  ${show_name}: not aired yet — files available tomorrow. Skipping.${NC}"
        return 1
    fi

    # Already downloaded this week's episode?
    if [ -f "$expected_file" ]; then
        echo -e "${CYAN}✔  ${show_name}: already have $(basename "$expected_file"). Skipping.${NC}"
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
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

    bash "./${script_name}"
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        echo -e "${GREEN}✔ Successfully updated ${show_name}!${NC}"
        echo -e "  ${GREEN}Files in: ${target_dir}${NC}"
    elif [ "$rc" -eq 75 ]; then
        echo -e "${YELLOW}⏭  Skipped ${show_name} — moving to next show.${NC}"
    else
        echo -e "${RED}✖ Error updating ${show_name}. See output above.${NC}"
    fi
    echo
}

# ---------------------------------------------------------------------------
echo -e "${YELLOW}=======================================${NC}"
echo -e "${YELLOW} C89.5 Master Update Script            ${NC}"
echo -e "${YELLOW} $(date -u '+%Y-%m-%d %H:%M UTC')      ${NC}"
echo -e "${YELLOW}=======================================${NC}"
echo

# ── Cafe Chill ── airs/available Sunday UTC (dow=6)
CAFE_DIR="/DATA/Media/Music/C895/c895_cafe_chill"
CAFE_DATE=$(last_weekday_date 6)
CAFE_FILE="${CAFE_DIR}/C895_Cafe_Chill_KNHC_${CAFE_DATE}.mp3"
echo -e "${CYAN}── Cafe Chill (expected: ${CAFE_DATE}) ──${NC}"
if should_run "Cafe Chill" "$CAFE_DIR" "$CAFE_FILE" 6; then
    run_show_script "cafe_chill_simple.sh" "Cafe Chill" "$CAFE_DIR"
fi

# ── Push The Tempo ── airs Friday night, available Saturday UTC (dow=5)
PTT_DIR="/DATA/Media/Music/C895/c895_push_the_tempo"
PTT_DATE=$(last_weekday_date 5)
PTT_FILE="${PTT_DIR}/C895_Push_The_Tempo_KNHC_${PTT_DATE}.mp3"
echo -e "${CYAN}── Push The Tempo (expected: ${PTT_DATE}) ──${NC}"
if should_run "Push The Tempo" "$PTT_DIR" "$PTT_FILE" 5; then
    run_show_script "push_the_tempo_simple.sh" "Push The Tempo" "$PTT_DIR"
fi

# ── Powermix ── airs Friday night, available Saturday UTC (dow=5)
PM_DIR="/DATA/Media/Music/C895/c895_powermix"
PM_DATE=$(last_weekday_date 5)
PM_FILE="${PM_DIR}/C895_Powermix_KNHC_${PM_DATE}.mp3"
echo -e "${CYAN}── Powermix (expected: ${PM_DATE}) ──${NC}"
if should_run "Powermix" "$PM_DIR" "$PM_FILE" 5; then
    run_show_script "powermix_simple.sh" "Powermix" "$PM_DIR"
fi


# ---------------------------------------------------------------------------
# Make sure each show's latest episode has a synced tracklist embedded as
# chapters (idempotent — skips files that already have them).
# ---------------------------------------------------------------------------
echo -e "${CYAN}── Ensuring latest episodes have synced chapters...${NC}"
python3 "$SCRIPT_DIR/ensure_chapters.py"
echo

# ---------------------------------------------------------------------------
# Refresh "latest.mp3" symlinks so the lofi-radio web app always serves the
# newest episode of each show at a stable URL (/c895/<show>/latest.mp3).
# ---------------------------------------------------------------------------
echo -e "${CYAN}── Updating latest.mp3 symlinks...${NC}"
for d in c895_cafe_chill c895_powermix c895_push_the_tempo; do
    show_dir="/DATA/Media/Music/C895/${d}"
    newest=$(ls "${show_dir}"/C895_*_KNHC_*.mp3 2>/dev/null | sort | tail -1)
    if [ -n "$newest" ]; then
        ln -sfn "$(basename "$newest")" "${show_dir}/latest.mp3"
        echo -e "  ${GREEN}${d}/latest.mp3 -> $(basename "$newest")${NC}"
    fi
done

# Extract embedded chapters -> latest.chapters.json sidecars for the web app.
echo -e "${CYAN}── Writing chapter sidecars...${NC}"
python3 "$SCRIPT_DIR/gen_chapters_json.py"

# Sync Spotify M3U playlists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${CYAN}── Syncing Spotify playlists...${NC}"
python3 "$SCRIPT_DIR/sync_spotify.py" &&     echo -e "${GREEN}✔ Spotify playlists updated.${NC}" ||     echo -e "${RED}✖ Spotify sync failed.${NC}"
