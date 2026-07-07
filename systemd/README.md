# systemd — C89.5 now-playing updater

Runs `now_playing_json.py --if-requested` every 30s to refresh
`/DATA/Media/Music/C895/now_playing.json`, which the lofi-radio web app polls
while the C89.5 live stream is playing.

`--if-requested` gates the Spinitron scrape on the web app actually polling the
sidecar (detected via the `lofi-radio-app` container's access log), so it only
hits Spinitron while someone is listening, not 24/7.

## Install

```bash
sudo cp c895-nowplaying.service c895-nowplaying.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now c895-nowplaying.timer
```

Check it: `systemctl list-timers c895-nowplaying.timer`
