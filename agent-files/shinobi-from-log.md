> **OBSOLETE / HISTORICAL ONLY.** Shinobi is no longer used. Its role was superseded
> by pano (cameras self-encode and upload over FTP; pano does post-processing). This
> file is kept only as reference history.

# Shinobi NVR notes (from Project Panopticon Log) — OBSOLETE

Source: embedded screenshots in `~/pano-log.pdf`, pages noted. **Credentials, email and
group key are omitted.**

Shinobi was the community NVR tried before pano. It was abandoned in favor of letting
the cameras do their own encoding and upload snapshots/video to FTP, with pano doing
the post-processing (cull, DAV→mp4, thumbnails, web pages).

## Monitor input (Edit Monitor > Input)

- Input Type: **H.264 / H.265 / H.265+**
- Connection Type: **RTSP**; RTSP Transport: **TCP**
- Host: camera IP (e.g. 192.168.2.120, 192.168.2.123), Port **80**
- Path: **/cam/realmonitor?channel=1&subtype=0**
- (username/password omitted)
- Also available: JPEG API Snapshot (cgi-bin), Raw H.264 Stream

## Stream output

- Stream Type: **MJPEG** (one configuration used **Base64 over Websocket**)
- # of allowed MJPEG clients: **20** (0 = infinite)
- Check Signal Interval: **10** min; Log Signal Event: **No**
- Quality: **1**; Rate: **10 fps**; Width **1920**; Height **1080**
- Video Filter / Rotate fields available (ffmpeg filters)

## Recording (for H.264/H.265 input)

- Record File Type: **MP4 (copy, libx264, libx265)**
- Video Codec: **libx264 (Default)**; Quality **1** (1=High, 28=Low); Preset **veryfast**
- Audio Codec: **No Audio**
- Video Record Rate: **2 fps**; Record Width **1280**; Height **720**
- Recording Segment Interval: **15** min; Double Quote Directory: **No**

## User / storage (Edit user)

- Max Storage Amount: **10000 MB**
- Keep Videos: **10** days; Keep Events: **10** days; Keep Logs: **10** days
- (email, group key, password omitted)

## Dashboard / operations

- Top bar shows CPU load, RAM, disk usage %, and a stream thumbnail
  (e.g. "2 CPUs on Darwin", ~4.29 GB RAM; other runs "1 CPU on Linux").
- Superuser console at `:8080/super` (e.g. 192.168.163.195:8080/super).
- Recurring instability: "Process Crashed for Monitor", "Video Finished"/"Unexpected
  Exit" events; heavy ffmpeg CPU/memory use (one ffmpeg ≈ 22% of Pi memory). These
  problems drove the move off Shinobi.
