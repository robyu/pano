---
update: 2026-11-08 PST
tags: quick-reference
---

# Project Panopticon — overview / quick reference

Imported from the **text** of `~/pano-log.pdf` ("Project Panopticon Log"). This is the
"KEEP UP TO DATE" quick-reference section at the top of that doc. **Credentials omitted**
(camera URL password, FTP account, admin logins, etc.).

## Quick reference

- Camera stream endpoints:
  - HTTP MJPEG: `http://<camera-ip>/cgi-bin/mjpg/video.cgi?channel=1&subtype=0`
  - RTSP: `rtsp://<camera-ip>:80/cam/realmonitor?channel=1&subtype=0`
  - (camera login is `admin`; password omitted)
- chuyu server: **192.168.2.8**
- pano web server: port **8080**
- Starting pano dockers: see notes 2021.04.09; if this changes, also update
  "chuyu server setup notes".
- Directories:
  - output files: `/mnt/HD2/pano`
  - pano source: `/home/ryu/2020/pano-docker`
- vsftpd server: **192.168.2.8:21** (upload account; creds omitted)
- Procedure for adding cameras / modifying JSON: see `pano-procedures.md` (2022.02.26).

## Camera inventory

Moved to **`pano-cameras.md`** (2026-11-08) — that file is the inventory of record
for cam-00…cam-11: model, location, MACs, Wi-Fi/wired IPs, status, active IP, auth,
firmware and serial. Probe history: `amcrest-camera-contact.md`.

## External references (from the doc)

- "Project Panopticon Cameras" (source table).
- "Detail Design Stuff" Google Doc:
  `https://docs.google.com/document/d/1n4Ae0iloo0cBrTICCZxejpJoaz52w04--EAVdQITsLI/edit`
- Camera spreadsheet (old, no longer used):
  `https://docs.google.com/spreadsheets/d/1EKczvIvg32XQH2ZDsnA4gf3Xf9PJD_5Fmse6NTwwNGM/edit`
- Video clients spreadsheet:
  `https://docs.google.com/spreadsheets/d/1XrhoOLGnPnRa0h7fywo1zHluGPBQhviWJb0lN-DMU4Q/edit`

## BUGS / ENHANCEMENTS (open items in the doc)

- Send alert when a camera hasn't talked in several hours.
- Make it more apparent when one camera isn't updating.
- Do log rotation for lighttpd and vsftpd.
- Need an admin console showing available disk space.
- Rename pano-docker's startup script to `start.sh`.

Additional enhancement ideas (2021.04.19):
- Log-file monitor based on tmux.
- Server status screen: time last executed, number of media files per camera, disk space.
- On restart, immediately regenerate just the web pages (without re-deriving media) so
  JSON changes take effect visibly.
- Ping admin IPs and show status.
- Change JSON to specify all possible camera IPs, add live links and admin links based
  on camera model.
