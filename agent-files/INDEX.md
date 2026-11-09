# pano-docker project index

Pano is a home surveillance system. This repo (pano-docker) runs it with docker: a
lighttpd web frontend, a vsFTPd server, and the pano python application (`pano/`).

## Top-level
* AGENTS.md - agent instructions (DOIT, HEY, self-documentation protocols)
* README.md - project readme
* update-docker-2026.md - plan to modernize the three Dockerfiles (pano/lighttpd/vsftpd)
* docker-compose.yml - compose file wiring the pano/lighttpd/vsftpd stacks; pano config is bind-mounted read-only
* docker-compose-build.sh - build images via Compose v2 (`pano_compose`)
* docker-compose-pull.sh - pull images via compose
* docker-compose-setup.sh - one-time setup: env vars, config check, `pano_compose`
* docker-compose-up.sh - bring the stack up via compose
* docker-compose-down.sh - bring the stack down via compose
* start-dockers.sh - start all docker containers
* stop-dockers.sh - stop all docker containers
* .gitignore - ignore rules

## agent-files/
* agent-files/INDEX.md - this catalog
* agent-files/LOG.md - change log for agent-files
* agent-files/amcrest-plugin.md - Amcrest/Dahua NPMedia browser plugin: packaging,
  NPAPI/Cocoa glue, JS API, SDK layers, Firefox 51 requirement, macOS 26 failure
* agent-files/amcrest-modern-access.md - plan for replacing the plugin on ARM Mac:
  why emulation is dead, vendor-app dead ends, CGI/snapshot + motion-mask model,
  browser-based local console design (no signing), MVP, optional live-streaming
  effort assessment, camera-replacement exit path
* agent-files/amcrest-console-plan.md - implementation plan for the plugin-free
  console: CLI (`--camera-ip`), browser login screen, Basic/Digest proxy, layout,
  HTTP/security model, phases, tests, risks
* agent-files/amcrest-config-reference.md - Configuration-tab reference for all
  config items (General/Network/NAS/NTP/Encode/AutoMaintain/MotionDetect):
  per-model IP2M-842 vs IP3M-943B applicability, NA/inert marking, console
  widget types, and correlation to the camera's built-in web UI pages
* agent-files/amcrest-camera-contact.md - dated camera probe log ONLY (identity
  lives in pano-cameras.md): 2026-11-01 reachability per Wi-Fi/wired
  interface, IP2M-842 Basic-auth correction, cam-01 firmware/mask/mirror, ARP,
  next steps; plus 2026-11-06 live motion-model verification (legacy mask
  operative, only window0 populated, windows 1-3 empty/inert) and the cam-05
  12-row anomaly
* agent-files/amcrest-rpc2-api.md - reverse-engineered RPC2 JSON API: endpoints,
  login handshake (realm/random + doubled MD5), session/cookie, configManager
  getConfig/setConfig tables, CGI-vs-RPC2 behavior, open questions
* agent-files/dahua-rpc-api-index.md - index of the third_party/dahua-rpc-api
  submodule: module-by-module contents, session/keepalive notes, cookie caveat
* agent-files/amcrest-cameras-from-log.md - Amcrest cam config (TCP/IP, FTP, encode,
  Auto Maintain, P2P serials, mobile-app onboarding) extracted from pano-log.pdf images
* agent-files/shinobi-from-log.md - (OBSOLETE) Shinobi NVR config (monitor/stream/
  record/user) extracted from pano-log.pdf images
* agent-files/network-and-misc-from-log.md - OpenDNS, Firefox, router, motion, Pi,
  wireframe notes extracted from pano-log.pdf images (contains obsolete Shinobi-era misc)
* agent-files/pano-cameras.md - THE camera inventory of record: cam-00..cam-11 with
  model, location, pano description, MACs, Wi-Fi and wired IPs, per-interface status,
  active IP, auth scheme, in-config flag, firmware and serial
* agent-files/pano-log-overview.md - quick-reference from pano-log.pdf text
  (endpoints, directories, external links, bugs/enhancements); camera table moved to
  pano-cameras.md
* agent-files/pano-log-chronology.md - condensed dated history from pano-log.pdf text
  (2024→2017; pre-pano/Zoneminder/Shinobi entries marked obsolete)
* agent-files/pano-procedures.md - operational procedures from pano-log.pdf text
  (add camera, FTP setup, camera networking, start/stop, debug, permissions,
  pano-docker.json `@`-prefixed comment-key convention)
* agent-files/docker-cheatsheet.md - docker command reference from pano-log.pdf text
* agent-files/update-docker-2026.md - executed 2026 Docker modernization plan (rel002
  bases, config bind-mount, toolchain caveats)

## amcrest-console/
* amcrest-console/README.md - run steps, LAN access, security model,
  logging/diagnostics, motion-mask UI, Configuration tab/forms, backups and
  Network warnings, tests
* amcrest-console/camera.py - shared stdlib CGI client: explicit Basic/Digest,
  request lock, throttle/backoff, identity cache, camera model auto-detection
  (`getDeviceType`), legacy mask codec helpers, RPC2 fallback with the
  client-set DhWebClientSessionID cookie, redacted protocol logging
* amcrest-console/console.py - phase 1 CLI: `--ip`, optional `--model`
  override (auto-detected at login), LAN bind (`--bind`, `--allow-host`), root
  URL, reachability check, browser launch, `--state-dir`/`--state-file`/
  `--backup-dir`, protocol logging to `<state-dir>/log-<slug>.log` with
  `--log-level`/`--log-file`; phase 4b `--noui --config {read,write}`
  with `--config-file`, `--dry-run`, `--include-secrets`, `--pano-config`,
  `--password-env`; firmware query `--noui --firmware` (RPC2
  `magicBox.getProductDefinition`, never the crash-prone
  `getSoftwareVersion` CGI)
* amcrest-console/server.py - LAN server: Host/Origin checks, browser login,
  single in-memory session, snapshot proxy, motion mask GET/PUT, config
  GET/POST, full backup download, state endpoint, API/protocol logging
* amcrest-console/schemas.py - phase 3 allowlisted config sections, field
  metadata, form groups, validation and secret flags
* amcrest-console/configfile.py - phase 4b non-interactive config read/write:
  config-document IO, Network-section compare-and-abort guard, and the shared
  section write/verify core used by `POST /api/config`
* amcrest-console/credentials.py - phase 4b non-interactive credential lookup
  (`--pano-config` -> `$AMCREST_PASSWORD` -> tty prompt) shared with
  discover.py
* amcrest-console/cgi_config.py - phase 3 flat CGI config parsing, revisions,
  diff/validation, and RPC2 table read-modify-write helpers
* amcrest-console/mask.py - phase 2 legacy 18x22 mask codec, validation, revision
* amcrest-console/state.py - phase 2 per-camera JSON mirror: atomic writes, lock,
  redaction, corrupt-file quarantine
* amcrest-console/static/ - frontend (index.html, app.js, style.css): Legacy mask
  editor tab plus read-only Region masks tab (all four MotionDetectWindow grids,
  color legend, horizontal flip for legacy alignment), snapshot + motion mask
* amcrest-console/discover.py - phase 0 discovery: CLI camera target, preemptive
  Basic (IP2M-842) / Digest (IP3M-943) with model detection, skips the
  IP2M-842 getSoftwareVersion web-server crash, sanitized config/snapshot fixtures,
  opt-in full-18-row legacy mask write
* amcrest-console/tests/test_discover.py - unittest coverage for parsing, redaction,
  pano credential lookup, Basic/Digest auth, JPEG dimensions, full-row mask writes
* amcrest-console/tests/test_camera.py - client tests: credential verify, identity
  caching/skip, backoff, request serialization, mask mirroring, log redaction and
  truncation
* amcrest-console/tests/test_server.py - server tests: Host/Origin rejection,
  single-session replacement, login/cookie, snapshot proxy, logout, static
  serving, motion get/apply, stale revision, write verification, mirror creation
* amcrest-console/tests/test_mask.py - mask codec tests: LSB order, round-trip,
  boundaries, invalid shapes, revision
* amcrest-console/tests/test_state.py - mirror tests: slug/path, atomic write,
  0600, redaction, corrupt/schema quarantine
* amcrest-console/tests/test_console.py - CLI tests: default `log-<slug>.log`,
  IP fallback, `--log-file` override, parent creation, 0600, bind/allow-host,
  backup-dir forwarding, LAN URL listing
* amcrest-console/tests/test_schemas.py - section/field metadata, secret and
  dangerous flags, validation/normalization tests
 * amcrest-console/tests/test_cgi_config.py - canonical revisions, diff/RMW,
   rejection of non-writable/unknown fields, RPC2 table conversion tests
 * amcrest-console/tests/test_configfile.py - phase 4b config read/write,
   Network-section mismatch guard, writable filtering, plan/verify/abort tests
 * amcrest-console/cameras/ - per-camera JSON mirrors, `config-<slug>.json`
   exports, and `log-<slug>.log` protocol logs (runtime; gitignored)
* amcrest-console/backups/ - sanitized pre-write config backups
  `<slug>-<timestamp>.json` (runtime; gitignored)
* amcrest-console/fixtures/ - local discovery output (snapshots/configs; gitignored)

## docker-vsftpd/
* docker-vsftpd/Dockerfile - almalinux:9 vsftpd image build
* docker-vsftpd/.dockerignore - build context exclusions
* docker-vsftpd/start.sh - container entrypoint
* docker-vsftpd/vsftp.conf - plain vsftpd config
* docker-vsftpd/vsftp_ftps.conf - FTPS (explicit TLS) config
* docker-vsftpd/vsftp_ftps_implicit.conf - FTPS (implicit TLS) config
* docker-vsftpd/vsftp_ftps_tls.conf - FTPS with added TLS options
* docker-vsftpd/README.md - vsftpd image notes

## lighttpd-docker/
* lighttpd-docker/Dockerfile - alpine:3.20 lighttpd image build
* lighttpd-docker/.dockerignore - build context exclusions
* lighttpd-docker/start.sh - container entrypoint
* lighttpd-docker/etc/lighttpd/lighttpd.conf - main lighttpd config
* lighttpd-docker/etc/lighttpd/mime-types.conf - mime type map
* lighttpd-docker/etc/lighttpd/mod_cgi.conf - CGI module config
* lighttpd-docker/etc/lighttpd/mod_fastcgi.conf - FastCGI module config
* lighttpd-docker/etc/lighttpd/mod_fastcgi_fpm.conf - FastCGI + PHP-FPM config
* lighttpd-docker/.github/workflows/docker-deploy.yml - CI docker deploy workflow
* lighttpd-docker/README.md - lighttpd image notes
* lighttpd-docker/LICENSE - license
* lighttpd-docker/passwd.digest - digest auth passwords
* lighttpd-docker/.gitignore - ignore rules

## pano/
Application code and runtime data.
* pano/Dockerfile - pano image build (python:3.14-slim-trixie)
* pano/.dockerignore - build context exclusions (runtime data, config, media)
* pano/requirements.txt - pinned pip deps (click)
* pano/pano.py - main pano application
* pano/campage.py - camera page renderer
* pano/indexpage.py - index page renderer
* pano/datastore.py - datastore layer
* pano/derived.py - derived data
* pano/dirwalk.py - directory walker
* pano/dtutils.py - datetime utilities
* pano/panoconfig.py - config loading
* pano/path_parser.py - path parsing
* pano/timeit.py - simple timing utility
* pano/watchdog.py - watchdog/monitor
* pano/pano-docker.json - docker runtime config
* pano/pano-no-docker.json - non-docker runtime config
* pano/pano-docker-test.json - test variant config
* pano/panodb.sqlite - sqlite database
* pano/pano.log - runtime log
* pano/pano-breadcrumb.txt - breadcrumb text
* pano/start-pano-docker.sh - start pano under docker
* pano/start-pano-chuyu-server.sh - start chuyu server

### pano/config/
* pano/config/00_readme.txt - config readme
* pano/config/lighttpd.conf - lighttpd config for pano
* pano/config/lighttpd-restart.sh - restart lighttpd
* pano/config/readme-lighttpd.txt - lighttpd notes
* pano/config/org.robertyu.pano.plist - launchd agent
* pano/config/org.robertyu.pure-ftpd.plist - launchd agent (pure-ftpd)

### pano/www/
Frontend assets (bootstrap + custom).
* pano/www/css/bootstrap*.css(.map) - bootstrap stylesheets
* pano/www/css/styles.css - custom styles
* pano/www/js/bootstrap.min.js, jquery.min.js, popper.min.js - frontend js
* pano/www/js/scripts.js - custom scripts
* pano/www/fonts/glyphicons-halflings-regular.* - glyphicons fonts
* pano/www/mryuck.png - logo image

## amcrest-support/
Amcrest/Dahua camera browser plugin artifacts (not used by pano at runtime).
* amcrest-support/amcrest-plugin.zip - camera plugin archive (npmedia.bundle)
* amcrest-support/npmedia.bundle/ - Dahua/Amcrest Netscape (NPAPI) plugin bundle:
  Contents/Info.plist, MacOS/npmedia binary, Frameworks/*.so|dylib (dhnetsdk, dhplay,
  etc.), Resources (icons/bmp/cur, en.lproj strings)
* amcrest-support/amcrest-camera-support/README.md - amcrest plugin support notes
* amcrest-support/amcrest-camera-support/Firefox 51.0b9.dmg - old firefox installer for plugin
* amcrest-support/amcrest-camera-support/webplugin_alps.pkg - web plugin package

### pano/camera-mount/
* pano/camera-mount/README.md - printed camera mount notes
* pano/camera-mount/SECURITY_mount2.stl - 3D-print template
* pano/camera-mount/SECURITY_mount2.zcode - CAM .zcode file
* pano/camera-mount/SECURITY_mount2.zprojx - CAM project
* pano/camera-mount/images/ - mount photos

### pano/writeup/
* pano/writeup/writeup.txt - writeup text
* pano/writeup/writeup.moin - moin-wiki format writeup
* pano/writeup/dfd/ - data-flow-diagram images (jpeg/resized)
* pano/writeup/ - screenshots/photos (media-page, status screens, alley day/night,
  cam-config, cam-mount photos, halo, resolution tests, readme media)

## third_party/
* third_party/dahua-rpc-api/ - git submodule: Dahua/Amcrest JSON-RPC API
  reference (13 module docs, README, MIT) plus a minimal `requests` client;
  catalogued in agent-files/dahua-rpc-api-index.md

## readme-images/
Documentation screenshot/photos used by README: Panopticon jpegs, cam-mount-0,
59[M][0@0][0].jpg, 2023-04-26 pano screenshot, etc.

## Excluded from index
* `*~` backup files
* pano/__pycache__/*.pyc bytecode