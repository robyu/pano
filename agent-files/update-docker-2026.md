# Docker Modernization Plan (2026)

Status: PLAN ONLY. No Dockerfiles have been changed yet.

Retention note: `pano/pano-docker.json` was set to `max_age_days: 21.0` and injected
into the running `pano-docker_pano_1` container (writable layer only). It will revert
to the image's baked-in `15.0` if the container is recreated before this plan is
executed.

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
| pano     | `python:3.14-slim-trixie` (or `3.13-slim` if a dep lacks 3.14 wheels) | system `ffmpeg imagemagick sqlite3 tzdata`; pip deps pinned |
| lighttpd | `alpine:3.20` (current stable)        | `apk add lighttpd lighttpd-mod_auth apache2-utils bash tzdata`, no exact package pin |
| vsftpd   | `almalinux:9` (keeps dnf + RHEL layout) or `debian:trixie-slim` | `dnf install vsftpd openssl` / `apt install vsftpd openssl` |

## Cross-cutting changes (all images)

- Pin base images **by digest** instead of fragile package versions.
- Add `.dockerignore` per build context. Currently copies `__pycache__`, `*.json~`,
  logs, sqlite, `amcrest-plugin.zip`, `npmedia.bundle` into the pano image, which is
  wasteful and leaks data.
- Use `ENV key=value` form (fixes the LegacyKeyValueFormat warning).
- Use a `requirements.txt` with pinned versions instead of ad-hoc `pip install`; drop
  `pudb` from prod (dev-only target/stage).
- Keep UID/GID build-args and non-root `pano` user.
- Add `HEALTHCHECK` and compose `healthcheck`.
- Drop compose `version: '3'` (obsolete).
- Bump `IMAGE_TAG=rel002` so old images remain for rollback.

## Per-image steps

### pano

1. Rebase on `python:3.14-slim-trixie`; delete `add-apt-repository`/deadsnakes/
   `update-alternatives`/python3.7 lines. `python3` is already correct.
2. `apt-get install -y --no-install-recommends ffmpeg imagemagick sqlite3 tzdata
   ca-certificates` (add `nano` optional).
3. Create `pano/requirements.txt` (`dtutils`, `click`) and
   `pip install --no-cache-dir -r requirements.txt`.
4. **Verify `dtutils` on 3.14** - it is an old PyPI package used for `sec_to_str`.
   If it will not install, either vendor the one function (replace with
   `datetime.strftime`) or pin an older Python. This is the main unknown.
5. `.dockerignore` to exclude runtime data. Consider a multi-stage build if any wheels
   need compilers.
6. Build: `docker compose build pano`; recreate only pano.

### lighttpd

1. `FROM alpine:3.20`; remove `LIGHTTPD_VERSION` pin (let apk pick the matching
   version).
2. Keep `passwd.digest`, config COPYs, UID/GID user creation.
3. Fix `ENV` -> `ENV TZ=America/Los_Angeles`.
4. `start.sh` mounts are unchanged (paths preserved).

### vsftpd

1. Prefer `almalinux:9` for minimal change: swap `yum` -> `dnf`, same `/etc/vsftp`,
   `/usr/sbin/vsftpd` paths.
2. If choosing Debian instead: `start.sh` uses bashisms (`&>/dev/null`, `[[ ]]`) with
   `#!/bin/sh` (dash) - must change shebang to `#!/bin/bash` or POSIX-ify, and paths
   may differ.
3. Note: TLS cert perms are `755` - tighten to `600` while here.

## Sequencing & verification

1. Merge config-volumes fix (bind-mount `pano-docker.json`) if you want 21 days to
   survive recreation before the rebuild lands.
2. pano: build -> `docker compose up -d pano` -> check `pano.log` for
   `max_age_days = 21.0`, camera page loads, a new FTP image gets slurped/derived.
3. lighttpd: build -> up -> verify auth + camera page assets over :8080.
4. vsftpd: build -> up -> upload a test file over FTP and confirm pano picks it up.
5. Keep old `rel001` images tagged until all three pass.

## Rollback

- Revert `IMAGE_TAG=rel001` and `docker compose up -d`; images still present.
- Old Dockerfiles remain in git history.

## Decisions needed

1. Python target: **3.14** (per AGENTS) with possible `dtutils` fallback to 3.13?
2. vsftpd base: **almalinux:9** (less churn) or **debian:trixie-slim** (consistent
   with pano)?
3. Include the config bind-mount so retention persists now, or wait for the full pano
   rebuild?
