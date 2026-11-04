---
title: Amcrest/Dahua RPC2 API (reverse-engineered)
update: 2026-11-03 18:59 PST
tags: amcrest, dahua, rpc2, api, motion-mask
---

# Amcrest/Dahua RPC2 API

RPC2 is the JSON API used by the camera's own web UI. It is **not** described
in `amcrest-support/amcrest-ip2m-842b-docs/AMCREST_CGI_SDK_API.pdf`; that PDF
documents only the CGI interface. Everything below was read from the camera's
served JavaScript and probed against cam-01 (IP2M-842, fw 2.212.0000.2.R).

Status: implemented as a fallback in `amcrest-console/camera.py`. The CGI
rejection is confirmed. RPC2 login now uses the camera's uppercase MD5 variant;
a live motion write still needs re-testing after the 2026-11-03 lockout window.

## Sources (camera web UI)

Fetched read-only from `http://192.168.2.121/`:

* `jsCore/rpcCore.js` — request wrapper, session handling, `sendRequest`
* `jsCore/rpcLogin.js` — `RPCLogin.login` handshake and error mapping
* `jsCore/md5.js` — `hex_md5` used by the handshake (returns uppercase hex)
* `js/set.js` — web UI settings pages, `ConfigManager` wrapper
* `index.html` — page shell and settings menu

The UI's own login form and settings pages drive these endpoints. No plugin or
SDK layer is involved for configuration; the NPAPI plugin is only for video.

## Transport

* Endpoints: `POST /RPC2_Login` and `POST /RPC2` on port 80.
* Body: JSON (`Content-Type: application/json`, `X-Request: JSON`).
* Session: returned as `session` in JSON and also written by the UI as the
  cookie `DhWebClientSessionID=<session>` (`path=/`, session cookie).
* The camera answers HTTP 200 even for login failures; check `result` and
  `error.code` in the body.
* Failed RPC2 logins appear to count toward the same account lockout as CGI:
  after repeated RPC2 failures on 2026-11-03, CGI Basic also returned 401.

## Login handshake

1. First request sends no password:

   ```json
   {"method":"global.login","params":{"userName":"admin","password":"","clientType":"Web3.0"},"id":10000}
   ```

   The camera replies with `result:false`, `error.code:401`, a `session` id, and
   `params.encryption`, `params.realm`, `params.random`. It may also set
   `DhWebClientSessionID`.

2. Build the password according to `params.encryption`:

   * `Default` (seen on IP2M-842):
     `h1 = MD5(user + ":" + realm + ":" + password)`
     `h2 = MD5(user + ":" + random + ":" + h1)`
     send `h2` as the password.
   * `Basic`: send `Base64(user + ":" + password)`.
   * `WatchNet`: the UI adds 3 to each character code of the username and sends
     the plain password.
   * anything else: send the plain password.

3. Second request reuses the returned session:

   ```json
   {"method":"global.login","session":<session>,"params":{"userName":"admin","password":"<h2>","clientType":"Web3.0"},"id":10000}
   ```

   Success is `result:true` and a new session id. Failure returns
   `params.error`: `PasswordNotValid`, `UserNotValid`, `HasBeenLocked`,
   `InBlackList`, or `HasBeedUsed` (the UI's spelling).

## Calls

Generic envelope:

```json
{"method":"<name>","params":{...},"session":<session>,"id":<n>}
```

Responses are `{"result":true,"params":{...},"id":<n>,"session":<session>}` or
`{"result":false,"error":{"code":...,"message":"..."},"id":<n>}`.

Configuration methods used by the UI:

* `configManager.getConfig` — params `{"name":"MotionDetect"}`; returns
  `params.table`.
* `configManager.setConfig` — params
  `{"name":"MotionDetect","table":<table>,"options":""}`. The table uses the
  same nested structure as CGI keys: `table.MotionDetect[0].Region[0..17]`,
  `table.MotionDetect[0].Enable`, etc. Send the whole table.
* `system.multicall` — params is an array of request strings; the UI batches
  multiple `getConfig`/`setConfig` calls this way. Not needed for one config.
* `system.listMethod` — returns supported method names (useful for discovery).

The camera's UI also uses `configManager.getDefault`, `system.listService`,
`global.getCurrentTime`, etc. (`jsCore/rpcCore.js`, `js/set.js`).

## CGI vs RPC2 on the IP2M-842

* CGI reads work: `GET /cgi-bin/configManager.cgi?action=getConfig&name=MotionDetect`.
* CGI writes fail for MotionDetect: `action=setConfig` with all 18 legacy
  `Region` rows returns the body `Error` (HTTP 200), even when unchanged; the
  same parameters sent as a POST return HTTP 500. Window `MotionDetectWindow`
  writes also return `Error`.
* The web UI uses RPC2 for settings, so RPC2 is the plausible write path. The
  fallback sends the full MotionDetect table through
  `configManager.setConfig`, then verifies by re-reading via CGI.

## Open questions / risks

* **Login hash case (resolved 2026-11-03).** RPC2 login returned
  `PasswordNotValid` for credentials that worked with CGI Basic. Root cause:
  the camera's `jsCore/md5.js` returns **uppercase** hex
  (`.toUpperCase()`), and the firmware compares it exactly. `camera.py` now
  uppercases both `h1` and `h2` via `rpc_default_password`. Repeated failures
  before the fix may have started the 1800 s lockout; wait it out if
  `PasswordNotValid` persists.
* **`LockLogin*` settings not in UI.** The web interface does not expose
  `LockLoginEnable`, `LockLoginTimes`, `LoginFailLockTime`, or
  `LoginFailLoginTime`. They exist in the `General` config and must be set via
  `configManager.setConfig` (RPC2) or the CGI `setConfig` call.
* **Cookie requirement (resolved 2026-11-03).** `/RPC2` requires a
  `DhWebClientSessionID` cookie whose value is the login `session`, but the
  camera **never sends `Set-Cookie`**. Its web UI sets the cookie client-side in
  `jsCore/rpcLogin.js` after the 401 challenge:
  `Cookie.write("DhWebClientSessionID", session, {path:"/"})`. The JSON `session`
  field alone is not enough: without the cookie `POST /RPC2` returns
  `301 Location: /` and the client follows the redirect to the web-UI HTML
  page, surfacing as `invalid RPC2 JSON ... <!DOCTYPE html>` (and
  `PUT /api/motion` -> 502). `camera.py` now sends
  `Cookie: DhWebClientSessionID=<session>` explicitly on non-login `/RPC2`
  calls (a cookie jar alone does not help). Verified against cam-03:
  `configManager.getConfig` and `configManager.setConfig` both succeed.
  Regression symptom: login succeeds, first `/RPC2` call returns HTML, 502.
* **Field coverage.** Only `MotionDetect` is exercised. Other config sections
  should use the same envelope; verify each table's JSON shape against CGI.
* **Firmware variance.** The handshake and error strings come from the IP2M-842
  UI; IP3M-943B may differ. Test before relying on RPC2 there.

## Cross-check against H3xano/dahua-rpc-api

Compared 2026-11-03 with <https://github.com/H3xano/dahua-rpc-api> (README and
`reference/dahua_rpc_client.py`).

Matches:

* Endpoints `/RPC2_Login` and `/RPC2`; POST with `Content-Type: application/json`.
* Payload envelope `method`, `params`, `id`, `session`.
* Two-step login: empty password first, then `realm`/`random` challenge and
  `MD5(user:realm:pass)` -> `MD5(user:random:hash1)`.
* `Default` encryption formula and the `Basic` base64 alternative.
* `system.multicall` batching and `system.listMethod` discovery.

Differences / additions from our IP2M-842 firmware:

* Challenge error code: the repo says `268632079`; our camera returns
  `error.code: 401`. Treat the numeric code as firmware-dependent and branch on
  `result`/message instead.
* Hash case: the repo/reference client uses lowercase MD5 hex; this IP2M-842
  web UI's `hex_md5` returns uppercase and the firmware rejects the lowercase
  form with `PasswordNotValid`.
* The camera's `rpcLogin.js` also has a `WatchNet` mode (username characters
  shifted by +3, plain password); the repo's README lists only Basic/Default.
* The repo's sample Python client always uses the doubled-MD5 formula and
  ignores `params.encryption`; the camera UI branches on it. Our implementation
  branches (Basic/Default/WatchNet).
* The repo documents session keepalive (`global.keepAlive` ~60s), secure calls
  (`system.multiSec`, RSA/AES for PPPoE/DDNS/VPN/Email), and unauthenticated
  `/OutsideCmd`. We have not observed or tested these on the IP2M-842.
* The repo calls it "JSON-RPC 2.0", but the payloads shown (and ours) omit a
  `jsonrpc` field. It is Dahua's JSON-RPC-like variant.
* The repo's session handling relies on `requests.Session` cookies; our Python
  client sends the session in JSON only. Add `DhWebClientSessionID` if `/RPC2`
  rejects a valid login session.
* Method count (repo claims 275+) is unknown for this 2016 firmware; run
  `system.listMethod` after the lockout clears.

## Implementation pointers

* `amcrest-console/camera.py`: `rpc_default_password` (uppercase doubled MD5),
  `rpc_login`, `rpc_call`, `rpc_get_config`,
  `rpc_set_config`, `set_motion_via_rpc`, `write_motion_mask`.
* `amcrest-console/server.py`: motion apply calls `write_motion_mask`, which
  uses CGI first and falls back to RPC2 when the CGI body contains `error`.
* Tests mock both CGI and RPC2; they do not prove live camera behavior.
