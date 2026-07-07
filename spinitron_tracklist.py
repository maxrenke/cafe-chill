"""Fetch synced tracklists for C89.5 (KNHC) shows from Spinitron.

KNHC logs every song it plays to Spinitron with a wall-clock timestamp.
Given a show's title, air date, and known start/duration, this looks up
the matching playlist on Spinitron's public calendar feed, scrapes the
per-song air times, and converts them into elapsed-seconds offsets that
line up with the downloader scripts' concatenated MP3s (which start at
the show's first hourly segment).
"""

import html
import json
import re
from datetime import datetime, timedelta

import requests

CALENDAR_FEED_URL = "https://spinitron.com/KNHC/calendar-feed"
STATION_URL = "https://spinitron.com/KNHC/"
SPIN_ROW_RE = re.compile(
    r'data-spin="({.*?})"[^>]*><td class="spin-time"><a[^>]*>([^<]+)</a>'
)
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_now_playing():
    """Return (time_text, artist, title, release) for the currently airing track.

    KNHC's station page lists its most recent spins newest-first, so the
    top entry is whatever's live on air right now (with whatever small lag
    exists between a song starting and the DJ/automation logging it).
    """
    resp = requests.get(STATION_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    match = SPIN_ROW_RE.search(resp.text)
    if match is None:
        return None
    spin = json.loads(html.unescape(match.group(1)))
    return match.group(2), spin.get("a"), spin.get("s"), spin.get("r", "")


def _fetch_calendar_events(air_date):
    """Return calendar-feed events spanning the day before/after air_date."""
    start = (air_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (air_date + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = requests.get(
        CALENDAR_FEED_URL,
        params={"timeslot": 30, "start": start, "end": end},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _find_show_event(events, title_keyword, air_date, start_hour, duration_hours):
    """Pick the calendar event matching this show's title/date/start hour.

    Spinitron occasionally logs overlapping/duplicate entries for the same
    slot (e.g. a rebroadcast) so we prefer the event whose start hour and
    duration match what the downloader script expects.
    """
    keyword = title_keyword.lower().replace("'", "")
    candidates = []
    for event in events:
        title = event["title"].lower().replace("'", "")
        if keyword not in title:
            continue
        event_start = datetime.strptime(event["start"], "%Y-%m-%dT%H:%M:%S%z")
        event_end = datetime.strptime(event["end"], "%Y-%m-%dT%H:%M:%S%z")
        if event_start.date() != air_date:
            continue
        candidates.append((event, event_start, event_end))

    if not candidates:
        return None

    def score(candidate):
        _, event_start, event_end = candidate
        hour_match = event_start.hour == start_hour
        duration_match = abs((event_end - event_start).total_seconds() / 3600 - duration_hours) < 0.5
        return (hour_match, duration_match, (event_end - event_start).total_seconds())

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def _parse_spins(playlist_url_path, event_start, event_end):
    """Fetch a Spinitron playlist page and return (elapsed_seconds, artist, title, release) tuples."""
    resp = requests.get(f"https://spinitron.com{playlist_url_path}", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    page = resp.text

    tracks = []
    for spin_json, time_text in SPIN_ROW_RE.findall(page):
        spin = json.loads(html.unescape(spin_json))
        artist, title = spin.get("a"), spin.get("s")
        if not artist or not title:
            continue

        clock = datetime.strptime(time_text.strip(), "%I:%M %p").time()
        for day_offset in (0, 1):
            candidate = datetime.combine(
                (event_start + timedelta(days=day_offset)).date(), clock,
                tzinfo=event_start.tzinfo,
            )
            if event_start - timedelta(minutes=5) <= candidate <= event_end + timedelta(minutes=15):
                elapsed = (candidate - event_start).total_seconds()
                tracks.append((max(0, int(elapsed)), artist, title, spin.get("r", "")))
                break

    return tracks


def fetch_tracklist(title_keyword, air_date, start_hour, duration_hours):
    """Look up a show's synced tracklist.

    Args:
        title_keyword: substring to match against Spinitron event titles,
            e.g. "Cafe Chill", "Powermix", "Push The Tempo".
        air_date: date object for the day the show actually aired (local/Pacific).
        start_hour: expected local start hour (0-23) of the show.
        duration_hours: expected show length in hours.

    Returns:
        List of (elapsed_seconds, artist, title, release) tuples sorted by
        elapsed_seconds, or None if no matching playlist was found (e.g. not
        posted to Spinitron yet).
    """
    events = _fetch_calendar_events(air_date)
    match = _find_show_event(events, title_keyword, air_date, start_hour, duration_hours)
    if match is None:
        return None
    event, event_start, event_end = match
    tracks = _parse_spins(event["url"], event_start, event_end)
    tracks.sort(key=lambda t: t[0])
    return tracks


def _format_timestamp(seconds):
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def write_sidecar_tracklist(txt_path, tracks):
    """Write a human-readable '[h:mm:ss] Artist - Title' file next to the MP3."""
    with open(txt_path, "w") as f:
        for elapsed, artist, title, release in tracks:
            line = f"[{_format_timestamp(elapsed)}] {artist} - {title}"
            if release:
                line += f" ({release})"
            f.write(line + "\n")


def embed_chapters(mp3_file_path, tracks, total_duration_seconds):
    """Embed ID3v2 chapter markers (CTOC/CHAP) so players can show the current track."""
    from mutagen.id3 import ID3, CTOC, CHAP, TIT2, CTOCFlags

    audio = ID3(mp3_file_path)
    for key in list(audio.keys()):
        if key.startswith("CHAP:") or key.startswith("CTOC:"):
            del audio[key]

    if not tracks:
        return

    chapter_ids = []
    for i, (elapsed, artist, title, _release) in enumerate(tracks):
        start_ms = int(elapsed * 1000)
        end_ms = int(tracks[i + 1][0] * 1000) if i + 1 < len(tracks) else int(total_duration_seconds * 1000)
        chap_id = f"chp{i}"
        chapter_ids.append(chap_id)
        audio.add(CHAP(
            element_id=chap_id,
            start_time=start_ms,
            end_time=end_ms,
            sub_frames=[TIT2(encoding=3, text=f"{artist} - {title}")],
        ))

    audio.add(CTOC(
        element_id="toc",
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=chapter_ids,
        sub_frames=[TIT2(encoding=3, text="Tracklist")],
    ))
    audio.save(v2_version=3)


def add_tracklist_to_show(mp3_file_path, title_keyword, air_date, start_hour, duration_hours):
    """Fetch the tracklist for a show and attach it (sidecar .txt + embedded chapters).

    Returns the list of tracks found, or None if no playlist was available yet.
    Safe to call even if Spinitron hasn't posted the playlist -- failures are
    caught and logged rather than breaking the download pipeline.
    """
    try:
        tracks = fetch_tracklist(title_keyword, air_date, start_hour, duration_hours)
        if not tracks:
            print(f"  No Spinitron tracklist found yet for {title_keyword} on {air_date}")
            return None

        txt_path = mp3_file_path.rsplit(".", 1)[0] + ".txt"
        write_sidecar_tracklist(txt_path, tracks)

        from mutagen.mp3 import MP3
        total_duration = MP3(mp3_file_path).info.length
        embed_chapters(mp3_file_path, tracks, total_duration)

        print(f"  Tracklist: {len(tracks)} songs -> {txt_path} (+ embedded chapters)")
        return tracks
    except Exception as e:
        print(f"  Tracklist fetch failed (non-fatal): {e}")
        return None
