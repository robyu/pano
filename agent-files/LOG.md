2026-10-31 Created agent-files/INDEX.md - initial project catalog from recursive search
2026-10-31 Created agent-files/LOG.md - initial change log
2026-10-31 Ingested ~/pano-log.pdf (text + 60 embedded images); created amcrest-cameras-from-log.md, shinobi-from-log.md, network-and-misc-from-log.md (credentials omitted)
2026-10-31 Marked shinobi-related notes obsolete (shinobi-from-log.md banner, INDEX/network-and-misc annotations)
2026-10-31 Imported pano-log.pdf text: created pano-log-overview.md, pano-log-chronology.md, pano-procedures.md, docker-cheatsheet.md (credentials omitted; obsolete systems flagged)
2026-10-31 Corrected camera-table note in pano-log-overview.md; flagged source's duplicate cam-10/cam-09 WiFi MAC as an author typo
2026-10-31 Removed firefox/ and firefox-125.0.3.tar.bz2 from INDEX.md (deleted by user)
2026-10-31 Changed max_age_days 15.0 -> 21.0 in pano/pano-docker.json (image retention); requires pano image rebuild + restart
2026-10-31 Created update-docker-2026.md - Dockerfile modernization plan (pano/lighttpd/vsftpd blockers, targets, sequencing)
2026-10-31 Executed Docker modernization (rel002): pano -> python:3.14-slim-trixie, lighttpd -> alpine:3.20, vsftpd -> almalinux:9; pinned base digests; added healthchecks/.dockerignore/requirements.txt
2026-10-31 Bind-mounted pano/pano-docker.json read-only (removed from image); removed VOLUME /home/pano which was masking updated code with a stale 2023 anonymous volume
2026-10-31 Verified rel002 runtime: config edit+restart changes max_age_days, camera pages regenerate, FTP uploads/derive work, lighttpd auth and vsftpd login OK
2026-10-31 Noted chuyu toolchain caveat: build with legacy docker-compose; recreate with /usr/libexec/docker/cli-plugins/docker-compose v2 (legacy 1.29.2 fails on Docker 28)
2026-10-31 Migrated scripts to Compose v2 via pano_compose in docker-compose-setup.sh; added docker-compose-down.sh; updated README/INDEX/docs
2026-11-01 Created agent-files/amcrest-plugin.md - analysis of npmedia NPAPI plugin (packaging, glue, JS API, Dahua SDK layers, Firefox 51 requirement)
2026-11-01 Moved amcrest plugin artifacts (amcrest-camera-support/, amcrest-plugin.zip, npmedia.bundle/) into repo-root amcrest-support/; updated INDEX.md and amcrest-plugin.md paths
2026-11-01 Created agent-files/amcrest-modern-access.md - analysis/plan for plugin-free Config+Live View (mask editing) on ARM Mac: emulation verdict, vendor-app dead ends, CGI/RTSP data model, PySide6 design, MVP
2026-11-01 Added pointer from amcrest-plugin.md to amcrest-modern-access.md
2026-11-01 Scoped amcrest-modern-access.md to Config + snapshot-based mask editing; live view/RTSP/PyAV deferred out of MVP
2026-11-01 Settled console signing: personal single-machine use -> ad-hoc signature, no notarization/Developer ID (self-signed only if TCC churn)
2026-11-01 Changed amcrest-modern-access.md to browser-based local web console (Python proxy + HTML/JS); recorded desktop-vs-browser trade-off and local-vs-server deployment; no code signing
2026-11-01 Added optional single-camera live-streaming assessment to amcrest-modern-access.md (no audio/recording; MJPEG-first, HLS fallback, WebRTC only if low latency needed)
2026-11-01 Added frontmatter (update, tags: amcrest-console) to amcrest-modern-access.md per AGENTS.md
2026-11-01 Decided console runs its own standalone local webserver; rejected reuse of pano's docker/lighttpd stack
2026-11-01 Created agent-files/amcrest-console-plan.md - implementation plan (CLI `--camera-ip`, layout, routes/security, phases, tests); linked from amcrest-modern-access.md and INDEX.md
2026-11-01 Implemented amcrest-console/discover.py + tests: phase 0 read-only discovery (Digest/Basic, config/snapshot fixtures, redaction, full-18-row legacy mask write)
2026-11-01 Ran phase 0 against cam-09 (192.168.2.129, IP3M-943B fw 2.400): legacy Region writable, 4-window Region writes ignored, partial writes reset mask; FTP config is NAS, System/FTP invalid
2026-11-01 Restored cam-09 legacy mask exactly after write probes; window model differs (values preserved in fixture); documented in amcrest-console-plan.md
2026-11-01 Added amcrest-console/fixtures/ to .gitignore; 13 discover tests passing
2026-11-01 Probed all known cameras: cam-07/08/09 + cam-09 wired reachable (IP3M-943B fw 2.400, legacy+4 windows); cam-01/03/04/05/06 ping but no TCP services; cam-00 down
2026-11-01 Corrected camera diagnosis: iOS app shows live streaming for cam-01/03/04/05/06 (P2P); IP2M-842 local HTTP briefly open then refused, likely HTTP restart or source-IP login lock, not camera offline
2026-11-01 Created agent-files/amcrest-camera-contact.md - consolidated read-only probe results (reachable IP3M-943B, flapping IP2M-842 HTTP, iOS P2P evidence, ARP, next steps)
2026-11-01 Re-probed both Wi-Fi and wired IPs per camera table: IP2M-842 Wi-Fi up with port 80 but HTTP closes on request; wired mostly down (cam-04 wired up); IP3M-943 cam-08 both up, cam-09 wired flapped. Updated contact/plan docs.
2026-11-01 Recorded current API status: CGI usable on cam-07/08/09; not usable on cam-01/03/04/05/06 (TCP 80 then connection closed); iOS P2P does not imply CGI; re-test after stopping stream/confirming password
2026-11-01 Fixed discover.py auth: explicit Basic header or separate Digest opener; default timeout 15s. Verified cam-01 Basic auth: magicBox 200, MotionDetect 200 (11,832 bytes)
2026-11-01 Design decision: console uses browser login screen (username+password), credentials in proxy memory only; HttpOnly SameSite session cookie; logout clears. Recorded in plan/modern-access docs
2026-11-01 Corrected docs: pano password is correct; earlier RD was client auth bug plus slow/single-connection IP2M-842 HTTP, not stale credentials. Recorded cam-01 mask values and legacy/window mirror
2026-11-01 Updated contact/plan/INDEX/LOG with auth status: cam-01 CGI works; cam-03/04/05/06 need retest with fixed client; cam-07/08/09 Digest OK
2026-11-01 Updated amcrest-plugin.md: Firefox 51/NPMedia path dead on macOS 26 Tahoe (32-bit i386, no Rosetta i386); modern browser login + CGI still work; added frontmatter
2026-11-01 Finalized docs: browser-login acceptance/risk criteria, one-request-at-a-time camera I/O, legacy-only mask writes; no credentials recorded
2026-11-01 Documented pano-docker.json convention: top-level keys starting with "@" are comments (panoconfig.py:122/128); added to pano-procedures.md, INDEX.md
2026-11-01 Fixed discover.py for IP2M-842: preemptive Basic, model-based auth, @camera_list skipped, 1s request delay, lockout hint; added tests (19 passing); docs updated
2026-11-01 Root-caused IP2M-842 web-server crashes: getSoftwareVersion crashes/restarts the web server. discover.py now queries getMachineName/getDeviceType first, skips getSoftwareVersion for IP2M-842, and uses a short Mozilla UA + Connection: close; full 8-camera discovery passes (24 tests)
2026-11-01 Reworded IP2M-842 getSoftwareVersion docs/code: "resets the HTTP server" -> "crashes/restarts the web server"
2026-11-01 Recorded cam-01 (192.168.2.121) IP2M-842 firmware 2.212.0000.2.R (build 2016-08-11) and WEB 3.2.1.273284 from its built-in webpage; serial AMC002A34HATK2G7HH confirmed
