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

Source table ("src: Project Panopticon Cameras"). WiFi addresses are DHCP (reserved via
the Google WiFi router app); wired addresses are static set on the camera itself.

| Name  | Iface | Location          | WiFi MAC          | WiFi IP       | Wired MAC         | Wired IP      | Serial               | Reboot |
|-------|-------|-------------------|-------------------|---------------|-------------------|---------------|----------------------|--------|
| cam-00 |       |                   | 3c:ef:8c:9c:85:6d | 192.168.2.120 | 9c:8e:cd:00:a4:b5 | 192.168.2.130 | AMC0028VA32S795UUB   |        |
| cam-01 | wifi  | porch             | 4c:11:bf:f5:89:a0 | 192.168.2.121 | 3c:ef:8c:64:fa:93 | 192.168.2.131 | AMC002A34HATK2G7HH   | 7:20   |
| cam-02 |       |                   | 3c:ef:8c:9c:85:c5 | 192.168.2.122 | 9c:8e:cd:00:a4:4c | 192.168.2.132 | AMC002768U5C4RHDK5   |        |
| cam-03 | wifi  | alley/look south  | 4c:11:bf:f4:48:91 | 192.168.2.123 | 4c:11:bf:e4:7b:b7 | 192.168.2.133 | AMC0027049793x76D1   | 13:33  |
| cam-04 | both  | alley/look north  | 3c:ef:8c:87:3c:2d | 192.168.2.124 | 3c:ef:8c:96:1b:19 | 192.168.2.134 | AMC002A47KTRBGDT10   | 14:22  |
| cam-05 | wifi  | deck              | 3c:ef:8c:9c:87:86 | 192.168.2.125 | 9c:8e:cd:00:a2:a2 | 192.168.2.135 | AMC0021AFXD4837U12   | 15:55  |
| cam-06 | wifi  | backyard/look N   | 3c:ef:8c:9c:83:43 | 192.168.2.126 | 9c:8e:cd:00:a6:e7 | 192.168.2.136 | AMC002U5127780784R   | 16:06  |
| cam-07 | wifi  | front/look north  | 9c:8e:cd:0d:2b:56 | 192.168.2.127 | 9c:8e:cd:0d:27:6e | 192.168.2.137 | AMC0184DF01N44       | 14:44  |
| cam-08 | both  | front/look north  | 9c:8e:cd:0d:3a:89 | 192.168.2.128 | 9c:8e:cd:0d:36:a1 | 192.168.2.138 | AMC018T127Y2F424P2   | 10:03  |
| cam-09 | wifi  | front/look south  | 9c:8e:cd:12:f6:c6 | 192.168.2.129 | 9c:8e:cd:12:f2:ce | 192.168.2.139 | AMC01861PG72172R3Q   | 11:11  |
| cam-10 |       |                   | 9c:8e:cd:12:f6:c6 | 192.168.2.119 | 9c:8e:cd:0f:c9:71 | 192.168.2.140 | AMC018GK64Q92016DM   |        |
| cam-11 |       |                   | 9c:8e:cd:0f:cf:be | 192.168.2.118 | 9c:8e:cd:0f:cb:d6 | 192.168.2.141 | AMC018X9031328K52C   |        |

Notes (from the doc):
- DHCP addresses are assigned from the Google WiFi router app (see robertyu.org network
  notes).
- All wired addresses are statically configured on the camera itself, **not** from the
  router app (redundant settings cause no communications). This lets you always reach a
  camera over a cable even if the router is down.
- Values above were reconstructed from the rendered page (the raw `pdftotext` output
  scrambles the table's multi-line cells). They match the source.
- **Source error:** cam-10's WiFi MAC (`9c:8e:cd:12:f6:c6`) is identical to cam-09's —
  an obvious author copy/paste typo. cam-10's real WiFi MAC is unverified.

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
