# Network & misc notes (from Project Panopticon Log)

Source: embedded screenshots in `~/pano-log.pdf`, pages noted. Credentials omitted.

## OpenDNS traffic (top domains, last week) — p4

- **dh.amcrestsecurity.com** — 12,696 requests (was blacklisted; "Successfully removed
  from the blacklist").
- **www.google.com** — 10,229.
- Next domain (~9,788) — a further consumer of camera-related traffic.
- Action taken: block all but the necessary Amcrest endpoints so the app still works.
  Needed URLs: `dh.amcrestsecurity.com`, `amcrestview.com`, `p2p.amcrestview.com`,
  `www.amcrestcloud.com`. Blocking `amcrestsecurity.com` still leaves the app working.

## Firefox (used to load the Amcrest NPAPI plugin) — p9, p29

- Privacy: History set to **"Never remember history"** (clearing cache to keep the
  plugin working); also clear history/cookies to revive a crashed plugin.
- Advanced > Update: **"Never check for updates (not recommended: security risk)"** —
  Firefox 51 is frozen because later versions dropped NPAPI support.
- Firefox 51 already recognizes the NP (manifest) plugin once installed.

## Router bandwidth (Tomato 1.28) — p48, p106, p111

- Real-time WAN/Wireless graphs show large camera-driven spikes (multi-Mbps peaks,
  e.g. 8–15 Mbps). Supports the decision to isolate cameras on their own switch/network.

## Motion detection "Detection Area" dialog — p98

- Grid-based motion regions (Region0..N) overlaid on the live frame.
- Per-region **Sensitivity** (e.g. 60) and **Threshold** (e.g. 17); colored region
  boxes; `Remove All` / `Delete` (or right-click). Sample frame: street view,
  timestamp 2018-02-25 14:34:32.

## UI / wireframe sketch — p95

- Wireframe of the media browser layout: thumbnail grid on the left, and a vertical
  timeline (times 13:30 / 13:45 / 13:50; day markers Apr 11 and Apr 12 2018) mapping
  thumbnails to recorded clips (`000.mp4`, `001.mp4`). This informed pano's per-camera
  page design (accordion list + media thumbnails).

## Raspberry Pi setup — p77

- `raspi-config` GPU-memory prompt: "How much memory (MB) should the GPU have?
  e.g. 16/32/64/128/256" set to **32** (for ffmpeg/hardware decode on the Pi).

## Misc — p115, p121 (historic; Shinobi-era, OBSOLETE)

- **Cheese** webcam test capture (p115): used to verify /dev/video0 on the Shinobi VM
  (Shinobi is obsolete).
- **WiFi Diagnostics** (macOS app, v5.1) p121: used for wireless troubleshooting.
- **Ubuntu tasksel "Software selection"** p121: Basic Ubuntu server, OpenSSH, LAMP,
  Samba file server, etc. — used when building the Shinobi VM/host (Shinobi is obsolete).
