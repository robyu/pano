---
update: 2026-11-08 PST
tags: amcrest-console, camera-contact
---

# Amcrest camera contact results (2026-11-01)

Read-only contact/probe run from chuyu-server. No camera writes were made.
Credentials were read from `pano/pano-docker.json` and are not reproduced here.

## Summary: both interfaces (probe 2026-11-01, after the auth fix)

Camera identity (model, MACs, IPs, firmware, serial) lives in the inventory table in
`pano-cameras.md`; this file records the dated probe results only. "HTTP" means
TCP port 80 plus the CGI request. `RD` (used only in the earlier pre-fix probes) =
TCP connect succeeded but the client saw `RemoteDisconnected`.

| Camera | Wi-Fi result | Wired result | iOS app |
|---|---|---|---|
| cam-00 | down | down | not shown |
| cam-01 | up; Basic CGI OK (preemptive) | down | live |
| cam-02 | down | down | not shown |
| cam-03 | up; Basic CGI OK (preemptive) | down | live |
| cam-04 | up; Basic CGI OK (preemptive) | up; Basic expected; retest | live |
| cam-05 | up; Basic CGI OK (preemptive) | down | live |
| cam-06 | up; Basic CGI OK (preemptive) | down | live |
| cam-07 | up; CGI OK | down | live |
| cam-08 | up; CGI OK | up; CGI OK | live |
| cam-09 | up; CGI OK | up earlier, down at second probe | live |
| cam-10 | down | down | not shown |
| cam-11 | down | down | not shown |

The 2026-11-06 motion read (below) re-verified CGI on cam-01/03/05/06/07/09 (Wi-Fi) and
cam-04/08 (wired), which is what the `*` marks in the inventory table mean.

cam-02, cam-10, and cam-11 are not in the active pano config and are not shown
by the iOS app. The iOS app proves the IP2M-842 units are online; it uses
P2P/cloud, so it does not prove local HTTP reachability.

The important correction: the IP2M-842 units are not simply "unreachable". They
are reachable on their active Wi-Fi addresses, and port 80 accepts a connection;
their wired addresses are mostly down (cam-04 is the exception).

## Correction: credentials and auth (2026-11-01 16:20 PST)

The pano-config credential is **correct**: `admin` + the stored password. The
earlier `RemoteDisconnected` failures were caused by the discovery client's
combined Digest+Basic `urllib` opener, not stale credentials.

Explicit Basic auth works from chuyu-server:

* `magicBox.cgi?action=getMachineName` -> `200`, `name=AMC002A3_K2G7HH`
* `configManager.cgi?action=getConfig&name=MotionDetect` -> `200`, 11,832 bytes

The IP2M-842 web server is still slow and single-connection. Rapid
multi-request probes (three `magicBox` calls plus config calls) can crash/restart
or refuse it. Use one request at a time, a long timeout, and stop the P2P stream if
a request hangs.

## Reachable CGI cameras

CGI worked on cam-07 Wi-Fi, cam-08 Wi-Fi and wired, and cam-09 Wi-Fi:

* Model: `IP3M-943B`
* Firmware: `2.400.AC02.15.R,build:2017-07-31`
* Auth: HTTP Digest
* Motion model: legacy 18x22 `Region` plus four `MotionDetectWindow` entries
* Serial examples: cam-07 `AMC0184D_F01N44`, cam-08 `AMC018T1_F424P2`,
  cam-09 `AMC01861_172R3Q`

cam-09 wired (`192.168.2.139`) worked on the first probe but was down on the
second. cam-07 wired (`192.168.2.137`) was down. So the reachable path is not
always the one in `pano/pano-docker.json`; probe both.

## Auth schemes

* **Basic** (IP2M-842): `Authorization: Basic base64(user:password)`. The
  password is encoded, not encrypted; safe only on a trusted LAN or over HTTPS.
* **Digest** (IP3M-943): the server sends a nonce challenge; the client returns
  a hash response and does not send the password. Better against passive
  sniffing, but still not encryption and obsolete versus HTTPS.
* The console/proxy must support both explicitly and must never log the
  `Authorization` header or the password.

## IP2M-842 local HTTP behavior

cam-01 confirmed; cam-03, cam-04, cam-05, cam-06 are the same family and use
Basic auth:

* Respond to ping and are streaming to the iOS app.
* Wi-Fi addresses are up; wired addresses are down except cam-04.
* Basic auth works with the pano credential. cam-01 was verified with
  `magicBox.cgi` (200) and `configManager.cgi` `MotionDetect` (200, 11,832
  bytes).
* The web server is slow and single-connection. Rapid multi-request probes can
  crash/restart or refuse it. A port scan briefly found TCP **80, 554, 37777, 5000,
  49152** open (cam-06 also 23).
* The earlier `RemoteDisconnected` pattern was the client's combined
  Digest+Basic opener, not the camera. Use explicit Basic, one request at a
  time, long timeout, and backoff on connection reset/refusal.
* `LoginFailLockTime=300` on the tested IP3M-943 firmware; avoid repeated failed
  logins.

## API status (current, after auth fix)

* **Usable via local CGI:** cam-01 (explicit Basic); cam-07, cam-08, cam-09
  (Digest); cam-08 wired; cam-09 wired when up.
* **Needs retest with the fixed client:** cam-03, cam-04, cam-05, cam-06. They
  are reachable on Wi-Fi and should use Basic, but were not re-tested after the
  client fix.
* **Down / not active:** cam-00 (both interfaces), cam-02, cam-10, cam-11.
* The iOS app's live view is **P2P**, not CGI, so it does not prove or disprove
  local CGI reachability.

## cam-01 motion mask

`MotionDetect[0].Enable=true`, `Level=3`. The legacy mask is almost full-frame
monitored with a small unmonitored strip on the left:

```text
######################
######################
##..##################
##..##################
##..##################
#...##################
#...##################
....##################
....##################
....##################
....##################
....##################
....##################
....##################
....##################
....##################
....##################
....##################
```

Legacy values:

`[4194303,4194303,4194291,4194291,4194291,4194289,4194289,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288]`

`MotionDetectWindow[0]` is the exact horizontal mirror (unmonitored strip on
the right), named `Region0`, sensitive 60, threshold 5. Windows 1-3 are empty.
The old UI uses the legacy model; the window model is read-only/mirrored.

## ARP observed

| Address | MAC |
|---|---|
| 192.168.2.121 | 4c:11:bf:f5:89:a0 |
| 192.168.2.123 | 4c:11:bf:f4:48:91 |
| 192.168.2.124 | 3c:ef:8c:87:3c:2d |
| 192.168.2.125 | 3c:ef:8c:9c:87:86 |
| 192.168.2.126 | 3c:ef:8c:9c:83:43 |
| 192.168.2.127 | 9c:8e:cd:0d:2b:56 |
| 192.168.2.129 | 9c:8e:cd:12:f6:c6 |
| 192.168.2.138 | 9c:8e:cd:0d:36:a1 |

Some of these differ from older log-table MACs, which is expected across units
and eras.

## Preemptive Basic and login lockout (2026-11-01 16:45 PST)

The IP2M-842 counts an unauthenticated `/cgi-bin` request as a failed login.
The old `discover.py` sent that request first to discover the auth challenge, so
the camera locked the client out (~300s) before the Basic retry could run. A
preemptive `Authorization: Basic ...` on the first request works; verified on
cam-05 (`192.168.2.125`, `200 name=AMC0021A_837U12`). The camera web UI itself
uses RPC2 login (`/RPC2_Login`, `encryption=Default`), not HTTP Basic; RPC2 login
with the pano credential succeeds on cam-01 as well.

`discover.py` now:

* sends Basic **first** (no challenge request) for `amcrest-ip2m-842`
* uses Digest for `amcrest-ip3m-943`
* auto-detects the model from `--pano-config` (`camera_list` only; `@`-prefixed
  keys are comments and are skipped)
* defaults to a 1.0s delay between requests on IP2M-842
* reports the login-lockout hint on connection reset/refusal instead of retrying

After a lockout, stop probing and wait several minutes (observed: port closed
for ~3 min, then the web server can still drop the next request; the lockout
may restart on each probe). Then run once with `--sections General --no-snapshot`
before doing a full probe. If it still drops connections, wait longer or
power-cycle the camera; repeated attempts extend the lockout.

## getSoftwareVersion crashes/restarts the IP2M-842 web server (2026-11-01 17:15 PST)

`magicBox.cgi?action=getSoftwareVersion` crashes/restarts the IP2M-842 web
server. Verified on cam-05 (`192.168.2.125`): `getMachineName` returned `200`,
then `getSoftwareVersion` returned `RemoteDisconnected` and port 80 was closed.
`getMachineName` and `getDeviceType` are safe. `discover.py` now queries those
two first and skips `getSoftwareVersion` when the model/device type is IP2M-842
(or unknown); it still fetches it for IP3M-943.

This was the real cause of the earlier "connection reset/refused" wave: the old
script called `getSoftwareVersion` **first**, so every subsequent config and
snapshot request hit a camera whose web server had just crashed/restarted.

## cam-01 firmware/version (from built-in webpage, 2026-11-01)

Read from the camera's own web page at `192.168.2.121` (safe; the
`getSoftwareVersion` CGI is what crashes this model's server):

* Software Version: `2.212.0000.2.R`, build `2016-08-11`
* WEB Version: `3.2.1.273284`
* S/N: `AMC002A34HATK2G7HH` (matches the camera table / cam-01 P2P serial)

This is the first recorded IP2M-842 firmware version; previous docs only had
the IP3M-943B firmware (`2.400.AC02.15.R`, build 2017-07-31).

## Next steps

1. Use the fixed `discover.py`/console client, which sends Basic preemptively
   and handles Digest explicitly. The pano credential is correct.
2. Make one camera request at a time with a 20-30 s timeout. If a request hangs,
   stop the iOS P2P stream for that camera and retry.
3. Verified 2026-11-01: cam-01/03/04/05/06 (preemptive Basic, full discovery)
   and cam-07/08/09 (Digest, full discovery). All fixture sections and snapshots
   were written successfully.
4. If HTTP still misbehaves, check the app's device settings for the local
   IP/HTTP port and whether local HTTP is enabled.
5. Do not run any mask write test until HTTP auth succeeds and the connection is
   stable.

## Commands / tools

* `amcrest-console/discover.py` (read-only probe, Digest/Basic)
* TCP connect scan of the known camera IPs only
* `ip neigh show` for ARP confirmation

## IP2M-842 mask writes require RPC2 (2026-11-03)

Full protocol notes: `amcrest-rpc2-api.md`.

While fixing the console "apply mask" failure on cam-01, the CGI path was
verified to be read-only for motion configuration:

* `configManager.cgi?action=getConfig&name=MotionDetect` works with Basic auth.
* `action=setConfig` with all 18 legacy `Region` rows returns the body `Error`
  (HTTP 200), even when every value is unchanged.
* `action=setConfig` with all 18 `MotionDetectWindow[0].Region` rows also
  returns `Error`.
* POSTing the same `setConfig` parameters returns HTTP 500.
* The camera's own web UI uses RPC2 (`/RPC2_Login`, `/RPC2`,
  `configManager.setConfig` with the full MotionDetect table), so the console
  now falls back to RPC2 when the CGI write is rejected.

RPC2 login testing on 2026-11-03 returned `PasswordNotValid` for the pano
credential even though the same credential works for CGI Basic. Several failed
RPC2 attempts then made Basic return 401 as well, consistent with the camera's
short login lockout (`LoginFailLockTime=300`). Stop probing for at least five
minutes before retrying. If RPC2 login still fails after the lockout expires,
confirm that the camera's web UI accepts the same password (the web/ONVIF
account may be separate from the credential pano uses).

## Motion mask / window model (2026-11-06 live verification)

Read-only `configManager.cgi?action=getConfig&name=MotionDetect` against all
eight cameras in the active pano config. No writes were made.

Both firmware families expose two motion models:

* Legacy `MotionDetect[0].Region[0..17]`: 18x22 binary cells. A set bit means
  the cell is motion-sensitive/monitored; an unset bit means ignored.
* Four `MotionDetectWindow[0..3]`: each has `Region` rows, `Window` coordinates,
  `Sensitive` (0-100), and `Threshold`. IP2M-842 names them `Region0`-`Region3`;
  IP3M-943B names them `Region1`-`Region4`.
* Sensitivity is per window, not per cell. `MotionDetect[0].Level` and
  `PirMotionLevel` are global.

Observed structure:

* Only the first window (`MotionDetectWindow[0]`) has region cells, and it is
  the exact horizontal mirror of the legacy `Region` mask. The other three
  windows have zero region cells on every online camera.
* Empty windows still carry `Sensitive`/`Threshold` values (e.g. cam-09
  window[3] sensitive 94), but those values are inert without cells.
* Therefore the console-edited legacy mask is the operative mask, equivalent to
  the first window. Writing it does not disable or override windows 1-3; they
  are simply empty and left unchanged.
* After console writes, the first window again mirrors the new legacy mask
  (verified on cam-01/03/09), so the firmware keeps the two in sync.

Live cell counts (2026-11-06):

| Camera | Host | Legacy cells | Window[0] cells | Window[1..3] cells |
|---|---|---|---|---|
| cam-01 | 192.168.2.121 | 340 | 340 | 0 / 0 / 0 |
| cam-03 | 192.168.2.123 | 396 | 396 | 0 / 0 / 0 |
| cam-04 | 192.168.2.134 | 383 | 383 | 0 / 0 / 0 |
| cam-05 | 192.168.2.125 | 12-row variant (48) | 48 | 0 / 0 / 0 |
| cam-06 | 192.168.2.126 | 341 | 341 | 0 / 0 / 0 |
| cam-07 | 192.168.2.127 | 396 | 396 | 0 / 0 / 0 |
| cam-08 | 192.168.2.138 | 302 | 302 | 0 / 0 / 0 |
| cam-09 | 192.168.2.129 | 289 | 289 | 0 / 0 / 0 |

Cam-04 is reached at its wired address; cam-08 at its wired address. Live cell
counts differ slightly from the 2026-11-01 fixtures; the masks were edited
between probes, but the model structure is unchanged.

### cam-05 12-row anomaly

cam-05 returns only `Region` rows 0-11 for the legacy model and
`MotionDetectWindow[0]` (12 rows, not 18). Windows 1-3 return only
`Region[0]=0` with all-zero `Window` coordinates. Within those 12 rows, the
first window still mirrors the legacy mask (e.g. legacy rows 5-10 = 8128;
window[0] rows 5-10 = 65024).

This is persistent: both the 2026-11-01 fixture and the 2026-11-06 live read
show 12 rows. Impact: `camera.parse_mask`/`get_motion` require all 18 rows, so
cam-05 reports `legacy=None` and window regions `None`. The console cannot read
or edit cam-05's mask, even though the camera has one. A parser fix (accept a
12-row variant or derive the row count from the device) is needed before cam-05
is editable.

### Console write behavior (summary)

* Writes only legacy `Region`, always all 18 rows.
* IP3M-943B accepts the CGI write (`OK`) and verifies by re-read.
* IP2M-842 rejects CGI (`Error`); the RPC2 fallback fetches the full
  `MotionDetect` table, replaces only `table[0].Region`, and writes it back.
  Window `Sensitive`/`Threshold` are preserved, not edited.
* Per-window sensitivity is not settable through the console, and window-model
  writes are unreliable (non-persistent; `Window` writes can reset the legacy
  mask). See `amcrest-console-plan.md`.
