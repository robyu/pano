---
update: 2026-11-03 19:30 PST
tags: dahua, rpc2, api, reference, submodule
---

# Dahua RPC API submodule index

Location: `third_party/dahua-rpc-api/` (git submodule, MIT).
Purpose: reverse-engineered Dahua/Amcrest JSON-RPC 2.0 API reference plus a
minimal Python client.

## Root
* `README.md` — architecture, endpoints, 2-step login, multicall, `multiSec`,
  session lifecycle, best practices, module table.
* `LICENSE` — MIT.
* `requirements.txt` — `requests>=2.28.0` (reference client only).
* `.gitignore`, `.git` — submodule metadata.

## reference/
* `reference/dahua_rpc_client.py` — minimal login + `system.listMethod` client.
  Uses `requests.Session` (so returned cookies persist implicitly), but has no
  keepalive, logout, or error-code handling.

## modules/
* `00-core-endpoints.md` — `/RPC2_Login`, `/RPC2`, `/OutsideCmd`; payload,
  response and error formats; challenge code `268632079`, invalid-session code
  `287637504`; encryption detection.
* `01-authentication.md` — `global.login` two-step handshake, `global.keepAlive`
  (~60 s), `global.logout`, authority types.
* `02-system-magicbox.md` — `system.listMethod`, `multicall`, `multiSec`, time
  get/set, reboot/shutdown/reset, device/hardware/firmware/system info,
  `DevInit`, `WebInit`.
* `03-configuration.md` — `configManager.getConfig/setConfig/getDefault/
  setTemporaryConfig/setChannelConfig/restore/restoreExcept/saveFile/deleteFile`;
  known tables; encrypted configs (PPPoE/DDNS/VPN/Email) need `system.multiSec`.
* `04-ptz-lens.md` — movement, presets, tours, patterns, scans, focus/iris,
  limits, `ptzBase`, `PtzFunc`, `PtzPeripheral`.
* `05-video-audio-encoding.md` — `encode`, video input/output, audio
  input/output/encode, `speak`, OSD, privacy masking, interlocks, stream URI.
* `06-alarms-events.md` — alarm slots/state/caps, `PirAlarm`, `eventManager`
  attach/detach/list/confirm, common event codes.
* `07-ivs-analytics-faces.md` — video analyse/detect, IntelliTracker, face
  recognition, flow/traffic stats, traffic snapshot/strobe.
* `08-storage-files.md` — storage info, partition format, record/snap managers,
  `FileManager`, `mediaFileFind`, `RecordFinder`, `RecordUpdater`, `SDEncrypt`.
* `09-network.md` — `netApp` interfaces/UPnP/WPS/mail/IP-conflict/RSSI/stream
  URI/comm ports, WLAN, DDNS, PPPoE, LoRa, mobile, intervideo, FTP.
* `10-security-users.md` — user/group/password/authority management, DockUser,
  encryption info, password reset, certificates, GB35114, CertManager, 802.1X.
* `11-thermography-sensors.md` — radiometry, thermography, thermal NUC, laser
  distance, temperature correction, FLIR debug, cooling, UWB.
* `12-maintenance-upgrade.md` — log find/clear/append, local/cloud/remote
  upgrade, backup, install manager, license, work directory, integration logs.

## Pano-relevant notes
* `configManager.getConfig` / `setConfig` (`modules/03-configuration.md`) is the
  documented path for `MotionDetect`.
* The docs specify the JSON `session` field but never mention the
  `DhWebClientSessionID` cookie. The reference client uses `requests.Session`,
  which silently persists `Set-Cookie`, so cookie-based auth is not ruled out —
  but it is not documented. This only partially supports the current cookie
  hypothesis for the HTML `/RPC2` response.
* Session invalidation is error code `287637504`; idle sessions need
  `global.keepAlive` roughly every 60 s. Our client does neither yet.
* The reference client is not a drop-in: no keepalive, no logout, no robust
  error handling, and it depends on `requests` (the console is stdlib-only).
