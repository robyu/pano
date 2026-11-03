# Amcrest console

A small, loopback-only web console for one Amcrest/Dahua camera. It replaces the
old NPAPI browser plugin for the parts pano needs: viewing a snapshot and (in
later phases) editing the motion mask and config.

Phase 1 provides: browser login, in-memory session, and snapshot proxying.

## Requirements

- Python 3.7+ (stdlib only; no pip installs)
- A reachable camera on the local network

## Run

```bash
cd amcrest-console
python3 console.py --camera-ip 192.168.2.121 --name cam-01 --model amcrest-ip2m-842
```

The console binds `127.0.0.1` only and prints a tokenized URL:

```text
Open: http://127.0.0.1:8765/s/<token>/
```

Open that URL, sign in with the camera username/password, and the snapshot
loads. Credentials are kept in the proxy's memory only; they are never written
to disk, the URL, the cookie, or the page source.

Useful options:

- `--camera-port` — camera HTTP port (default 80)
- `--port` — local console port (default 8765)
- `--auth {auto,basic,digest}` — default `auto` (model-based, then challenge)
- `--request-delay` — seconds between camera requests (default 1.0 for IP2M-842)
- `--timeout` — camera request timeout (default 20s)
- `--no-browser` — print the URL without opening a browser

## Remote access (SSH tunnel)

Keep the loopback bind and forward the port over SSH:

```bash
ssh -L 8765:127.0.0.1:8765 ryu@chuyu-server.local
# then browse http://127.0.0.1:8765/s/<token>/
```

Do not bind the console to `0.0.0.0` or a LAN address.

## Security model

- Loopback bind plus a per-run random token in the path.
- `Host` and `Origin` are checked to block DNS rebinding and cross-origin writes.
- Session cookie is random, `HttpOnly`, and `SameSite=Strict`.
- Only allowlisted camera CGI endpoints are proxied; the camera host is fixed by
  `--camera-ip`.
- Camera requests are serialized and throttled; the IP2M-842 is slow and
  single-connection, and `getSoftwareVersion` crashes its web server.

## Tests

```bash
cd amcrest-console
python3 -m unittest discover -s tests
```

## Phase 0 discovery

`discover.py` is the read-only discovery tool used to learn the camera CGI
behavior. See `../agent-files/amcrest-console-plan.md` for findings and the
remaining phases.
