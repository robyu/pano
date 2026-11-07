---
update: 2026-11-06 PST
tags: amcrest-console, implementation-plan, motion-mask, json-mirror
---

# Amcrest console implementation plan

Implements the decisions in `amcrest-modern-access.md`: a standalone,
LAN-accessible Python web console for camera Config + snapshot-based motion-mask
editing. No Docker, no desktop bundle, no live video in the MVP.

## Fixed decisions

* Target directory: `amcrest-console/` (created; phase 0 tool present).
* Single explicit camera target per process, supplied with `--camera-ip`.
* Python **stdlib only** (`urllib`, `http.server`, `json`, `argparse`, `ipaddress`,
  `getpass`) so it runs on the installed Python 3.7 and pano's Python 3.14.
* Bind `0.0.0.0` by default so any LAN browser can connect; `--bind 127.0.0.1`
  restores local-only access.
* Serve routes from `/`; no URL token. Camera login plus a single in-memory
  session is the access gate; one browser at a time.
* `Host` must be a local/allowlisted name and `Origin` must match `Host` for
  writes, preserving DNS-rebinding and cross-origin protection.
* Local proxy handles Digest **and** Basic auth server-side; the browser stays
  same-origin.
* Snapshot-only preview; no RTSP/MJPEG/HLS in MVP.
* Credentials are queried through a browser login screen and kept only in
  proxy memory; never command-line arguments, never logged, never written to
  disk.
* One JSON configuration mirror per camera under `amcrest-console/cameras/`.
  The camera remains authoritative; the mirror is updated after successful
  reads and verified writes, is marked stale when the camera is unreachable,
  and redacts secret-looking keys.

## Phase 0 findings (2026-11-01)

Discovery tool: `amcrest-console/discover.py`; tests: `amcrest-console/tests/`
(13 passing). cam-09 (`192.168.2.129`) is an **IP3M-943B**, firmware
`2.400.AC02.15.R,build:2017-07-31`, using **Digest** auth. cam-01
(`192.168.2.121`) is an **IP2M-842** using **Basic** auth.

The pano-config credential (`admin` + stored password) is **correct**. The
earlier `RemoteDisconnected` failures were caused by the client's combined
Digest+Basic `urllib` opener, not bad credentials. The client now selects Basic
explicitly or Digest per `401` challenge. The IP2M-842 HTTP server is also slow
and single-connection, so rapid multi-request probes can still reset it; use
one request at a time and a long timeout.

**Config section names**

* Valid and used: `General`, `Network`, `NAS`, `NTP`, `Encode`, `AutoMaintain`,
  `MotionDetect`.
* `FTP` and `System` are **invalid** on this firmware (`ErrorID=5`). The FTP
  upload target is under **`NAS`** (`NAS[0].Address`, `Directory`, `Password`,
  `UserName`, `Protocol=FTP`, ...).
* Snapshot: `2304x1296`, ~610 KB JPEG from `snapshot.cgi?channel=0`.

**Motion mask**

* Firmware reports both the legacy 18x22 `MotionDetect[0].Region[0..17]` and
  four `MotionDetectWindow[0..3]` windows.
* Legacy `Region` is writable. **All 18 rows must be sent in one `setConfig`
  call**; a single-row write resets the omitted rows to all-monitored
  (`0x3FFFFF`). Verified by toggling `Region[0]` 0 -> 1 -> 0 and restoring the
  full original mask exactly.
* Bit order is **LSB = leftmost column**, matching the CGI PDF example.
* The 4-window model is **read-only in practice**: writing
  `MotionDetectWindow[n].Region[...]` returns `OK` but does not persist.
  Writing `MotionDetectWindow[n].Window[...]` **resets the legacy mask**.
  Do not write the window model; read and display it only.
* A mixed request containing legacy and window fields is rejected
  (`ErrorID=2, Invalid Request!`).
* Final camera state after probing: legacy mask restored exactly. Window model
  differs from its pre-probe state (window 0 `Sensitive` 60 vs 86 and a few
  region bits; window 3 `Window` fields zeroed and rows 3-6 cleared). The
  pre-probe values are preserved in the 15:21 fixture. Leave the window model
  alone; the old plugin uses the legacy mask.
* **cam-01 (IP2M-842) mask:** legacy `Region` and `MotionDetectWindow[0]` are
  exact horizontal mirrors. Legacy has the unmonitored strip on the left;
  window 0 has it on the right. The old UI uses legacy. Window 0 is named
  `Region0`, sensitive 60, threshold 5; windows 1-3 are empty.
* cam-01 legacy values:
  `[4194303,4194303,4194291,4194291,4194291,4194289,4194289,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288,4194288]`
  (56 unmonitored cells):

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

**Camera reachability, both interfaces (2026-11-01 15:56 PST)**

`RD` = TCP 80 accepted then the camera closed the connection
(`RemoteDisconnected`). Wi-Fi/wired addresses are from
`pano-log-overview.md`; pano's config lists only one interface per camera.

| Camera | Model | Wi-Fi IP | Wi-Fi result | Wired IP | Wired result | iOS app |
|---|---|---|---|---|---|---|
| cam-00 | IP2M-842 | 192.168.2.120 | down | 192.168.2.130 | down | not shown |
| cam-01 | IP2M-842 | 192.168.2.121 | up; Basic CGI OK; slow/fragile | 192.168.2.131 | down | live |
| cam-02 | IP2M-842 | 192.168.2.122 | down | 192.168.2.132 | down | not shown |
| cam-03 | IP2M-842 | 192.168.2.123 | up; Basic expected; retest after auth fix | 192.168.2.133 | down | live |
| cam-04 | IP2M-842 | 192.168.2.124 | up; Basic expected; retest after auth fix | 192.168.2.134 | up; Basic expected; retest | live |
| cam-05 | IP2M-842 | 192.168.2.125 | up; Basic expected; retest after auth fix | 192.168.2.135 | down | live |
| cam-06 | IP2M-842 | 192.168.2.126 | up; Basic expected; retest after auth fix | 192.168.2.136 | down | live |
| cam-07 | IP3M-943B | 192.168.2.127 | CGI OK | 192.168.2.137 | down | live |
| cam-08 | IP3M-943B | 192.168.2.128 | CGI OK | 192.168.2.138 | CGI OK | live |
| cam-09 | IP3M-943B | 192.168.2.129 | CGI OK | 192.168.2.139 | up earlier, down now | live |
| cam-10 | IP3M? | 192.168.2.119 | down | 192.168.2.140 | down | not shown |
| cam-11 | IP3M? | 192.168.2.118 | down | 192.168.2.141 | down | not shown |

Full probe details, ARP table, and next steps: `amcrest-camera-contact.md`.

The iOS app reports live streaming for cam-01/03/04/05/06/07/08/09, so the
IP2M-842 units are online. The app uses P2P/cloud and does not prove local HTTP
reachability. Their active Wi-Fi interfaces are up; their wired interfaces are
mostly down (cam-04 is the exception).

The earlier "TCP accepted then closed" behavior was the **client's combined
Digest+Basic opener**, not the camera. With explicit Basic auth, cam-01 returns
`200` for `magicBox.cgi` and the full `MotionDetect` config. The IP2M-842 HTTP
server is nevertheless slow and single-connection: rapid multi-request probes
can still reset or refuse it. Use one request at a time, a long timeout, and
stop the P2P stream if a request hangs. `LoginFailLockTime=300` on the tested
IP3M-943 firmware.

**Current API status (after auth fix):** cam-01 CGI works with explicit Basic;
cam-07/08/09 work with Digest; cam-03/04/05/06 are reachable on Wi-Fi but need a
retest with the fixed client; cam-00/02/10/11 are down or inactive. See
`amcrest-camera-contact.md`.

**Fixtures**

* `amcrest-console/fixtures/cam-09-192.168.2.129/20261101-152151/` contains the
  pre-probe sanitized configs, mask JSON/ASCII, and snapshot.
* cam-01 mask values and the legacy/window mirror finding are recorded in
  `amcrest-camera-contact.md`; no cam-01 fixture was saved.
* `.gitignore` excludes `amcrest-console/fixtures/`; snapshots and camera
  configs stay local.

**Implementation consequences**

* Use legacy `Region` for the mask editor and always write all 18 rows.
* **IP2M-842 CGI writes are rejected.** On cam-01, both legacy
  `MotionDetect[0].Region[...]` and `MotionDetect[0].MotionDetectWindow[0].Region[...]`
  `setConfig` calls return `Error` over `configManager.cgi` (verified
  2026-11-03). The camera's web API is RPC2 (`/RPC2_Login` + `/RPC2`
  `configManager.setConfig` with the full MotionDetect table), so the console
  falls back to RPC2 when the CGI write is rejected. The CGI read path still
  works and is used for verification.
* Read-only display of the window model is fine; hide or disable window writes.
* Verified 2026-11-06 on all eight online cameras: only
  `MotionDetectWindow[0]` has cells (it mirrors the legacy mask); windows 1-3
  are empty and their `Sensitive` values are inert. The edited legacy mask is
  therefore the operative mask. Details and live counts:
  `amcrest-camera-contact.md` (Motion mask / window model).
* **cam-05 12-row anomaly:** cam-05 returns only 12 `Region` rows, so
  `parse_mask` (which requires 18) reports `legacy=None` and the console cannot
  read/edit its mask. Needs a parser fix before cam-05 is editable.
* Query credentials through the browser login screen; keep them in memory only.
* Use explicit Basic auth or a separate Digest opener; never combine both in one
  opener.
* Be gentle with IP2M-842: one request at a time, long timeout, backoff.
* `discover.py --verify-mask-write --yes` performs the full 18-row toggle and
  restore; it never writes the window model. The tool now handles Basic and
  Digest explicitly, but still makes several identity requests; do not use it
  as a rapid poller on a fragile camera.
* Prefer `General` over `System` and `NAS` over `FTP`.

## Per-camera JSON mirror

Implemented in phase 2 (`amcrest-console/state.py`). One file per camera:
`amcrest-console/cameras/<slug>.json`, where the slug comes from `--name` or
falls back to the camera IP. `--state-dir` and `--state-file` override the
location; `cameras/` is gitignored. Protocol logs share the directory as
`log-<slug>.log` (appended, mode 0600); `--log-file` overrides the destination.
`--state-file` moves only the JSON mirror, not the log.

* `schema_version: 1` so later sections can be added under `configuration`
  without breaking old files.
* `camera` holds name/host/port/model/firmware; `configuration` currently holds
  `MotionDetect` (legacy `region_values`, decoded `rows`, `revision`, plus the
  read-only windows); `mirror` holds `updated`, `last_apply`, `verified`, and
  `stale`.
* The camera is the source of truth. The mirror is written after every
  successful read and every verified write, never updated when verification
  fails, and served marked `stale: true` (Apply disabled) when the camera is
  unreachable.
* Writes are atomic (temp file + `os.replace`), mode 0600, serialized with an
  advisory lock, and sanitized with `camera.sanitize` so secret-looking keys are
  stored as `<redacted>`. Camera login credentials and session tokens are never
  stored.
* A corrupt or unsupported mirror is renamed to `<file>.bad-<timestamp>` and
  rebuilt from the camera rather than crashing.

## Command-line interface

```bash
python3 console.py --camera-ip 192.168.2.120 \
  [--name cam-00] \
  [--user admin] \
  [--camera-port 80] \
  [--port 8765] \
  [--no-browser]
```

* `--camera-ip` — **required**; validated with `ipaddress.ip_address`.
* `--name` — optional display/backup label; defaults to the IP.
* `--user` — optional username prefill for the browser login screen; default
  `admin`.
* `--camera-port` — camera HTTP port; default `80`.
* `--port` — local console port; default `8765`.
* `--no-browser` — print the URL without opening a browser.
* `--state-dir` — mirror and log directory; default `amcrest-console/cameras/`.
* `--state-file` — explicit mirror file for this camera, overriding the
  derived per-camera path.
* `--log-level` — `DEBUG`, `INFO`, `WARNING`, or `ERROR`; default `INFO`.
* `--log-file` — override the default `<state-dir>/log-<slug>.log` path.

**Credential prompt:** the console does not ask for the password on the command
line. The first browser load shows a login screen with username (prefilled from
`--user`, default `admin`) and password. It posts to
`/api/login`; the proxy verifies the credentials with a harmless camera request
and keeps them **only in memory** for the session. Success sets a random
`HttpOnly`, `SameSite=Strict`, `Path=/` session cookie. A logout action clears
the cookie and in-memory credentials. A second login replaces the previous
session, so only one browser is active at a time. `AMCREST_PASSWORD` may remain
an optional noninteractive escape hatch, but the normal path is the browser
form. Never accept `--password`.

Startup prints LAN URLs, e.g. `http://192.168.2.5:8765/` and
`http://127.0.0.1:8765/`, and fails fast on a bad/missing IP or an unreachable
camera. Login errors are shown in the form.

## Network access

The console binds `0.0.0.0:8765` by default and is reachable from any browser on
the LAN; no token or SSH tunnel is needed. `--bind 127.0.0.1` restores
local-only access. Hostnames other than IP literals/`localhost` require
`--allow-host HOST[:PORT]`. For off-LAN access, forward the port over SSH:

```bash
ssh -L 8765:127.0.0.1:8765 ryu@chuyu-server.local
# then browse http://127.0.0.1:8765/
```

Traffic is plain HTTP on the LAN (the camera password is not encrypted in
transit), so use a trusted network/VLAN.

## Proposed layout

```text
amcrest-console/
  discover.py           # phase 0 discovery tool (implemented)
  console.py            # phase 1 CLI: argparse, startup, URL printing (implemented)
  server.py             # phase 1 ThreadingHTTPServer, login/session, static, Host/Origin checks (implemented)
  camera.py             # shared CGI client: explicit Basic + Digest, timeout, lock, backoff (implemented)
  static/index.html     # login, snapshot, motion editor UI (implemented)
  static/app.js         # login/snapshot/motion frontend logic (implemented)
  static/style.css      # styles (implemented)
  cgi_config.py         # phase 3 getConfig/setConfig parsing + read-modify-write
  mask.py               # phase 2 legacy 18x22 grid codec (implemented)
  state.py              # phase 2 per-camera JSON mirror (implemented)
  schemas.py            # phase 3 allowlisted config sections and form metadata
  cameras/              # per-camera JSON mirrors + log-<slug>.log, gitignored (runtime)
  cameras.example.json  # optional future multi-camera example; unused by MVP
  tests/test_discover.py  # phase 0 tests (implemented)
  tests/test_camera.py    # phase 1 client tests (implemented)
  tests/test_server.py    # phase 1+2 server tests (implemented)
  tests/test_mask.py      # phase 2 mask codec tests (implemented)
  tests/test_state.py     # phase 2 mirror tests (implemented)
  tests/test_console.py   # CLI logging destination tests (implemented)
  fixtures/             # local discovery output, gitignored
  README.md             # run steps, LAN access, security model (implemented)
```

## HTTP surface

Allowlist only these camera CGI endpoints:

* `/cgi-bin/snapshot.cgi` — JPEG backdrop.
* `/cgi-bin/configManager.cgi` — getConfig/setConfig.
* `/cgi-bin/magicBox.cgi` — firmware/device info for backup metadata.

Console routes (served from `/`):

* `GET /api/session` — whether the proxy has an authenticated in-memory session.
* `POST /api/login` — username/password from the browser form; verifies against
  the camera; sets an `HttpOnly`, `SameSite=Strict` session cookie.
* `POST /api/logout` — clears the session cookie and in-memory credentials.
* `GET /api/camera` — target name, model/firmware, mask model.
* `GET /api/snapshot` — proxied JPEG, `Cache-Control: no-store`.
* `GET /api/config?name=<Name>` — parsed config section.
* `POST /api/config` — apply only changed keys, read-modify-write, verify.
* `GET /api/motion` — parsed legacy mask, read-only windows, and mirror
  metadata; falls back to the last mirror marked `stale` when the camera is
  unreachable.
* `PUT /api/motion` — body `{rows, revision, confirm}`; rejects unknown fields,
  requires confirmation, verifies the revision against a fresh read, writes all
  18 legacy rows in one call, re-reads, and updates the mirror only on exact
  verification. Returns 409 on a stale revision and 502 on failed verification.
* `GET /api/state` — the per-camera JSON mirror (read-only).
* `GET /api/backup` — timestamped JSON dump.
* `POST /api/restore` — diff-only restore with confirmation.

No arbitrary URL proxying; the camera host is fixed by `--camera-ip`.

## Security model

* LAN bind (`0.0.0.0`) with camera login as the only access gate; no URL token.
  One in-memory session, so one browser at a time (a new login replaces it).
* `Host` must be a local IP literal, `localhost`, or an explicit
  `--allow-host` name; private/link-local IP literals are accepted on the
  console port. `Origin` must match `Host` for writes. This blocks DNS
  rebinding and cross-origin CSRF against the proxy.
* Plain HTTP on the LAN; the camera password is not encrypted in transit, so
  use a trusted network/VLAN. TLS is not implemented.
* Reject any path outside the allowlist before constructing a camera request.
* Browser login screen; credentials stay in proxy memory only. Never in the
  URL, cookie, localStorage, page source, or logs. Redact `Authorization`,
  `password`, and query strings.
* Session cookie is random, `HttpOnly`, `SameSite=Strict`, and `Path=/`;
  logout clears both the cookie and the in-memory credentials.
* Auth scheme is chosen per camera from the `401` challenge. Basic uses an
  explicit `Authorization: Basic` header; Digest uses a separate opener. Do
  not combine Digest and Basic handlers in one opener.
* Login failures are not auto-retried; a per-source delay (1-5 s) reduces
  camera login lockout churn.
* Be gentle with the IP2M-842: one camera request at a time, long timeout
  (20-30 s), backoff on reset/refusal, cache identity, and avoid rapid
  multi-request probes.
* Explicit confirmation in the UI for every write; no auto-apply.
* Mirrors are local state only: mode 0600, atomic writes with a per-file lock,
  and secret-looking keys redacted. Camera credentials and session tokens are
  never written to a mirror.

## Phases

**0. Discovery (done 2026-11-01; see findings above)**
* Confirmed camera reachability, firmware, and Digest/Basic auth.
* Fetched `General`, `NAS`, `Network`, `NTP`, `Encode`, `AutoMaintain`,
  `MotionDetect`; saved sanitized fixtures.
* Determined the legacy mask is the only safe writable model and verified
  LSB=leftmost with full-18-row round-trips.

**1. Server + snapshot (done 2026-11-01)**
* `console.py`, `server.py`, `camera.py`; static serving at `/`.
* Browser login screen and in-memory session; Basic/Digest per challenge.
* Long timeouts, one request at a time, backoff on reset/refusal.
* Snapshot endpoint and startup failure messages.
* Implemented: `camera.py` (shared client, lock, throttle/backoff, identity
  cache), `server.py` (Host/Origin checks, login/logout, session cookie,
  `/api/session`, `/api/camera`, `/api/snapshot`), `console.py` (CLI, LAN bind,
  reachability check, LAN URLs), `static/` UI, `README.md`.
* Tests: 43 passing (`test_discover.py` 24, `test_camera.py` 8,
  `test_server.py` 11). End-to-end smoke test with a mock camera passes.

**2. Mask editor + JSON mirror (done 2026-11-03)**
* `mask.py`: decode/encode legacy `Region[0..17]` (18 rows x 22 blocks; 32-bit
  ints; bit = monitored); validation, revision hash, invert/clear helpers;
  round-trip unit tests.
* Read and display `MotionDetectWindow[0..3]` as read-only information, never
  write it (phase 0 found window writes do not persist and reset legacy).
* SVG overlay scaled to the snapshot; paint/drag/erase/clear/invert/revert.
* Apply always sends all 18 legacy rows in one `setConfig`; re-reads and verifies
  the full mask before marking clean. Stale revisions return 409; verification
  mismatches return 502 with expected/actual.
* IP2M-842: when the CGI write returns `Error`, fall back to the RPC2
  `configManager.setConfig` path (full MotionDetect table) and verify via CGI.
  RPC2 login is cached per camera client.
* `state.py` maintains one JSON mirror per camera (atomic, 0600, locked,
  sanitized), updated on successful reads and verified writes, marked stale
  when the camera is unreachable.
* Implemented: `mask.py`, `state.py`, `GET /api/motion`, `PUT /api/motion`,
  `GET /api/state`, `--state-dir`/`--state-file`, motion editor UI, mirror/stale
  display.
* Diagnostics: `--log-level`/`--log-file`; structured protocol logs in
  `camera.py`/`server.py` (request/response summaries, RPC2 login steps, CGI
  writes, backoff, verification); secret redaction in log payloads; NullHandler
  keeps the library quiet when tests do not configure logging.
* Tests: mask codec, mirror atomicity/redaction/quarantine, motion auth,
  validation, stale revision, all-18-row writes, verification failure.
* Suite: 82 passing (`test_discover` 24, `test_camera` 9, `test_server` 26,
  `test_mask` 12, `test_state` 11).

**3. Config browser + forms (1–1.5 days)**
* Read-only raw viewer for each allowlisted section, then full JSON backup.
* Schema-driven forms for Network, NAS (FTP), Encode, NTP, AutoMaintain,
  MotionDetect.
* Apply changes only touched keys; re-fetch and verify.
* Extra warning and automatic backup before Network/NAS writes.

**4. Backup/restore + safety (0.5–1 day)**
* Pre-write backup to `amcrest-console/backups/<name>-<timestamp>.json`.
* Restore applies only differences, serializes writes with a short delay.
* Abort on missing/unexpected response fields.

**5. Optional live-stream spike (0.25–0.5 day)**
* Test `/cgi-bin/mjpg/video.cgi` in Safari. If it renders, add a separate
  non-critical panel; otherwise defer to ffmpeg→HLS or go2rtc. Never block
  phases 1–4.

**6. Hardening + docs (0.5 day)**
* Mock-camera tests for Digest, malformed CGI, and write ordering.
* Manual acceptance on one camera.
* `README.md`: run steps, macOS Local Network prompt, credential handling,
  troubleshooting, known CGI quirks.

Total: about 4–6 days without live streaming, plus discovery.

## Tests

* `mask.py` round-trip, LSB-leftmost, boundary, and invalid-shape tests for the
  legacy mask model.
* `state.py` tests: one file per camera, atomic writes, 0600 mode, redaction,
  corrupt-file quarantine, schema rejection.
* CGI key=value parser and serializer tests, including duplicate keys and
  malformed lines.
* Read-modify-write test proving unrelated keys are untouched.
* Mock Digest camera server for proxy/auth/failure tests.
* Host/Origin rejection tests, single-session replacement, and cookie path.
* One manual smoke test per release: snapshot, read config, toggle one mask
  cell, re-read, restore backup.

## Acceptance criteria

* Starts with the documented CLI and is reachable from LAN browsers (default
  `0.0.0.0`), with login required and one browser session at a time.
* Snapshot renders and refreshes on demand.
* Current mask loads, edits, applies, and verifies by re-read.
* Exactly one JSON mirror exists per camera; it matches the last successful
  camera read and is marked stale when the camera is unreachable.
* Secrets never appear in a mirror, and mirrors are mode 0600.
* Config sections load read-only; curated forms round-trip without touching
  unrelated keys.
* Backup/restore produces and consumes usable JSON.
* Browser login screen works; credentials are never written to disk or placed in
  the URL/cookie/localStorage/frontend source, and logout clears them.
* No credentials in shell history, process arguments, logs, or frontend source.
* Bad IP or unreachable camera fails clearly at startup; bad credentials are
  rejected by the login screen with a generic error.
* Legacy mask writes send all 18 rows; window-model writes are disabled.

## Risks and mitigations

* 2015-era firmware may differ from the CGI PDF → discovery phase and fixtures.
* Mask bit order/interpretation may be wrong → empirical round-trip before
  trusting the editor.
* Camera dislikes rapid reads and writes → one request at a time, long
  timeout, backoff, single-writer lock.
* macOS Local Network/TCC prompt may appear for Python → document it in README.
* Live streaming is the only large unknown → keep it out of the MVP.
