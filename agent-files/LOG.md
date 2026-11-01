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