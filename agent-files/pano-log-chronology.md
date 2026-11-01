# Project Panopticon — chronological log

Imported (condensed) from the **text** of `~/pano-log.pdf`. Reverse-chronological as in
the source. Credentials omitted. Entries marked **(obsolete)** belong to pre-pano
systems (Zoneminder, Shinobi) that were abandoned.

## 2024

- **2024.05.18** — Trying to run Firefox 51 (last NPAPI-capable) for the Amcrest plugin.
  Crashes on macOS 11.4 (green macbook) and on Intel MBP; runs on pink macbook (10.13).
  Connecting to a camera auto-downloaded/installed `webplugin_alps.pkg`. Putting
  firefox51 + webplugin in `pano/amcrest-support`. Still use the Amcrest iOS app to set
  region sensitivity.
- **2024.05.12** — Wanted to adjust cam-07 motion settings but the npmedia bundle plugin
  can't run on Linux; hit "technical debt wall"; reolink suggested as alternative.
- **2024.04.14** — OpenDNS shows heavy Amcrest traffic. Block all but necessary URLs so
  the app works: `dh.amcrestsecurity.com`, `amcrestview.com`, `p2p.amcrestview.com`,
  `www.amcrestcloud.com`; blocking `amcrestsecurity.com` still leaves the app working.
- **2024.02.05** — Upgrading mac mini to mac-mini-2024 (ARM) → loses the usual Firefox 51
  setup; it won't run on ARM. Considering a Linux version.

## 2023

- **2023.10.26** — None of the docker images rebuild; CentOS (vsftpd base) is
  unsupported and its yum repo is offline. Ensure images are on Docker Hub; use
  `docker-compose-pull.sh`.
- **2023.06.14** — Set all cameras to DST: Mar 12 02:00 – Nov 5 02:00.
- **2023.03.11** — Punting on vsftpd logging to stdout (hard/impossible); `tail -f | tee`
  works but the log grows monotonically.
- **2023.03.10** — Make compose pull from Docker Hub rather than build. `docker login`,
  tag/pull `robyu/pano-docker_vsftpd:rel001`; set `image:` + `build: context:`. Notes on
  compose build tag behavior.
- **2023.03.09** — Deleted a mess of docker images, then rebuilds fail (Alpine removed
  the pinned lighttpd package). Do **not** build lighttpd from within `lighttpd-docker`;
  use the compose script so env vars are set. Updated lighttpd to 1.4.64-r0 and fixed
  the pano docker. Got pano running via `start-dockers.sh` (debug line drops into bash);
  created `/home/pano/develop` volume mapping to the host source so scripts can be edited
  live. index.html was missing the accordion because the initial page was generated
  before any files were processed. pano crashed on cull (permission denied on bad
  derived dirs); manually fixed perms. Documented Docker Hub tagging.
- **2023.03.09 (later)** — Replaced `/mnt/HD2` device with an internal SATA drive;
  afterward pano generated malformed index.html (accordion missing). Philosophy: the app
  should generate/validate directories itself (deleting `./pano` should still work); fail
  loudly.
- **2023.02.12** — Firefox 51 + NP plugin working again after clearing history/cookie
  cache (about:preferences#privacy).
- **2023.01.31** — Disabling the daily reboot stopped cameras deleting older images. But
  cam-07 now keeps images/video during motionless evenings. Can't open camera settings
  (plugin crashes even in Firefox 51); Amcrest no longer supports the camera; considering
  Dahua firmware.
- **2023.01.26** — cam-07/08 delete images while cam-09 is fine, same firmware; IP3M-943
  unsupported. Things to try: disable nightly reboot, delete+re-add FTP config, factory
  reset. Disabled auto-reboot and auto-delete on cam-08 (192.168.2.138).

## 2022

- **2022.12.26** — cam-07 has 2 days of images, cam-08 only 1 (since 9:53am); cam-07's
  earlier files disappeared between 14:24–14:40. Try toggling "auto delete old files".
- **2022.12.25** — cam-07/08 retaining only 1 day; pano.log shows no deletion entries;
  cam-07..09 are newer IP-43 but cam-09 works. Log shows pano trying to delete
  non-existent cam-07 files from 2022-12-10.
- **2022.12.24** — cam-08 only today's images; cull repeatedly tries to delete files
  that don't exist.
- **2022.10.12** — Police requested alley-cam videos. Many DAVs didn't convert to mpg
  correctly (partial corruption). AVI works better but preview breaks:
  `ffmpeg -i foo.dav foo.avi`.
- **2022.07.30** — HD2 died; pano docker restart-looped because the `www` directory must
  be set up a specific way (now done by `pano/start-pano-docker.sh`).
- **2022.06.15** — Bugs: HD2 filling up; need log rotation; lighttpd access errors; use
  docker logging (compose log size/count; startup logs to stdout).
- **2022.04.02** — cam-07 missing from panopticon; works in app; FTP settings fine;
  camera "Test" → "failure, list right loss" (known firmware bug). FTP to 192.168.2.8
  works; no uploads since Mar 12. Deleting the cam-07 dir + rebooting the camera brought
  new files. Standardized time settings + daily reboot schedule in the spreadsheet.
- **2022.03.26** — cam-09, cam-07 down after Tuesday power-cycle for cleaning; suspect
  GFI flipped.
- **mar 21 2022** — Webserver not expanding cams; dockers had restarted (cams-00/02
  expiring?). Updated Ubuntu + restarted; removed cams-00/02 from JSON temporarily.
- **feb 26 2022** — Replace old cameras: cam-02 → cam-08 (wired, front-north), cam-00 →
  cam-09 (wifi, front-south). JSON validation + add-camera procedure (see
  `pano-procedures.md`). vsftpd not pinned to a version (3.0.3).
- **feb 3 2022** — Amcrest app flow to bring up a camera and get the serial. Issues:
  front/north too sensitive; 4 more IP3M (12 total) but wired/wireless scheme only allowed
  10. chuyu-server must boot in desktop mode or docker swarm won't start (power-outage
  risk). Camera networking procedure (see `pano-procedures.md`).
- **2022.02.05** — Safari can't reach the Amcrest UI much longer; Firefox supports
  plugins until v51. Downloaded firefox 51.0b9 — works with the plugin (temporary fix;
  long-term: macOS High Sierra docker). Disable Firefox updates after install; it
  already knows about the NP plugin.
- **dec 4 2021** — Raise `max_age_days` 14→21 by editing `pano-docker.json`, then
  `docker-compose down` + `./docker-compose-up.sh`. Page slow to update; `tail -F
  /mnt/HD2/pano/logs/pano.log`. Lighttpd rebuild failed (Alpine pinning); `phusion/baseimage:latest`
  gone — found a workaround; images built.

## 2021

- **apr 26 2021** — Docker log rotation not working.
- **apr 19 2021** — Enhancement ideas (see overview).
- **apr 15 2021** — Add log rotation to pano; also needed for vsftpd/lighttpd.
- **apr 09 2021** — Starting pano-docker: three images as a compose service; `up`/`down`
  (wrapped in a script for env vars); auto-restarts after reboot; logs to
  `/mnt/HD2/pano/logs`; webpages at `http://192.168.2.8:8080`. FTP "test" button always
  reports a write-permissions error. docker-compose replaces supervisord (edited
  supervisord.conf; `supervisorctl reread/update`).
- **apr 06 2021** — Compose reference/manual links.
- **apr 04 2021** — Run pano attached for debugging (`docker run -it -v ... pano`).
- **apr 01 2021** — lighttpd won't serve `www/derived` or `www/FTP`; those volumes must
  be mounted and symlinks created inside the lighttpd container.
- **mar 31 2021** — lighttpd won't serve symlinked derived/FTP; supervisord lighttpd logs
  under `/var/logs`.
- **mar 30 2021** — SQL to reset `derive_failed`; run
  `python pano.py --loglevel=info --logfname=stdout --nodroptable ...`. Derived files not
  landing correctly; cull traceback (derived/cam-00 missing).
- **mar 6 2021** — Getting unit tests working again; installed sqlitebrowser.
- **feb 28 2021** — supervisord starts/stops the pano dockers (scripts in
  `~/supervisord-config`); dockers in `~/ryu/2020/pano-docker`. Migrated off the
  spreadsheet. Preparing 2 new cameras: current IP2M-842, upgrade to IP3M-943B.
- **oct 31 2020** — After switching to Xfinity, renamed the 2.4 GHz network consistently
  (cameras are 2.4 GHz only). .125/.126 went offline; decided to set fixed wired IPs on
  all cameras so they survive a rename/reboot.
- **june 7** — supervisord runs `stop-start-dockers.sh`.
- **may30** — Running pano dockers: `cd ~/2020/pano-docker; ./start-dockers.sh`; lighttpd
  port 8080; volumes under `/mnt/HD2/pano`.
- **may28** — fstab mounts; permission problems (pano docker can't create symlinks:
  `PermissionError /var/FTP -> /var/www/FTP`).
- **may26** — Revisit vsftpd (local fork of loicmathieu/vsftpd not running).
- **may25** — HTML assumes media under ./derived and ./FTP; symlinks already in www.
- **may17** — Fixed logging; webserver working with pano; lighttpd symlinks; export
  /var/FTP and /var/derived volumes.
- **may15** — Logging broken with python3.8 (stderr + file); TODO fix logging, rename
  `baseline_datetime` → `latest_datetime`.
- **may13** — `python3 pano.py --droptable pano-macmini.json --loglevel debug
  --logfname stdout --loopcnt 1`.
- **may12** — Copy www assets to /var/www on startup (mapped drive appears empty);
  `baseline_datetime: "now"`.
- **apr30** — mod_auth challenges but doesn't recognize the username; check lighttpd.conf.
- **apr 28** — Find a lighttpd image (spujadas/lighttpd-docker, sebp/lighttpd); build/run;
  browse mryuck.png; need mod_auth.
- **apr 27** — vsftpd working via loicmathieu/docker-vsftpd; tested with cam-05 (worked).
- **apr 24** — tacocat dead; recreate pano in docker. (Docker cheatsheet — see
  `docker-cheatsheet.md`.)
- **apr 12** — tacocat acting weird (no autologin, sporadic/slow boot) → suspect corrupted
  drive.
- **jan 16** — pano stopped (keyboard pulled → reboot → hung); pure-ftpd not running;
  manual start via launchctl; disk check ok.
- **nov 2 (2020)** — Launching pure-ftpd as root at startup: use launchctl + plist (copy
  to `~/pano/config/org.robertyu.pure-ftpd.plist`); add `-U 113:002`; file must be
  root:wheel. Also: `cull_by_ext` used a delete-list instead of a keep-list → rewrote to
  keep-list, deleting many old `.dav_/.idx_` files.
- **nov 1** — Configuring pure-ftpd (mac pain); umask `-U 113:002` → files 664, dirs 775.
- **oct 31** — Log falling behind up to 2 hours; purge fails because ftpupload dirs are
  755 ftpupload:admin; built-in ftpd can't change perms → use third-party (pureftpd).
- **sep 2** — Media HD filled; perms only let ftpuser delete; modify purge to verify
  deleted files are gone.
- **aug 29** — Network woes from rclone not dying + camera traffic; inserted a switch
  isolating the cameras.
- **aug 10** — Network woes caused by camera (disconnecting attic ethernet fixed router);
  spikes from cam-04. Set video duration 30s → 15s except porch cam-01.
- **jul 23** — Startup on mac via launchd + plist in `~/Library/LaunchAgent` (painful);
  TODO refactor derive.py into an object.
- **jul 22** — New 2TB in tacocat; moved all FTP uploads to tacocat.
- **jul 19** — Mac mini HDD upgrade references.
- **jul 18** — FTP server on mac: `/Volumes/HD500GB-2/FTP`, chmod, user, home dir, sharing
  + remote login, `dseditgroup ... com.apple.access_ftp`. Can't use port 80 (need root);
  copy mryuck.png to www.
- **jul 13** — Install lighttpd on macOS (`brew services`); www dir `/usr/local/var/www`;
  symlinks via `www-dir-setup.sh`; lighttpd.conf; mod_auth digest with `htdigest`.
- **jul 11** — Make `convert` location a JSON param; check availability at startup.
- **jul 10** — Installing pano on mac-mini tacocat (192.168.2.47): git clone pano +
  ryu-env; brew python3/lighttpd/imagemagick; pip pudb/click.
- **june 26** — Clicking a photo opens it in a new tab.
- **june 05 (2019)** — pure-ftpd errors (buffer IO error, sda2); external drive
  disconnected/unmounted; stop pure-ftpd, killall, remount.
- **may 28** — New drive; update `~/FTP` symlink to `/media/wd2tb/FTP`; update symlinks.
- **may 23** — Screwed up fstab → Pi won't boot; recovery links; do not put
  `init=/bin/sh` on a separate line; added `noauto`.
- **may 22** — Added 2TB external HDD; needs powered USB hub; exfat-fuse; fstab UUID.
- **apr 23** — 2 weeks/6 cameras uncovered bugs: derived fname listed but doesn't exist;
  empty dirs not culled (FIXED); move cull empty dirs to sleep cycle; index page updates
  too slowly (move derivation outside page gen); better skip flags.
- **apr 20** — wd1tb filled during spring break; video stutter = DAV missing frames.
- **apr 5** — Amcrest "smart player" sucks; ffmpeg on mac converts fine:
  `ffmpeg -i foo.dav foo.mp4`; `-crf 0` = lossless; benchmarked presets.
- **mar 10** — Script for DAV→mp4 via ffmpeg (Dav2Mp4 notes).
- **mar 6** — Buying 2 more cams for door entrances + an 850 nm illuminator.
- **jan 22 2019** — Unit tests failing (python2/3 issues, many errors).
- **jan 17 2019** — Auto boot after power loss via rc.local.
- **jan 5 2019** — TODO: optimize processing, finish writeup, startup.

## 2018

- **dec 13** — Password-protect HTTP (lighttpd digest auth via htdigest; restart).
- **dec 2** — Cleaned garage, tweaked camera positions; "done with the actual system";
  wished for a status light on the camera.
- **dec 1** — Port forward 65534 → 192.168.2.110:80; enable lighttpd accesslog.
- **nov 30** — Modify ffmpeg to use OpenMAX; subprocess output to logger; garage cam-03
  works; cam-04 had no WiFi because its power outlet was on a light switch.
- **nov 26** — Bootstrap accordion + anchor; **kerberos (obsolete)** only supported 1
  camera; surveillance software evaluation link.
- **nov 25** — Installing garage cams; need Ethernet (mesh/faraday issue).
- **nov 22** — pure-ftp transfer log: `/var/log/pure-ftpd/transfer.log`.
- **nov 18** — Newest Amcrest uploads.
- **nov 17** — TODO: startup script, writeup, back cameras, python3, fix tests, reboot
  times 7am.
- **nov 15** — Camera times off by 1 hour when DST isn't in effect; disable NTP sync.
- **nov 14** — Boot startup references; `/etc/init.d/lighttpd`.
- **nov 13** — Camera criteria (price, browser config, FTP, JPG, MPG, 1080p, IR,
  scheduled reboot, viewing angle). Essay: arguments against cloud-based cameras.
- **nov 10** — Unit tests failing (python2).
- **oct 29** — TODO: python3, better image browsing (bottle rejected), document campage,
  status photo on index, alley setup (2 cams, PoE, ethernet), bootup.
- **oct 11–23** — UI work: carousel CSS, navbar HTML snippets.
- **oct 11** — Amcrest serial numbers 121/120/122.
- **oct 10** — Bootstrap collapse/navbar links.
- **oct 3** — Document full Amcrest setup; hostname 192.168.2.122 → cam-02.
- **sep 25** — Unicode/python3; bottle (rejected — dev server only).
- **sep 23** — Logging docs.
- **sep 22** — Hardwired eth to Pi; reset resolution to test glitches.
- **sep 20** — Pi temp 60.7°C; IP3M-943 supposedly does MP4 (not for IP2M-842) — "no more
  amcrest/foscam cameras".
- **sep 19** — `lighttpd -D -f /etc/lighttpd/lighttpd.conf`; TODO move JSON into
  panoconfig.py.
- **sep 17** — Remaining TODO (fps, python3, logging, bad uploads, bootup, alley, network,
  clear-media flag, watchdog, docs, VPN/dd-wrt).
- **sep 16** — Launch python at startup; Amcrest firmware downloads; emailed Amcrest
  asking for MP4/AVI output.
- **sep 7 / sep 6 / sep 4 / sep 1** — Bootstrap modal/collapse, CSS positioning,
  details/summary, HTML video links.
- **aug 20** — Remaining TODO; execution had stopped Aug 13 (thumb file didn't exist).
- **jul 28 / jul 21 / jul 17 / jul 12** — Video-in-popup; symlinks `/var/www/FTP` →
  `/media/wd1t/FTP`, `/var/www/derived` → `/media/wd1t/derived`, remove absolute paths
  (incl. mryuck.png); unit tests; mobile view in Chrome.
- **jul 2 / jul 1 / jul 10 / jul 9** — Test timings; unit tests.
- **june 23/20/18/17/16/13/8/7/6/5** — SQLite unique constraint; hashlib md5;
  performance timings; cull-by-age traceback; Pi swapfile 1GB (gen_derived works);
  Pi temp 75.2°C; subprocess OOM "cannot allocate memory"; `python3 -m http.server`;
  rpi ssh; cron deletes >2 weeks; bitbucket push; "database is locked" test errors.
- **may30 / May 17 / April 30 / April 27 / April 25** — CLI (click); testdata failures;
  best DAV→mp4; time formats; "Stuff Left to Do" (test pages over 1-2 days, time-date,
  mobile tabs, dirwalker class, scheduler, worker pool, config JSON, home page with
  activity graph, auto-startup, watchdog, publishing HTML, more cameras).
- **apr 12** — **Shinobi super login / mysql credentials / forums (obsolete; creds
  omitted)**.
- **apr 13** — Chrome devtools tips. **apr 12** — wireframe (`https://wireframe.cc/TDdU94`);
  thumbnail-from-video ffmpeg.
- **mar 12 / mar 5 / mar 3 / mar 1** — Headless Pi; thingiverse Amcrest mount; sqlite in
  python tutorial; lsof; docker+python.
- **feb 26** — Revelation: stop cramming ffmpeg onto the Pi (cameras already encode);
  **abandon Shinobi (obsolete)**. Plan: cameras do motion + upload to FTP; a script does
  housekeeping (cull, DAV→mp4, thumbnails, dead-simple webpage), optional no-activity /
  disk-space warnings; package into docker. DAV→mp4 via ffmpeg is fast.
- **feb 22** — Samba masked; pureftpd service; created samba user (creds omitted);
  DAV→mp4 command that works (generates errors): `ffmpeg -i ...dav -vcodec copy -preset
  veryfast out2.avi`. Noted Shinobi applies form ffmpeg params even in COPY mode.
- **feb 21** — Amcrest firmware download; prepared 2nd camera 192.168.2.122; labels for
  every camera (MAC + IP); moved FTP to `/media/wd1t/FTP`.
- **feb 16** — ffmpeg process started; **Shinobi (obsolete)** crashed in the morning
  (maybe when camera rebooted; "not very stable").
- **feb 15** — ftpd on Pi (`/var/log/pure-ftpd/transfer.log`); **Shinobi (obsolete)**
  running again.
- **feb 13** — Bail on another tp-link router (WDS issues, dd-wrt flashing limits); bought
  2 cams; dd-wrt repeater bridge (halves bandwidth); maybe PoE.
- **feb 12** — archer c7 hw v4 lacks WDS; **Shinobi (obsolete)** recording but camera
  crashed; reboot URL; set up daily reboot.
- **feb 11** — Stuck: no compute platform for 4 cams, unhappy with **Shinobi
  (obsolete)**, WiFi doesn't reach NE corner; need core i7 server; estimate 5-7 cams.
- **feb 8** — Motion detection not working; recording hangs at limits; set limit 21 GB
  (fixes it).
- **feb 7** — Enabled **Shinobi (obsolete)** motion plugin; can't see diagnostics.
- **feb 6** — 15-min video file listing; **feb 2** — installed **Shinobi (obsolete)** on
  mac + process list.
- **jan 30 / jan 28 / jan 27 / jan 26 / jan 23 / jan 22 / jan 21** — ffmpeg ~22% Pi
  memory; libx264 vs h264_omx benchmark; ffmpeg hw-accel compile flags; ordered Pi;
  1080p recordings 150-210 MB/file; logging to 1TB HDD, FPS oddities, compute stick,
  ultrafast preset, process-monitor crashes.
- **jan 20** — Intel compute stick STCK1A8LFC (anemic, 1-2 cams); **Shinobi (obsolete)**
  superuser setup (creds omitted).
- **jan 8** — Reduced bandwidth (bitrate 4096); iOS app works with substream; amcrest
  bullet0 MAC 3c-ef-8c-9c-85-6d → 192.168.2.120; can't connect via app.
- **jan 6 / jan 5 / jan 4** — Camera shows in **Shinobi (obsolete)**; VLC/RTSP/HTTP
  URLs + encode config caps; compute-stick Ubuntu links.

## 2017 (pre-pano; Zoneminder/Shinobi era — obsolete)

- **dec 30–23** — **Shinobi (obsolete)** w/ 2 USB cams; keep-videos days; camera/CPU
  shopping; /dev/video0 and Cheese device-busy (added ryu to `video` group); shinobi
  install on Ubuntu VM (MariaDB); **Zoneminder (obsolete)** install attempts (Linux Mint,
  docker kylejohnson/zoneminder, LAMP/tasksel). Alternatives considered: shinobi, blue
  iris, motion eye.
- **dec 26** — Video-clients spreadsheet; kerberos only on Pi (obsolete).
