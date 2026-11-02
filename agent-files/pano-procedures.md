---
update: 2026-11-01 16:30 PST
tags: pano, procedures, config
---

# pano procedures

> NOTE (2026-10-31): Docker commands below are historical (imported from the log).
> Current scripts use the Compose v2 plugin: `./docker-compose-up.sh`,
> `./docker-compose-down.sh`, `./docker-compose-build.sh`. v1 `docker-compose` is EOL.

Imported from the **text** of `~/pano-log.pdf`. Step-by-step operational procedures
recorded there. Credentials omitted.

## Add a new camera / modify pano JSON (2022.02.26)

1. Set up the camera IP addresses and its FTP destination (see below).
2. Stop the dockers:
   ```
   cd 2020/pano-docker/pano
   docker-compose stop
   ```
3. Edit `pano-docker.json` to add the new camera. The `"name"` field must **exactly
   match** the FTP destination directory on the server.
4. Validate the JSON:
   ```
   cat pano-docker.json | python -m json.tool
   ```
5. Rebuild and restart the dockers:
   ```
   cd ..              # to pano-docker
   ./docker-compose-up.sh
   ```
   (Open question in the doc: do you need to delete the old docker image?)
6. Verify the dockers are actually running (not restarting continuously):
   ```
   docker ps
   ```
   Expect pano, vsftpd, and lighttpd all "Up".
7. Open a browser at `http://localhost:8080` and confirm the new camera appears in the
   index table.
8. `git` stage/commit/push the changes.

> Note: an invalid JSON silently produces no new web page; it can take hours before you
> notice. Always validate with `python -m json.tool`.

## pano-docker.json conventions

- **Keys beginning with `@` are comments.** `pano/panoconfig.py:122` deletes any
  top-level key whose first character is `@` before merging defaults, and
  `panoconfig.py:128` skips `@` keys in the defaults dict. Example in
  `pano/pano-docker.json`: `"@camera_list"` is a commented-out/example list; only
  `"camera_list"` is read.
- JSON itself has no comments, so use this `@` prefix instead of `//` or `#`.
- The convention is applied by pano's config loader, **not** by generic JSON tooling;
  scripts that read the file directly (e.g. `amcrest-console/discover.py`) do not strip
  `@` keys automatically.
- Since `@` keys are top-level-only, do not put comment keys inside camera objects.

## Configure the camera's FTP destination

In the camera web UI: Storage > Destination > FTP. Enable FTP; server address
`192.168.2.8`, port `21`, the upload account (creds omitted), and set **Remote
Directory** to the camera name (e.g. `cam-07`). See `amcrest-cameras-from-log.md` for
the firmware "Test button fails" bug — uploads still work.

## Set up networking on a new camera (2022.02.03)

1. In the Google Home app, reserve the wireless IP. **First unplug the Ethernet cable**
   so only the wireless interface shows up. (The wired entry may still appear in the
   reservation list even if offline; the WiFi interface seems to be the lower MAC.)
2. After assigning the reserved IP, reboot the camera.
3. Connect to the camera (via old Safari or Firefox 51) and log in.
4. Network > TCP/IP:
   - Set Host Name.
   - Ethernet Card > Wireless, click **Set as Default**; copy the MAC to the spreadsheet.
   - Ethernet Card > Wired, click **Static**, set the IP Address; copy the MAC.
   - Save.

## Get a camera serial number (for Google Home) via the Amcrest app

See the onboarding flow in `amcrest-cameras-from-log.md` (Device Manager → add device →
details page shows the S/N).

## Open a bash shell in a running container

```
docker exec -it pano-docker_pano_1 bash
```

## Start / stop the pano dockers (2021.04.09, 2021.05.30)

- Start (wrapped in a script because it needs env vars during build/deploy):
  ```
  ./docker-compose-up.sh
  ```
  or, on chuyu-server:
  ```
  cd ~/2020/pano-docker
  ./start-dockers.sh
  ```
- Stop:
  ```
  docker-compose down
  ```
- pano-docker auto-restarts after reboots.
- lighttpd is mapped to port **8080**; volumes (derived, FTP, logs, www) live under
  `/mnt/HD2/pano`.
- Logs for all three dockers: `/mnt/HD2/pano/logs`, e.g.
  ```
  tail -F /mnt/HD2/pano/logs/pano.log
  ```

## Debug: run pano attached (2021.04.04)

```
docker run -it -v /mnt/HD2/pano/www:/var/www -v /mnt/HD2/pano/FTP:/var/FTP \
  -v /mnt/HD2/pano/derived:/var/derived -v /mnt/HD2/pano/logs:/home/pano/logs \
  --name pano pano
```

## chuyu-server caveat (2022.02.03)

chuyu-server must boot in **desktop mode**, otherwise docker swarm does not start — a
problem after a power outage.

## Reset the derive_failed column (2021.03.30)

```
update pano
set derive_failed=0
where derive_failed=1
```

## www setup & permissions (2021.05.28, 2022.07.30)

- The `www` directory must be set up in a very specific way; this is now done by
  `pano/start-pano-docker.sh`. If it's wrong, the pano docker restart-loops.
- lighttpd must have the `FTP` and `derived` volumes mounted **and** the symlinks
  created inside the lighttpd container (it cannot serve the host-side symlinks
  directly).
- Historically the pano docker couldn't create symlinks due to permissions
  (`/var/FTP -> /var/www/FTP`).
