---
update: 2026-11-01 16:24 PST
tags: amcrest-console
---

# Modern replacement for the Amcrest browser plugin

Goal: on a modern **ARM Mac**, perform the functions the plugin was actually used
for — **Config** and **motion-detection mask editing**. Continuous live view is
**not required**: a still frame from `snapshot.cgi` is an adequate backdrop for
the mask grid. This supersedes the "old x86 Mac + Firefox 51 + NPMedia plugin"
procedure in `amcrest-plugin.md`.

Cameras are Dahua OEM (e.g. IP2M-842B); the CGI API is documented in
`amcrest-support/amcrest-ip2m-842b-docs/AMCREST_CGI_SDK_API.pdf`.

Implementation plan (CLI, file layout, phases, tests): `amcrest-console-plan.md`.

## Verdict on the original options

1. **Run the plugin in an emulated environment — dead end.** The plugin is
   32-bit i386 Mach-O with Cocoa NPAPI glue. Rosetta 2 does not support i386;
   the only host that can load it is x86 macOS, which under full QEMU emulation
   is unusably slow and lacks working Cocoa/GPU video. Not worth pursuing.
2. **Write a new client — the viable path.** No off-the-shelf Mac-native
   GUI edits camera-side motion masks (see below), so this is the realistic
   durable option.

## Why no vendor path remains

* **Amcrest Surveillance Pro / Dahua SmartPSS**: native but Windows-centric
  (older macOS build would run under Rosetta); treated as non-starters.
* **Amcrest View Pro (iOS)**: not updated in ~3 years — assume it stops working
  soon. It was also the last WiFi-onboarding path.
* **DahuaConsole** (https://github.com/mcw0/DahuaConsole, Python, MIT): excellent
  open-source Dahua tool, but a **CLI/JSON dump-restore console**, not a
  live-view GUI. Useful as a protocol reference and for config backup/restore.
* The plugin existed only to open the camera's own admin UI; `pano` itself never
  used it and is unaffected (it consumes FTP-uploaded JPEGs).

## Why a new client is small

The camera is fully driveable over **HTTP CGI**, independent of any Amcrest
software:

* Config: `GET /cgi-bin/configManager.cgi?action=getConfig&name=<Name>` and
  `action=setConfig&<param>=<value>`. Covers `Network`, `NAS` (FTP target),
  `Encode`, `NTP`, `AutoMaintain`, `MotionDetect`, etc. Auth is **HTTP Digest**
  or Basic depending on firmware (admin user).
* Mask backdrop: `/cgi-bin/snapshot.cgi` (still frame; no video pipeline needed).
* PTZ: `/cgi-bin/ptz.cgi` (only if ever needed).
* Optional future: `rtsp://<user>:<pass>@<ip>:554/cam/realmonitor?channel=1&subtype=<0|1>`
  if a live preview is ever wanted — deliberately out of scope now.

**Key insight:** the motion mask is just a bit grid, so a still snapshot is fully
equivalent to the plugin's live view for setting masks. Dropping live video
removes the RTSP/decoder/webview-video complexity from the app entirely.

## Motion mask data model (CGI PDF §6.3)

* Legacy: `MotionDetect[ch].Region[0..17]` — 18 lines, 22 blocks/line; each line
  is a 32-bit int, bit = 1 means that block is monitored.
* Newer (firmware >= 2.212): `MotionDetect[ch].MotionDetectWindow[n]` (n = 0..3)
  with `Id`, `Name`, `Sensitive`, `Threshold`, `Region[0..17]`.
* Also `Enable`, `Level` (1..6 sensitivity), `EventHandler`.
* Grid coordinates are normalized to the frame, so preview resolution does not
  affect the mask.

## Architecture: browser-based console, local deployment

**Decision:** build the console as a small **locally-run web app**, not a native
desktop bundle.

* **Backend:** Python 3.x **stdlib only** (`http.server`, `urllib`), a
  **standalone webserver** bound to `127.0.0.1` only. It
  serves the static frontend and proxies the camera CGI, handling Basic or
  Digest auth server-side. **Do not reuse pano's docker/lighttpd stack**; the console owns its
  own process and assets.
* **Frontend:** plain HTML/CSS/JS. Snapshot via
  `<img src="/proxy/snapshot.cgi?channel=0">`; mask grid as a canvas/SVG overlay;
  config forms via `/proxy/config?action=...`.
* **Launch:** `python3 console.py` → open Safari at `http://127.0.0.1:<port>`.
* **No `.app`, no PyInstaller/Briefcase, therefore no code signing, notarization,
  Gatekeeper, or TCC-identity churn.** Do not wrap it in Electron/pywebview/
  PyInstaller — that reintroduces signing.

A local proxy is still required: the camera CGI sends no CORS headers and
cross-origin Digest auth is unreliable/removed in modern browsers. The proxy
keeps the browser same-origin, handles Basic/Digest, avoids mixed-content problems,
and keeps camera credentials out of the frontend.

### Trade-off

| Concern | Desktop bundle (rejected) | Browser-based, local (chosen) |
|---|---|---|
| Signing / notarization | ad-hoc or self-signed; TCC churn | none |
| Packaging | `.app` bundle via Briefcase/PyInstaller | just scripts |
| Lifetime | Qt/PySide + app-bundle churn | browser-policy churn + a process to launch |
| Video | PyAV/ffmpeg if live view added | none (snapshot-only) |
| CORS / Digest | direct from app | handled by local proxy |
| Install | copy `.app` | none; run script |

Net: modestly longer-lived and easier to repair. The camera firmware/CGI remains
the real lifetime limit, not the client code.

### Deployment options considered

* **Standalone local webserver (chosen):** self-contained, works offline, only
  Terminal/Python gets the macOS Local Network prompt. Rebuild = edit files, no
  re-signing. The console runs its own server process; nothing is shared with
  pano.
* **pano's docker/lighttpd stack (rejected):** do not reuse it. Coupling the
  admin UI to the pano stack adds a Docker dependency, an extra admin surface,
  and contradicts the standalone requirement.

## Credential UX (settled 2026-11-01)

The console queries the user via a **browser login screen** on first load:
username (prefilled `admin`) and password. The form posts to the tokenized local
proxy; credentials stay in proxy memory only and are never placed in the URL,
cookie, localStorage, page source, or logs. Success sets a random `HttpOnly`,
`SameSite=Strict` session cookie; logout clears it. The proxy selects Basic or
Digest from the camera's `401` challenge and uses explicit Basic or a separate
Digest opener. It does not auto-retry failed logins, to avoid camera lockouts.

## Proposed MVP

Target directory: `amcrest-console/` (created; phase 0 tool present).

1. Browser login screen for credentials (sent to the local proxy once); read-only first.
2. **Snapshot preview** proxied from `/cgi-bin/snapshot.cgi` (main stream frame; no
   video).
3. **Motion mask editor**: load the legacy `MotionDetect[ch].Region` through the
   proxy, draw the 18x22 grid over the snapshot, paint with mouse, debounce
   applies. Show the 4-window data read-only; do not write it. Re-fetch the snapshot on demand (Refresh button) rather than
   streaming.
4. **Config forms** for the names the old UI used (Network/NAS(FTP)/Encode/NTP/
   AutoMaintain) via a generic getConfig/setConfig form layer in the proxy.
5. **Config backup/restore**: full dump to JSON, restore with read-modify-write.
6. **Safety**: per-apply pre-write snapshot; never clobber unrelated fields;
   serialize `setConfig` calls (camera dislikes rapid writes).

## Optional: live streaming (out of current scope)

Assumed scope if added: **one camera, substream, no audio, no recording/playback,
no PTZ**. The mask editor stays snapshot-based; live view is a separate,
non-critical panel so its failure can't break Config or masks.

| Path | Work | Latency | New deps | Risk |
|---|---|---|---|---|
| Proxy camera MJPEG (`/cgi-bin/mjpg/video.cgi`, CGI PDF §4.2) | 0.25–0.5 day | ~0.2s | none | Safari has historically not rendered `multipart/x-mixed-replace` in `<img>` — test first; high bandwidth |
| ffmpeg remux RTSP substream → HLS (`-c copy`, no transcode) | 1–2 days | 3–6s tuned | ffmpeg | segment/process tuning |
| go2rtc / MediaMTX sidecar → WebRTC, built-in player | 1–2 days | <0.5s | Go binary or Docker | helper needs ad-hoc signing or Docker |
| Custom WHEP integration | 3–5 days | <0.5s | same | signaling/ICE edge cases |
| ffmpeg → jsmpeg (MPEG1 over WebSocket) | 2–4 days | 0.3–1s | ffmpeg | CPU transcode, quality |
| WebCodecs + fMP4 parsing | 5–10 days | low | none | most code, browser quirks |

Hidden costs: helper process supervision/auto-restart, RTSP reconnect/backoff,
camera RTSP-client limits (fine for one camera, not a wall), the macOS Local
Network prompt now attaching to the spawned helper, and Safari-version testing.
Signing: the console still needs none; a downloaded go2rtc/MediaMTX binary needs a
one-time `codesign -s -` (notarization-free), or run it in Docker.

Recommendation: spend ~0.5 day testing `/cgi-bin/mjpg/video.cgi` in Safari. If it
renders, this is nearly free. Otherwise use ffmpeg → HLS (1–2 days) — adequate for
"is someone there" and mask-setting does not need it. Pay for WebRTC only if
sub-second latency becomes a real requirement.

## Caveats

* Auth varies by model: IP2M-842 uses Basic; IP3M-943 uses Digest. Support both
  explicitly; do not combine both handlers in one opener.
* Bind the local proxy to `127.0.0.1`, never `0.0.0.0`; do not log credentials.
  Query them via the browser login screen; keep them in memory only.
* The IP2M-842 HTTP server is slow and single-connection. Use one request at a
  time, long timeouts, and backoff; stop the P2P stream if a request hangs.
* Two mask models coexist. Phase 0 found the legacy `Region` is the only safe
  writable model; write **all 18 rows** in one `setConfig`, because partial
  writes reset the rest. The 4-window model is read-only in practice, and on
  cam-01 it is the exact horizontal mirror of the legacy mask. Do not write it.
  See `amcrest-console-plan.md`.
* Keep cameras wired/static (as in `amcrest-cameras-from-log.md`) so vendor
  onboarding is never needed again; document the CGI network-config fallback.
* Disable unused P2P/cloud so loss of Amcrest services can't surprise us.

## Exit path

If the 2015-era cameras fail, replace with current plugin-free cameras (Amcrest/
Dahua/Reolink) that have an HTML5 web UI and FTP upload. `pano` only consumes
FTP-uploaded JPEGs, so a compatible camera drops into the existing pipeline; the
custom app then becomes unnecessary.

## Open decisions

* Whether to add the optional single-camera live-streaming panel (see the
  live-streaming section); Config + mask editing do not depend on it.

Settled: the console runs its own standalone local webserver and does not reuse
pano's docker/lighttpd stack.

Signing is moot under this architecture: the app is plain scripts + a browser, so
there is nothing to sign. Signing/notarization only returns if the console is
later wrapped in an Electron/pywebview/PyInstaller bundle, which is explicitly
avoided.
