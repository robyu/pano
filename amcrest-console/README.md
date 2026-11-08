# Amcrest console

A small, LAN-accessible web console for one Amcrest/Dahua camera. It replaces
the old NPAPI browser plugin for the parts pano needs: viewing a snapshot and
(in later phases) editing the motion mask and config.

Phase 1 provides browser login, an in-memory session, and snapshot proxying.
Phase 2 adds the legacy motion-mask editor and a per-camera JSON configuration
mirror. Phase 3 adds the Configuration tab: sanitized raw views, schema-driven
forms, verified read-modify-write, and pre-write backups.

## Requirements

- Python 3.7+ (stdlib only; no pip installs)
- A reachable camera on the local network

## Run

```bash
cd amcrest-console
python3 console.py --camera-ip 192.168.2.121 --name cam-01 --model amcrest-ip2m-842
```

The console binds `0.0.0.0:8765` by default and prints the URLs to open:

```text
Listening on 0.0.0.0:8765 (login required).
Open: http://192.168.2.5:8765/
Open: http://127.0.0.1:8765/
```

From any browser on the local network, open the LAN URL and sign in with the
camera username/password. No URL token or SSH tunnel is needed. Credentials are
kept in the proxy's memory only; they are never written to disk, the URL, the
cookie, or the page source.

Use `--bind 127.0.0.1` to restrict access to the local machine.

Useful options:

- `--camera-port` — camera HTTP port (default 80)
- `--port` — console port (default 8765)
- `--bind` — bind address (default `0.0.0.0`; `127.0.0.1` for local only)
- `--allow-host HOST[:PORT]` — extra accepted Host names (repeatable)
- `--auth {auto,basic,digest}` — default `auto` (model-based, then challenge)
- `--request-delay` — seconds between camera requests (default 1.0 for IP2M-842)
- `--timeout` — camera request timeout (default 20s)
- `--state-dir` — mirror and log directory (default `amcrest-console/cameras/`)
- `--state-file` — explicit mirror file for this camera
- `--backup-dir` — pre-write backup directory (default `amcrest-console/backups/`)
- `--no-browser` — print the URL without opening a browser
- `--log-level {DEBUG,INFO,WARNING,ERROR}` — protocol log verbosity (default `INFO`)
- `--log-file PATH` — override the default per-camera log file

## Motion mask and JSON mirror

The console loads the camera's legacy `MotionDetect[0].Region[0..17]` mask,
draws it over the snapshot, and lets you paint or erase cells. Painted cells are
motion-sensitive (motion there triggers detection); unpainted cells are ignored.
Apply sends all 18 rows in one `setConfig` call, re-reads the mask, and only
reports success if
the camera returns exactly what was written. If the camera rejects the CGI
write (the IP2M-842 does), the console falls back to the camera's RPC2 web API
(`configManager.setConfig` with the full MotionDetect table) and still verifies
through CGI. The newer `MotionDetectWindow` model is displayed read-only and is
never written directly.

The UI has two tabs. **Legacy mask** is the editable view above. The **Region
masks** tab overlays all four `MotionDetectWindow` regions on the snapshot in
distinct colors and is read-only (no paint or apply controls). On the current
cameras only the first window has cells; the other three are empty, so their
legend entries show `0 cells`. Window rows are flipped horizontally for display
so the first region aligns with the legacy mask. A window whose grid cannot be
decoded (for example cam-05's 12-row variant) is listed as
`region grid unavailable`.

One JSON file per camera is kept in `cameras/<name>.json` (or the IP when no
`--name` is given). The camera is the source of truth: the file is updated
after every successful read and every verified write. If the camera is
unreachable, the last mirror is shown marked stale and Apply is disabled.
Secret-looking keys are redacted before anything is written, and mirrors are
mode 0600. `cameras/` is gitignored.

## Configuration

The **Configuration** view lists the allowlisted sections (`General`,
`Network`, `NAS`, `NTP`, `Encode`, `AutoMaintain`, `MotionDetect`) and shows
sanitized raw JSON for each. `General` is read-only. The other sections have
schema-driven forms; only fields declared in `schemas.py` are writable. Unknown
firmware keys remain visible in the raw viewer but cannot be changed.

Apply re-reads the live section, checks the section revision, sends only changed
keys, then re-reads and verifies every key. A stale revision returns 409; a
verification mismatch returns 502 with expected/actual values and does not
update the mirror. `MotionDetect` in the Configuration view edits only `Enable`
and `Level`; the 18x22 mask is still edited in the Legacy mask tab, and window
models remain read-only.

`Network` and `NAS` are marked dangerous and require the typed confirmation
phrase shown in the UI. Before either write, the console reads all allowlisted
sections and writes a complete sanitized backup under `amcrest-console/backups/`
(mode 0600, gitignored). Network address changes can disconnect the camera; the
console reports the write as unverified and marks the mirror stale. Restart it
with the new `--camera-ip` if needed.

**Download backup** writes a sanitized full JSON snapshot with
`Content-Disposition: attachment`. If a section cannot be read live, the
download is marked `complete: false` and may use the last mirror for that
section. Passwords are stored as `<redacted>` in mirrors and backups; restore
must re-enter them.

## Logging and diagnostics

Logs are written at `INFO` by default to `cameras/log-<name>.log` (or
`cameras/log-<ip>.log` when `--name` is omitted), inside `--state-dir` if one is
given. The file is appended to and mode 0600. `--log-file` overrides the
destination. For protocol debugging, raise the level:

```bash
python3 console.py --camera-ip 192.168.2.121 --name cam-01 \
  --model amcrest-ip2m-842 --no-browser --log-level DEBUG
```

`INFO` logs request/response summaries (URL, HTTP status, bytes, duration),
configuration key counts, RPC2 login steps, CGI motion-write responses, and
verification results. `DEBUG` also includes sanitized request parameters and
payload previews. Passwords, session IDs, and cookies are redacted before
logging. Server-side request logs include the API route but never credentials.

Useful checks when a write fails:

```bash
rg -n "RPC2 login|CGI motion write|motion write verification|backoff|auth" \
  cameras/log-cam-01.log
```

## Network access

The console is reachable from the LAN by default. For off-LAN access, either
keep the LAN bind and forward the port over SSH:

```bash
ssh -L 8765:127.0.0.1:8765 ryu@chuyu-server.local
# then browse http://127.0.0.1:8765/
```

or run with `--bind 127.0.0.1` and tunnel to it. If the console is unreachable
from another host, allow TCP 8765 in the server firewall.

## Security model

- LAN bind (`0.0.0.0`) with camera login as the only access gate. Only one
  browser may be signed in at a time; a new login replaces the previous session.
- `Host` must be a local IP literal, `localhost`, or an explicit `--allow-host`
  name; private/link-local IP literals are accepted on the console port. This
  blocks DNS rebinding. `Origin` must match `Host` for writes, blocking
  cross-origin requests.
- Session cookie is random, `HttpOnly`, `SameSite=Strict`, and scoped to `Path=/`.
- Failed logins are delayed per source address to reduce camera lockout churn.
- The console speaks plain HTTP. The camera password crosses the LAN in clear
  text, so use a trusted network/VLAN. There is no TLS yet.
- Only allowlisted camera CGI endpoints are proxied; the camera host is fixed by
  `--camera-ip`.
- Camera requests are serialized and throttled; the IP2M-842 is slow and
  single-connection, and `getSoftwareVersion` crashes its web server.
- Motion writes require the browser session, a matching stale-check revision,
  explicit confirmation, and a successful re-read.
- Mirrors and pre-write backups are written atomically, mode 0600, with
  secret-looking keys redacted. Backups are sanitized, so restore must re-enter
  passwords.

## Troubleshooting

- `camera rejected motion write: error`: the IP2M-842 rejects CGI
  `MotionDetect` writes. The console retries through RPC2 automatically.
- `invalid RPC2 JSON ... <!DOCTYPE html>`: the camera redirected `/RPC2` to its
  login page. RPC2 requires a `DhWebClientSessionID=<session>` cookie, which
  this firmware never sends via `Set-Cookie`; the client sets it from the login
  session. If it recurs, the camera may have invalidated the session.
- `RPC2 login failed: PasswordNotValid`: the camera's RPC2/web password may
  differ from the CGI password, or the account is in a login lockout. cam-01's
  `General.LoginFailLockTime` is 1800 seconds (30 minutes). Stop retrying until
  it expires; each failed attempt can extend it.
- The camera config `General` section has `LockLoginEnable`, `LockLoginTimes`,
  `LoginFailLockTime`, and `LoginFailLoginTime` if you need to adjust this.
  Note: `LockLogin*` settings are not available via the camera's web UI; set
  them through the config API (`configManager.setConfig`) instead.

## Tests

```bash
cd amcrest-console
python3 -m unittest discover -s tests
```

The suite is mock-only: every test binds an ephemeral `127.0.0.1` server. No
test reads `--camera-ip`/`AMCREST_*` or contacts a real camera. Live writes are
manual acceptance steps and need explicit approval.

## Phase 0 discovery

`discover.py` is the read-only discovery tool used to learn the camera CGI
behavior. See `../agent-files/amcrest-console-plan.md` for findings and the
remaining phases.
