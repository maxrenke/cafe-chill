#!/usr/bin/env python3
"""Print the track currently airing live on C89.5 (KNHC)."""

from spinitron_tracklist import fetch_now_playing


def main():
    result = fetch_now_playing()
    if result is None:
        print("Couldn't reach Spinitron.")
        return
    time_text, artist, title, release = result
    line = f"[{time_text}] {artist} - {title}"
    if release:
        line += f" ({release})"
    print(line)


if __name__ == "__main__":
    main()
