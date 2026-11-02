---
update: 2026-11-01 20:08 PST
tags: amcrest-console, camera-contact
---

# Amcrest camera contact results (2026-11-01)

Read-only contact/probe run from chuyu-server. No camera writes were made.
Credentials were read from `pano/pano-docker.json` and are not reproduced here.

## Summary: both interfaces

Addresses are from the camera table in `pano-log-overview.md`. "HTTP" means
TCP port 80 plus the CGI request. `RD` (used only in the earlier pre-fix
probes) = TCP connect succeeded but the client saw `RemoteDisconnected`.

| Camera | Model | Wi-Fi IP | Wi-Fi result | Wired IP | Wired result | iOS app |
|---|---|---|---|---|---|---|
| cam-00 | IP2M-842 | 192.168.2.120 | down | 192.168.2.130 | down | not shown |
| cam-01 | IP2M-842 | 192.168.2.121 | up; Basic CGI OK (preemptive) | 192.168.2.131 | down | live |
| cam-02 | IP2M-842 | 192.168.2.122 | down | 192.168.2.132 | down | not shown |
| cam-03 | IP2M-842 | 192.168.2.123 | up; Basic CGI OK (preemptive) | 192.168.2.133 | down | live |
| cam-04 | IP2M-842 | 192.168.2.124 | up; Basic CGI OK (preemptive) | 192.168.2.134 | up; Basic expected; retest | live |
| cam-05 | IP2M-842 | 192.168.2.125 | up; Basic CGI OK (preemptive) | 192.168.2.135 | down | live |
| cam-06 | IP2M-842 | 192.168.2.126 | up; Basic CGI OK (preemptive) | 192.168.2.136 | down | live |
| cam-07 | IP3M-943B | 192.168.2.127 | up; CGI OK | 192.168.2.137 | down | live |
| cam-08 | IP3M-943B | 192.168.2.128 | up; CGI OK | 192.168.2.138 | up; CGI OK | live |
| cam-09 | IP3M-943B | 192.168.2.129 | up; CGI OK | 192.168.2.139 | up earlier, down at second probe | live |
| cam-10 | IP3M? | 192.168.2.119 | down | 192.168.2.140 | down | not shown |
| cam-11 | IP3M? | 192.168.2.118 | down | 192.168.2.141 | down | not shown |

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
