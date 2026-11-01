# Docker Modernization Plan (2026)

Status: EXECUTED 2026-10-31 — all three images rebuilt and running as `rel002`.

Config note: `pano/pano-docker.json` (`max_age_days: 21.0`) will no longer be baked
into the pano image. It is bind-mounted read-only from the host at
`$PWD/pano/pano-docker.json` -> `/home/pano/pano-docker.json`. Edit the host file and
restart pano to apply; no image rebuild is required. pano reads config only at startup
(`panoconfig.py:94`), and never writes it, so `:ro` is safe.

## Current state / blockers

| Image    | Base                              | Blocker |
|----------|-----------------------------------|---------|
| pano     | `phusion/baseimage:focal-1.0.0` + deadsnakes python3.7 | `apt install python3.7` fails (PPA dropped focal builds) |
| lighttpd | `alpine:3.15.0`, pinned `lighttpd=1.4.64-r0` | EOL alpine, package version no longer in repo |
| vsftpd   | `centos:centos8.4.2105`           | CentOS 8 EOL (mirrors/content dead) |

Three separate failures; order the work pano -> lighttpd -> vsftpd so the retention
fix lands first.

## Target

| Image    | New base                              | Py/runtime |
|----------|---------------------------------------|------------|
| pano     | `python:3.14-slim-trixie` (decided)   | system `ffmpeg imagemagick sqlite3 tzdata ca-certificates procps`; pip `click` pinned |
| lighttpd | `alpine:3.20` (current stable)        | `apk add lighttpd lighttpd-mod_auth apache2-utils bash tzdata nano`, no exact package pin |
| vsftpd   | `almalinux:9` (decided; ships vsftpd 3.0.5, same RHEL layout/paths) | `dnf install nano openssl vsftpd` |

## Pinned base digests

- `python:3.14-slim-trixie@sha256:cd89c30eda26ee911a4611b18680086e0ea42e6f5f8cbe653d07fa7958c9cec8`
- `alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc`
- `almalinux:9@sha256:245f8aab832fe800aa42bdab5fad75ebbd8e0b4c9f24820a83c638b177857ae2`

Resolved 2026-10-31 via `docker buildx imagetools inspect` (index digests).

## Cross-cutting changes (all images)

- Pin base images **by digest** instead of fragile package versions.
- Add `.dockerignore` per build context. The pano context is ~190MB (sqlite, writeup,
  amcrest support, npmedia bundle) but only ~1.3MB (py + www) is copied; exclude the rest.
- Stop baking `pano-docker.json` into the image; bind-mount it read-only from the host
  (Option B). This also keeps camera credentials out of image layers. Add a file-exists
  check in `docker-compose-setup.sh` so Docker cannot create a directory at the mount path.
- Use `ENV key=value` form (fixes the LegacyKeyValueFormat warning).
- Use a `requirements.txt` with pinned versions instead of ad-hoc `pip install`; drop
  `pudb` from prod (its only use is an unused import in `watchdog.py`).
- Keep UID/GID build-args and non-root `pano` user.
- Add `HEALTHCHECK` and compose `healthcheck`.
- Drop compose `version: '3'` (obsolete).
- Bump `IMAGE_TAG=rel002` so old images remain for rollback.

## Per-image steps

### pano

1. Rebase on `python:3.14-slim-trixie`; delete `add-apt-repository`/deadsnakes/
   `update-alternatives`/python3.7 lines. `python3` is already correct.
2. `apt-get install -y --no-install-recommends ffmpeg imagemagick sqlite3 tzdata
   ca-certificates procps` (add `nano` optional; `procps` for the healthcheck).
3. Create `pano/requirements.txt` (`click`, pinned `8.5.0`) and
   `pip install --no-cache-dir -r requirements.txt`.
4. `dtutils` is not needed from PyPI: `pano/dtutils.py` is a local module providing
   `sec_to_str`/`now_to_str` and shadows the installed package. Drop the pip install.
4b. Remove unused `import pudb` from `pano/watchdog.py:4` so prod does not need `pudb`.
5. `.dockerignore` to exclude runtime data (`*.json` incl. pano-docker.json, logs, sqlite,
   `__pycache__`, docs/media dirs). No multi-stage build needed (only pure-Python deps).
6. Build via `./docker-compose-build.sh` (Compose v2 plugin); recreate only pano.

### lighttpd

1. `FROM alpine:3.20`; remove `LIGHTTPD_VERSION` pin (let apk pick the matching
   version).
2. Keep `passwd.digest`, config COPYs, UID/GID user creation.
3. Fix `ENV` -> `ENV TZ=America/Los_Angeles`.
4. `start.sh` mounts are unchanged (paths preserved).
5. Add `.dockerignore` (`.github/`, `README.md`, `LICENSE`).

### vsftpd

1. Use `almalinux:9` (decided): swap `yum` -> `dnf`, same `/etc/vsftp`,
   `/usr/sbin/vsftpd` paths; ships vsftpd 3.0.5 (config compatible with 3.0.3).
2. Change `start.sh` shebang to `#!/bin/bash` for the existing bashisms (`&>/dev/null`,
   `[[ ]]`), even though RHEL `/bin/sh` is bash today.
3. Note: TLS cert perms are `755` - tighten to `600` while here.
4. Add `.dockerignore`.
5. Risk: if vsftpd fails under AlmaLinux PAM in-container, comment
   `session required pam_loginuid.so` in `/etc/pam.d/vsftpd`.

## Sequencing & verification

1. Bind-mount config via `PANO_CONFIG="$PWD/pano/pano-docker.json"` (setup script);
   verify compose interpolation before building.
2. pano: `./docker-compose-build.sh` -> `./docker-compose-up.sh` -> check `docker
   inspect` mount source, `pano.log` for `max_age_days = 21.0`, camera page loads, a
   new FTP image gets slurped/derived.
3. lighttpd: build -> up -> verify auth + camera page assets over :8080.
4. vsftpd: build -> up -> upload a test file over FTP and confirm pano picks it up.
5. Keep old `rel001` images tagged until all three pass.

## Rollback

- Revert `IMAGE_TAG=rel001` and run `./docker-compose-up.sh`; images still present.
- Old Dockerfiles remain in git history.
- `rel001` has the config baked in, so reverting the compose mount still runs.

## Decisions (resolved 2026-10-31)

1. Python target: **3.14** (`python:3.14-slim-trixie`); no fallback needed (local dtutils).
2. vsftpd base: **almalinux:9** for the smallest delta from CentOS 7/8-era paths.
3. Config: **bind-mount** `$PWD/pano/pano-docker.json` -> `/home/pano/pano-docker.json`
   (read-only), remove it from the image. pano must be restarted to re-read edits.

## Execution results (2026-10-31)

- pano: Python 3.14.10, ffmpeg 7.1.5, ImageMagick 7.1.1 (provides `convert`),
  sqlite3 3.46.1, click 8.5.0. Removed unused `pudb` import. Local `dtutils.py` used.
- lighttpd: 1.4.85 on Alpine 3.20.10; `lighttpd-mod_auth` + `nc` healthcheck work.
- vsftpd: 3.0.5 on AlmaLinux 9.8; existing 3.0.x config worked unchanged.
- **Removed `VOLUME /home/pano`**: it created an anonymous volume that masked newer
  image code (the running container had 2023-era `.py` files from an old volume).
  Code now comes from the image; `/home/pano/develop` and `/home/pano/logs` remain
  volumes.
- Added `container_name: pano-docker_<service>_1` to keep the pre-existing names
  (Compose v2 otherwise uses hyphens).
- Verified config bind mount: host edit `21.0` -> `21.5` + `docker restart pano`
  produced `max_age_days = 21.5` in `pano.log`; reverted to `21.0` and confirmed.
- Verified runtime: pano healthy, index/camera HTML refreshed, FTP uploads accepted,
  derived files generated, lighttpd returns 401 (digest auth active), FTP login works.

### Toolchain note on chuyu (resolved by migration)

- The `docker compose` resolved by the Docker CLI here is an old experimental
  compose-cli that silently drops build args; v1 `/usr/bin/docker-compose` is EOL and
  fails to recreate containers under Docker 28 (`KeyError: 'ContainerConfig'`).
- All repo scripts now call `pano_compose` (defined in `docker-compose-setup.sh`),
  which prefers `/usr/libexec/docker/cli-plugins/docker-compose` (v2.35.1), falls back
  to a real v2 `docker compose`, then v1.
- Verified: `./docker-compose-build.sh` builds all three images via the v2 plugin, and
  `./docker-compose-up.sh` recreates/starts them healthy. Added
  `docker-compose-down.sh` for the matching teardown.
