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
  NPAPI/Cocoa glue, JS API, SDK/framework layers, Firefox 51 requirement
* agent-files/amcrest-cameras-from-log.md - Amcrest cam config (TCP/IP, FTP, encode,
  Auto Maintain, P2P serials, mobile-app onboarding) extracted from pano-log.pdf images
* agent-files/shinobi-from-log.md - (OBSOLETE) Shinobi NVR config (monitor/stream/
  record/user) extracted from pano-log.pdf images
* agent-files/network-and-misc-from-log.md - OpenDNS, Firefox, router, motion, Pi,
  wireframe notes extracted from pano-log.pdf images (contains obsolete Shinobi-era misc)
* agent-files/pano-log-overview.md - quick-reference from pano-log.pdf text: endpoints,
  camera inventory table, external links, bugs/enhancements
* agent-files/pano-log-chronology.md - condensed dated history from pano-log.pdf text
  (2024→2017; pre-pano/Zoneminder/Shinobi entries marked obsolete)
* agent-files/pano-procedures.md - operational procedures from pano-log.pdf text
  (add camera, FTP setup, camera networking, start/stop, debug, permissions)
* agent-files/docker-cheatsheet.md - docker command reference from pano-log.pdf text
* agent-files/update-docker-2026.md - executed 2026 Docker modernization plan (rel002
  bases, config bind-mount, toolchain caveats)

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

## readme-images/
Documentation screenshot/photos used by README: Panopticon jpegs, cam-mount-0,
59[M][0@0][0].jpg, 2023-04-26 pano screenshot, etc.

## Excluded from index
* `*~` backup files
* pano/__pycache__/*.pyc bytecode