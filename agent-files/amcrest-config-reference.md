---
update: 2026-11-08 11:30 PST
tags: amcrest, cameras, console, configuration, ip2m-842, ip3m-943b
---

# amcrest-console configuration reference

Every configuration item `amcrest-console` exposes in its **Configuration** tab,
explained item by item, with applicability per camera model and the
corresponding control in the camera's own built-in web UI.

## Scope

* **Console:** `amcrest-console` (phase 3 Configuration tab). Sections are
  allowlisted in `schemas.py`; values are read via
  `configManager.cgi?action=getConfig` and written back via CGI with an RPC2
  (`configManager.setConfig`) fallback (`cgi_config.py`, `camera.py`).
* **Models:** `IP2M-842` (cam-01/03/04/05/06) and `IP3M-943B` (cam-07/08/09).
  Model is auto-detected at login (`getDeviceType`).
* **Key inventory source:** the sanitized per-camera dumps in
  `amcrest-console/fixtures/cam-NN-<ip>/<timestamp>/config-<Section>.json`
  (captured 2026-11-01 by `discover.py`). Five IP2M-842 units and three
  IP3M-943B units were unioned; a key is reported as present for a model if any
  unit of that model returns it.
* **UI correlation source:** the cameras' own web-UI page modules
  (`/html/<page>.htm`, `/js/<page>.js`), read 2026-11-08 after an RPC2 login
  supplied the `DhWebClientSessionID` cookie. Control ids quoted below
  (`tcpip_v4_address`, `video_resolution0`, `v_m_sen`, …) are the real element
  ids from those pages.

## How to read the tables

| Column | Meaning |
|---|---|
| Item | Flat config key. `[n]` stands for every index the camera returns. |
| Console | Widget the console renders. **ro** = visible in the raw viewer only; the console refuses to write it. |
| 842 / 943 | `✔` present on that model · `NA` firmware does not return it · `✔ inert` present but disabled/unused. |
| Built-in web UI | Where the same setting lives in the camera's own web interface. |
| Meaning | What the item does. |

**NA has two flavours**, and both are called out:

* **absent** — the firmware never returns the key (e.g. `NAS[3]` on the
  IP3M-943B). Nothing on that model can use it.
* **inert** — the key exists but the feature is off, so changing it does
  nothing: `NAS[1..3] Enable=false`, `AutoShut*Day=-1`,
  `Encode…ExtraFormat[1..3] VideoEnable=false`,
  `MotionDetectWindow[1..3]` regions all-zero.

## Why the console shows more than the built-in web UI

The camera's web UI is a thin front end over the same `configManager` tables; it
only renders the fields its pages happen to have widgets for, and it hides
several entirely. The console instead shows the whole table for a section, so it
surfaces items the web UI has no control for:

* `General.*` — login lockout policy. The IP2M-842's General page has **no**
  control for `LockLogin*` (so the console is the only way to read it there —
  as `amcrest-console/README.md` says), but the IP3M-943B **does** expose
  `LockLoginEnable` and `LockLoginTimes` as `gen_LockEnable` / `gen_LockTimes`
  on Setup ▸ System ▸ General **[v]**. The console shows all of it read-only.
* `Network.bond0.*` — a bonding interface the web UI's TCP/IP page never shows.
* `NAS[1]`, `NAS[2]`, `NAS[3]` — the unused NFS / iSCSI / SMB storage slots. The
  web UI's FTP page only ever touches slot 0.
* `MotionDetect[0].EventHandler.*` — ~40 per-event action flags (alarm out,
  record latch, tour, PTZ link, weekly schedule, de-jitter). The web UI spreads
  a few of these across checkboxes and never exposes the rest.
* `Encode[0].MainFormat[1..3]`, `ExtraFormat[1..3]`, `SnapFormat[1..2]` —
  alternate resolution/bitrate profiles. The web UI presents only the active
  profile.
* `AutoMaintain.AutoOpen*`, `AutoShut*`, `AutoStartUp*` — schedules the web UI
  does not render (it shows Auto Reboot and Auto Delete Old Files).

Two console-specific caveats: `General` is read-only by design, and
`MotionDetect` in the Configuration tab edits only `Enable` and `Level` — the
18x22 mask lives in the **Legacy mask** tab.

## Built-in web UI map

Recovered from the cameras themselves: `js/set.js` supplies the setup menu and
each menu item's `data-filename`, which maps to a page module served at
`/html/<name>.htm` + `/js/<name>.js`:

| Console section | Page module | IP2M-842 (legacy UI) | IP3M-943B (Web3.0 UI) |
|---|---|---|---|
| General | `generalConfig` | Setup ▸ System ▸ General **[v]** | Setup ▸ System ▸ General **[v]** |
| Network | `networkConfig` | Setup ▸ Network Settings ▸ TCP/IP Settings **[v]** | Setup ▸ Network ▸ TCP/IP **[v]** |
| NAS | `recordStorageConfig` (`_old` variant also present on the 842) | Setup ▸ Memory Manage ▸ Storage ▸ Destination ▸ FTP **[v]** | Setup ▸ Storage ▸ Destination ▸ FTP **[v]** |
| NTP | `generalConfig`, Date-Time tab | Setup ▸ System ▸ General ▸ Date & Time **[v]** | Setup ▸ System ▸ General ▸ Date & Time **[v]** |
| Encode (video) | `encodeConfig` | Setup ▸ Camera Setup ▸ Video **[v]** | Setup ▸ Camera ▸ Video **[v]** |
| Encode (audio) | `audioConfig` | Setup ▸ Camera Setup ▸ Audio **[v]** | Setup ▸ Camera ▸ Audio **[v]** |
| AutoMaintain | `autoMaintainConfig` | Setup ▸ System ▸ Auto Maintain **[v]** | Setup ▸ System ▸ Auto Maintain **[v]** |
| MotionDetect | `videoDetectConfig` (`_old` variant also present on the 842) | Setup ▸ Event manage ▸ Video Check **[v]** | Setup ▸ Event ▸ Video Detection **[v]** |

Full IP2M-842 setup menu, in camera order, as scraped from `js/set.js`
(translation keys, `w_` prefix stripped):

* **Camera Setup** — Camera Attribute, Video, Audio, IVS Set
* **Network Settings** — TCP/IP Settings, Connect Settings, PPPOE, DDNS
  Settings, IP Purview, Mail Settings, UPNP, SNMPv1/v2, QOS, Bonjour, Multicast,
  Auto Register, WIFI, 3G, IEEE802, VPN Settings, ATMOsd, access_platform
* **Event manage** — Video Check, AlarmConf, ABNORMITY
* **Memory Manage** — Timetable, memory (storage/FTP), Recording Control
* **System** — Local Config, User Management, UserSearch, PtzConfig, ComConf,
  Default Setting, Collocate I/O, Auto Maintain, Firmware Upgrade
* **System Info** — Edition Info, Log, Onlineuser, VspCfg, GAYS, ldap

Page modules fetched 2026-11-08 (read-only, one RPC2 login per camera):
`encodeConfig`, `audioConfig`, `networkConfig`, `videoDetectConfig`
(+ `videoDetectConfig_old`), `recordStorageConfig` (+ `_old`),
`autoMaintainConfig`, `generalConfig` — from both 192.168.2.121 and
192.168.2.127. Note that HTTP Basic/Digest alone is not enough: the pages
301-redirect to the login screen unless the `DhWebClientSessionID` cookie from
an RPC2 login is sent, which is why the first pass could not read them.

The IP2M-842's page markup ships with SimpChinese defaults, so a few labels were
read from the English `tl()` keys in the page JS instead (e.g. `w_Auto Reboot`,
`w_Auto Delete File`, `w_Sensitivity`).

---

## 1. General — read-only

Console: no form, raw viewer only. `schemas.py` marks the whole section
read-only. Nothing here maps to a built-in web UI page **[v]**.

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `General.MachineName` | ro text | ✔ `cam-06` | ✔ `AMC01861_172R3Q` | 842: none · 943B: `gen_devName` (System ▸ General) **[v]** | Device name / machine identifier. The 842 units carry the pano camera name; the 943B units carry a factory machine string. |
| `General.LocalNo` | ro text | ✔ `8` | ✔ `8` | 842: none · 943B: `gen_devNo` **[v]** | Local device number used by the Dahua/Amcrest local protocol. Fixed. |
| `General.LockLoginEnable` | ro bool | ✔ `true` | ✔ `true` | 842: **none** · 943B: `gen_LockEnable` checkbox **[v]** | Master switch for the failed-login lockout. Only the 943B's UI exposes it — on the 842 the console is the only way to read it. |
| `General.LockLoginTimes` | ro number | ✔ `5` | ✔ `30` | 842: **none** · 943B: `gen_LockTimes` **[v]** | Failed-login attempts before lockout. The 943B widget clamps input to 3-10 even though its firmware reports 30. The 842 is far stricter (5). |
| `General.LoginFailLockTime` | ro number | ✔ `1800` | ✔ `300` | none on either model **[v]** | Lockout duration in seconds once tripped. **842 = 30 min**, 943B = 5 min — this is why a 842 lockout is so disruptive. |
| `General.LoginFailLoginTime` | ro number | ✔ `300` | NA | none **[v]** | Window (seconds) in which failures are counted. Only the 842 reports it. |
| `General.MaxOnlineTime` | ro number | NA | ✔ `3600` | none **[v]** | Max web session length in seconds. Only the 943B reports it. |

**Operational note:** the console's own failed logins count toward this
lockout (`server.py` delays per source address to limit churn). If a 842 starts
returning 401 for good credentials, wait out `LoginFailLockTime` (1800 s) before
retrying.

## 2. Network — dangerous

Console: form groups per interface (`eth0`, `eth2`, plus `bond0` where present),
typed fields (IP/MTU/boolean). Marked **dangerous**: requires the typed
`APPLY NETWORK` confirmation and writes a full sanitized backup to
`amcrest-console/backups/` first. Built-in UI: Setup ▸ Network Settings ▸
TCP/IP Settings **[v]**.

Interfaces: `eth0` = wired, `eth2` = wireless on both models. The console is
usually pointed at `eth2` (the address the cameras get by DHCP).

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `Network.DefaultInterface` | text (dangerous) | ✔ `eth2` | ✔ `eth2` | 842: `tcpip_network_card` + `tcpip_network_card_set_as_default` (Ethernet Card / Set DefaultCard) · 943B: `NN_*` card selector **[v]** | Which interface serves the camera's traffic. Changing it can make the camera unreachable. |
| `Network.Hostname` | text (dangerous, RFC-1123 validated) | ✔ `cam-06` | ✔ `cam-09` | `tcpip_hostname` / `NN_hostname` (HostName) **[v]** | Device hostname. Matches the pano camera name. |
| `Network.Domain` | text | ✔ `IPC` | ✔ `dauha` | none — no control on either TCP/IP page **[v]** | Search domain. Factory filler on both; unused on this LAN. |
| `Network.<if>.IPAddress` | IP (dangerous) | ✔ | ✔ | `tcpip_v4_address` / `NN_IPV4_IP` (IP Address) **[v]** | Static address of the interface. |
| `Network.<if>.SubnetMask` | IP (dangerous) | ✔ `255.255.255.0` | ✔ `255.255.255.0` | `tcpip_v4_subnet_mask` / `NN_IPV4_SM` **[v]** | Netmask. |
| `Network.<if>.DefaultGateway` | IP (dangerous) | ✔ | ✔ | `tcpip_v4_gateway` / `NN_IPV4_DG` **[v]** | Gateway. `eth0` and `eth2` can point at different gateways. |
| `Network.<if>.DhcpEnable` | bool (dangerous) | ✔ (`eth2`=`true`, `eth0`=`false`) | ✔ (same) | `tcpip_v4_mode` (Mode: Static / DHCP) **[v]** | DHCP vs static. Wired is static, wireless is DHCP on every unit. |
| `Network.<if>.EnableDhcpReservedIP` | bool (dangerous) | ✔ `false` | ✔ `false` | none **[v]** | Ask the DHCP server for a reserved lease. Unused here. |
| `Network.<if>.DnsServers[n]` | IP (dangerous), n = 0-1 | ✔ | ✔ | `tcpip_v4_preferred_dns` / `tcpip_v4_alternate_dns` (First/Second DNS Server) · 943B `NN_IPV4_DNS1/2` **[v]** | Preferred and alternate DNS. Slot 1 is `0.0.0.0` (empty) on most units. |
| `Network.<if>.MTU` | number 576-9000 | ✔ `1500` | ✔ `1500` | **none** — no MTU control on either model's TCP/IP page **[v]** | Link MTU. |
| `Network.<if>.PhysicalAddress` | ro text | ✔ | ✔ | `tcpip_mac_address` / `NN_macadd` (Mac Address) **[v]** | Burned-in MAC, read-only. |
| `Network.<if>.DnsAutoGet` | bool | ✔ (cam-04/06 only) | NA | none **[v]** | Obtain DNS from DHCP automatically. **Absent on the 943B**; on the 842 only cam-04 and cam-06 report it. |
| `Network.<if>.Enable` | bool | ✔ (cam-04/06 only) | NA | none **[v]** | Administrative up/down for the interface. Same availability caveat. |
| `Network.<if>.NetMode` | text | ✔ empty (cam-04/06) | NA | none **[v]** | Wired/wireless mode string. Empty on every unit — effectively unused. |
| `Network.<if>.Type` | ro text | ✔ empty (cam-04/06) | NA | none **[v]** | Interface type string. Empty. |
| `Network.bond0.*` | see below | ✔ | **NA** | none **[v]** | Link-bonding pseudo-interface. Present on every 842 unit; the 943B has no `bond0` at all. |
| `Network.bond0.Bonding` | ro bool | ✔ `false` | NA | none **[v]** | Whether bonding is active. Disabled everywhere — inert. |
| `Network.bond0.IPAddress` | IP | ✔ `192.168.1.110` | NA | none **[v]** | Bond address. Off-subnet and inert. |
| `Network.bond0.{DefaultGateway,DhcpEnable,DnsAutoGet,Enable,EnableDhcpReservedIP,MTU,NetMode,PhysicalAddress,SubnetMask,Type}` | mixed | ✔ cam-04/06 only | NA | none **[v]** | Rest of the bonding table; only two 842 units expose it. Inert. |

Also on the TCP/IP page but with **no** console item: `tcpip_arp_enable`
(Open ARP/Ping — enabled on these units, per the pano log), the IPv6 block
(`tcpip_v6_*` / `NN_IPV6_*`), T2U/P2P (`tcpip_T2U*` / `NP_T2UEnable`), and the
943B's serial/QR display (`NP_SN`, `NP_QR`).

Firmware variant: the 842 population is split — cam-01/03/05 return 23 Network
keys, cam-04/06 return 41 (the extra `bond0`, `DnsAutoGet`, `Enable`, `NetMode`,
`Type` entries). The 943B units are uniform at 21.

## 3. NAS / FTP — dangerous

Console: one group per storage slot, protocol select (FTP/NFS/iSCSI/SMB),
password field kept blank to preserve the current value, port/timeout numbers.
Marked **dangerous** (`APPLY NAS`, backup before write). Built-in UI: Setup ▸
Memory Manage ▸ Storage ▸ Destination ▸ FTP **[v]**.

This is the section pano depends on: the cameras FTP-upload snapshots to the
vsftpd container at `192.168.2.8:21`, one directory per camera.

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `NAS[n].Protocol` | select FTP/NFS/ISCSI/SMB (dangerous) | ✔ 4 slots: FTP, NFS, ISCSI, SMB | ✔ 3 slots: FTP, ISCSI, NFS | fixed per tab: FTP tab = slot 0, NAS tab = the NFS/iSCSI/SMB slots **[v]** | Storage protocol of the slot. The **SMB slot is NA on the 943B**. |
| `NAS[n].Enable` | bool (dangerous) | ✔ slot 0 = `true`, 1-3 = `false` | ✔ slot 0 = `true`, 1-2 = `false` | `rs_tab_ftp_enable` (Setup FTP) / `rs_tab_network_enable` (Setup NAS) **[v]** | Turns the slot on. Slots 1+ are inert on every camera. |
| `NAS[n].Address` | text (dangerous) | ✔ `192.168.2.8` | ✔ `192.168.2.8` | `rs_tab_ftp_address` / `rs_tab_network_address` (Server Address) **[v]** | Target host. FTP host for pano; unused slots hold `0.0.0.0` (943B) or empty (842). |
| `NAS[n].Port` | number 1-65535 | ✔ `21` | ✔ `21` | `rs_tab_ftp_port` / `rs_tab_network_port` (Port) **[v]** | Target port. Unused slots carry the protocol default (21/3260/445). |
| `NAS[n].Directory` | text (dangerous) | ✔ all 4 slots | ✔ slots 0 and 2 only | `rs_tab_ftp_directory` (Remote directory) / `rs_tab_network_directory` (Remote Path) **[v]** | Remote path — one per camera (e.g. `cam-06`). The 943B's iSCSI slot has no Directory field. |
| `NAS[n].UserName` | text (dangerous) | ✔ (pano FTP user) | ✔ (pano FTP user) | `rs_tab_ftp_username` / `rs_tab_network_username` (User) **[v]** | Login for the target. Value omitted here per the repo's no-credentials convention; read it from `pano/pano-docker.json` or the console. |
| `NAS[n].Password` | password (secret, blank = keep) | ✔ | ✔ | `rs_tab_ftp_password` / `rs_tab_network_password` **[v]** | Stored as `<redacted>` in mirrors and backups; restore must re-enter it. |
| `NAS[n].CharacterEncoding` | text | ✔ all 4 slots | ✔ slots 0 and 2 only | none **[v]** | Filename encoding. `UTF-8` everywhere; no web UI control. |
| `NAS[n].TimeOut` | number 0-3600 | ✔ slot 0 = `0` | ✔ slot 0 = `10000` | none **[v]** | Transfer timeout (ms). Only slot 0 has the field, and the two models disagree: 842 = 0 (no timeout), 943B = 10 s. |
| `NAS[n].Name` | text | **NA** | ✔ `FTP1` / `ISCSI1` / `NFS1` | none **[v]** | Slot label. Only the 943B names its slots. |

Also on the storage page, with no console item: `rs_tab_ftp_emergency`
(Exigency Storage(Local) — the "Emergency (Store on SD Card)" box the pano log
records as unchecked), `rs_tab_ftp_sync` (Syn Data), the Local Storage tab (SD
card — "No SD Card" on these units), and the Record/Capture-Picture path tabs
(`rs_tab_path_video`, `rs_tab_path_snap`).

## 4. NTP

Console: five plain fields, not marked dangerous. Built-in UI: Setup ▸ System ▸
General ▸ **Date-Time** tab (the "Sync with NTP Server" block) **[v]** — the
page is `generalConfig` on both models, and the pano log screenshots agree
(`clock.isc.org`, port 123, update every 10 min).

Identical on both models — no NA rows.

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `NTP.Enable` | bool | ✔ `true` | ✔ `true` | `date_time_NTP_enable` / `gen_NTPEnable` (NTP Settings — "Sync with NTP Server") **[v]** | Turns NTP sync on. |
| `NTP.Address` | text | ✔ `clock.isc.org` | ✔ `clock.isc.org` | `date_time_NTP_server` / `gen_NTPServer` (NTP Server) **[v]** | Time server hostname. |
| `NTP.Port` | number 1-65535 | ✔ `123` | ✔ `123` | `date_time_NTP_port` / `gen_NTPPort` (Port) **[v]** | NTP port. |
| `NTP.TimeZone` | number 0-32 | ✔ `28` | ✔ `28` | `date_time_time_zone` / `gen_timeZone` (Time Zone) **[v]** | Firmware timezone index. 28 = GMT-08:00 (matches the log screenshots). |
| `NTP.UpdatePeriod` | number 0-1440 | ✔ `10` | ✔ `10` | `date_time_NTP_update_periods` / `gen_NTPUPeriod` (Update Period, minutes) **[v]** | Sync interval in minutes. |

DST sits on the same Date-Time tab (`date_time_DST_*` / `gen_DST*`) **[v]** but
has **no** console item — the pano log records DST off on these units, and the
console cannot see or change it. Same tab also carries date/time format, the
current system time, and "Sync PC" (`date_time_synchronize_PC`).

## 5. Encode

Console: a group per profile — *Main format n*, *Extra format n*,
*Snapshot format n* — with video and audio sub-fields. Not marked dangerous.
Built-in UI: Setup ▸ Camera Setup ▸ **Video** (video fields) and **Audio**
(audio fields) **[v]**.

Profile indices actually returned:

| Profile | IP2M-842 | IP3M-943B |
|---|---|---|
| `MainFormat` | 0-3 (20 fields each) | 0-3 (24 fields each) |
| `ExtraFormat` | 0-3 (20/19/19/19 fields) | 0-2 (23/22/22 fields) |
| `SnapFormat` | 0-2 (19 fields each) | 0-2 (23 fields each) |

Main = the full-resolution stream (842: 1920x1080; 943B: 2304x1296). Extra = the
sub-stream used by the mobile apps (842: 640x480; 943B: 640x480). Snap = the
MJPEG snapshot stream pano's FTP captures rely on. Indices 1-3 are alternate
saved profiles; only index 0 is live, so indices 1-3 are **inert** on both
models.

### Video fields

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `Encode[0].<fmt>[n].Video.resolution` | text, `WxH` pattern | ✔ | ✔ | `video_resolution0` (main) / `video_resolution1` (sub) / `video_snap_resolution` **[v]** | Frame size (e.g. `1920x1080`, `2304x1296`, `640x480`). |
| `Encode[0].<fmt>[n].Video.FPS` | number 1-60 | ✔ | ✔ | `video_fps0` / `video_fps1` (Frame rate(FPS)) **[v]** | Frames per second. |
| `Encode[0].<fmt>[n].Video.BitRate` | number 8-65536 (Kbps) | ✔ | ✔ | `video_bitrate0` / `video_bitrate1` (Bit Rate, with a recommended range in `video_bitrefer*`) **[v]** | Target bitrate. |
| `Encode[0].<fmt>[n].Video.BitRateControl` | text | ✔ `CBR`/`VBR` | ✔ `VBR` | `video_bitctrl0` (Bit Rate Type: CBR/VBR) **[v]** | Constant vs variable bitrate. |
| `Encode[0].<fmt>[n].Video.Compression` | text | ✔ `H.264`, `MJPG` (snap) | ✔ `H.264`, `MJPG` (snap) | `video_compression0` (Encode Mode) **[v]** | Codec. Snapshot profiles are MJPEG. |
| `Encode[0].<fmt>[n].Video.Profile` | text | ✔ `Main`/`High` | ✔ `Main`/`High` | none directly — the 842's Encode Mode select folds `H.264`/`H.264B`/`H.264H` into Compression + Profile **[v]** | H.264 profile, written from the compression choice. |
| `Encode[0].<fmt>[n].Video.GOP` | number 1-600 | ✔ | ✔ | `video_gop0` (I Frame Interval, 1-150 on the 943B) **[v]** | GOP length; the web UI labels it "frame interval". |
| `Encode[0].<fmt>[n].Video.Quality` | number 1-6 | ✔ | ✔ | `video_quality0` (Quality) / `video_snap_imgQuality` **[v]** | Quality step (6 = best). Only meaningful under VBR. |
| `Encode[0].<fmt>[n].VideoEnable` | bool | ✔ | ✔ | `video_subStream_enable` (sub-stream Enable); main stream is always on **[v]** | Turns the profile on. Index 0 is `true`; the rest are `false` → inert. |
| `Encode[0].<fmt>[n].Video.Priority` | number 0-100000 | **NA** | ✔ `0` | none — not present in the 943B's encode page JS **[v]** | Stream priority. 943B only, console-only item. |
| `Encode[0].<fmt>[n].Video.MaxBitrate` | number 8-65536 | **NA** | ✔ (cam-09 only) | none — not present in the 943B's encode page JS **[v]** | Bitrate ceiling for VBR. 943B only, and only cam-09's firmware reports it. Console-only. |
| `Encode[0].<fmt>[n].Video.SVCTLayer` | ro number | **NA** | ✔ `1` | `video_svc0` on the 943B (`h.SVCTLayer` is written from it) **[v]** | SVC temporal layer count. 943B only, read-only in the console. |
| `Encode[0].<fmt>[n].Video.CustomResolutionName` | ro text | ✔ (`ExtraFormat[0]`, `VGA`) | ✔ (main + snap, e.g. `2304x1296`) | `video_custom0` (custom resolution) **[v]** | Label for a custom resolution. Read-only. |
| `Encode[0].<fmt>[n].Video.Width` / `.Height` | ro number | ✔ | ✔ | none (derived from Resolution) **[v]** | Dimensions mirroring `resolution`; read-only. |
| `Encode[0].<fmt>[n].Video.QualityRange` | ro number | ✔ `6` | ✔ `6` | none **[v]** | Number of quality steps available. Read-only. |
| `Encode[0].<fmt>[n].Video.Pack` | ro text | ✔ `DHAV` | ✔ `DHAV` | none **[v]** | Dahua stream packaging. Read-only. |

Also on the Video page with no console item: `video_water_*` (Watermark — the
pano log records "amcrest0"), `video_OSD_*` (on-screen text/time overlays),
`video_privmask_*` (privacy mask), `video_Inter_*` (region of interest), and
`video_encodeAuth_enable*` / `video_svcPwd_enable*` (stream encryption).

### Audio fields

Audio is `AudioEnable=false` on every profile of every unit — the whole audio
table is **inert** on this system.

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `Encode[0].<fmt>[n].AudioEnable` | bool | ✔ `false` | ✔ `false` | `audio_mainAudio` / `audio_extraAudio` (842) · `au_e_mEnable` (943B) **[v]** | Turns audio on. Off everywhere. |
| `Encode[0].<fmt>[n].Audio.Compression` | text | ✔ `G.711A` | ✔ `AAC` (index 0), `G.711A` (rest) | `audio_codeMode` / `audio_mainAudioList` (Encode Mode) **[v]** | Audio codec. |
| `Encode[0].<fmt>[n].Audio.Bitrate` | number 8-65536 | ✔ `64` | ✔ `64` | none **[v]** | Audio bitrate (Kbps). |
| `Encode[0].<fmt>[n].Audio.Frequency` | number 0-100000 | ✔ `44000` | ✔ `44000` | `audio_mainAudioList` (Sampling Frequency) **[v]** | Sample rate. |
| `Encode[0].<fmt>[n].Audio.Depth` | number 0-100000 | ✔ `16` | ✔ `16` | none **[v]** | Sample bit depth. |
| `Encode[0].<fmt>[n].Audio.Pack` | text | ✔ `DHAV` | ✔ `DHAV` | none **[v]** | Stream packaging. Read-only in practice. |
| `Encode[0].MainFormat[n].Audio.Mode` | number 0-100000 | ✔ `0` (main only) | ✔ `0` (main only) | none **[v]** | Audio input mode. Only the Main profiles carry it. |
| `Encode[0].<fmt>[n].Audio.Channels` | not in the console | NA | not returned by `getConfig` — but the 943B's Audio page has two-channel checkboxes (`au_e_mCh0/1`) **[v]** | 943B Audio page | Audio channel map. The 943B UI can set it; no camera dump has ever returned the key, so the console cannot see it. |

## 6. Auto maintain

Console: five groups — *Auto open*, *Auto reboot*, *Auto shut*, *Auto
shutdown*, *Auto start up* — each with Enable / Day / Hour / Minute. Not marked
dangerous. Built-in UI: Setup ▸ System ▸ Auto Maintain **[v]**, which only
renders Auto Reboot and Auto Delete Old Files.

`Day` is `-1` = never, `0-6` = a weekday, `7` = every day (both models use `7`
for Auto Reboot). **Neither model returns `AutoOpenEnable`, `AutoShutEnable`,
`AutoShutdownEnable` or `AutoStartUpEnable`** — only `AutoRebootEnable` exists —
so the open/shutdown/startup schedules are day+time only, with no on/off flag.

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `AutoMaintain.AutoRebootEnable` | bool | ✔ `true` | ✔ mixed (`false` on cam-07, `true` elsewhere) | `autoMaintain_autoRebootEnable` (w_Auto Reboot) · 943B `a_r_show`/`a_r_time` **[v]** | Daily reboot on/off. **Pano wants this off**: the daily reboot was what deleted older images. |
| `AutoMaintain.AutoRebootDay` | number -1..7 | ✔ `7` | ✔ `7` | `autoMaintain_everyday` / `autoMaintain_Monday`…`Sunday` (w_everyday / weekday boxes) **[v]** | Reboot day; `7` = every day. |
| `AutoMaintain.AutoRebootHour` | number 0-23 | ✔ `16` | ✔ `11`/`14` | `autoMaintain_autoRebootHour` (time box) **[v]** | Reboot hour. |
| `AutoMaintain.AutoRebootMinute` | number 0-59 | ✔ `6` | ✔ `11`/`44` | `autoMaintain_autoRebootMinute` **[v]** | Reboot minute. |
| `AutoMaintain.AutoOpenDay` / `.AutoOpenHour` / `.AutoOpenMinute` | numbers | ✔ all `-1`/`0` | **NA** | none — no control on the 842's Auto Maintain page **[v]** | Scheduled power-on. 842 only, and inert (day `-1`). |
| `AutoMaintain.AutoShutDay` / `.AutoShutHour` / `.AutoShutMinute` | numbers | ✔ all `-1`/`0` | **NA** | none **[v]** | Scheduled shutdown — **842 spelling (`Shut`)**. Inert. |
| `AutoMaintain.AutoShutdownDay` / `.AutoShutdownHour` / `.AutoShutdownMinute` | numbers | **NA** | ✔ all `-1`/`0` | none **[v]** | Scheduled shutdown — **943B spelling (`Shutdown`)**. Inert. |
| `AutoMaintain.AutoStartUpDay` / `.AutoStartUpHour` / `.AutoStartUpMinute` | numbers | **NA** | ✔ all `-1`/`0` | none **[v]** | Scheduled start-up. 943B only, inert. |

Note the firmware naming split (`AutoShut*` vs `AutoShutdown*`);
`schemas.py` accepts both spellings, so the console renders whichever the
camera returns.

**Auto Delete Old Files** — the setting the pano log blames for lost images —
is on this page in both UIs (`autoMaintain_autoFileHoldEnable`, w_Auto Delete
File, with `autoMaintain_autoFileHoldDays`, w_Days ago / w_Customize; 943B
`a_d_days` / `am_showAD`) **[v]**, but it has **no** console item: it is not in
the `AutoMaintain` table the console reads. Verify via the camera's web UI only.

## 7. Motion detect

Console: exactly two writable fields (`Enable`, `Level`). Everything else in the
section is read-only raw-viewer material, and the mask itself is edited in the
**Legacy mask** tab. Built-in UI: Setup ▸ Event manage ▸ Video Check **[v]**.

### Writable

| Item | Console | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|---|
| `MotionDetect[0].Enable` | bool | ✔ `true` | ✔ `true` | `videoDetect_title_able0` (w_StartUp) · 943B `v_m_enable` **[v]** | Master motion-detection switch. |
| `MotionDetect[0].Level` | number 1-6, "Level (1-6 sensitivity)" | ✔ `3` | ✔ `3` | `videoDetect_select_sensitivity` (w_Sensitivity) · 943B `v_m_sen` **[v]** | Camera-wide sensitivity. Pano runs 3. The page writes `Level` from that control on save. |

### Read-only (raw viewer)

| Item | 842 | 943 | Built-in web UI | Meaning |
|---|---|---|---|---|
| `MotionDetect[0].EventHandler.RecordEnable` / `.Record` / `.RecordChannels[n]` | ✔ `true` | ✔ `true` | `videoDetect_recordChannel0` (w_RecordChannel) **[v]** | Record to SD on motion. Channel bitmask. |
| `MotionDetect[0].EventHandler.RecordLatch` | ✔ `15` | ✔ `10` | `videoDetect_recordDelay0` (RecordLatch = record delay) **[v]** | Seconds to keep recording after motion stops. |
| `MotionDetect[0].EventHandler.SnapshotEnable` / `.Snapshot` / `.SnapshotChannels[n]` | ✔ `true` | ✔ `true` | `videoDetect_snapTitle0` (w_Snap) **[v]** | Take snapshots on motion — the path that feeds the FTP upload. |
| `MotionDetect[0].EventHandler.SnapshotTimes` | **NA** | ✔ `3` | none — the 943B's page does not render it **[v]** | Number of snapshots per event. 943B only. |
| `MotionDetect[0].EventHandler.Dejitter` | ✔ `5` | ✔ `5` | `videoDetect_antiInput0` / `v_m_anti` (w_RemoveDither) **[v]** | Anti-dither interval (seconds). |
| `MotionDetect[0].EventHandler.Delay` | ✔ `0` | ✔ `0` | none **[v]** | Event delay before firing. |
| `MotionDetect[0].EventHandler.TimeSection[n][n]` (n = 0-6 days × 0-5 periods) | ✔ all `1 00:00:00-23:59:59` on period 0 | ✔ same | `videoDetect_setTimeTable` (w_TimeAlarmPeriod) + `videoDetect_mon`…`sun` **[v]** | Weekly armed schedule. Every day is armed 24 h on both models. |
| `MotionDetect[0].EventHandler.AlarmOutEnable` / `.AlarmOut` / `.AlarmOutChannels[n]` / `.AlarmOutLatch` | ✔ `true` | ✔ `true` | `videoDetect_alarmOut0` (w_Alarm Out), `videoDetect_alarmDelay0` (latch) **[v]** | Alarm-output relay action and latch. |
| `MotionDetect[0].EventHandler.ExAlarmOut*` | ✔ `false` | ✔ `false` | none **[v]** | External alarm output. Not fitted → inert. |
| `MotionDetect[0].EventHandler.LogEnable` | ✔ `true` | ✔ `true` | none **[v]** | Write the event to the camera log. |
| `MotionDetect[0].EventHandler.MailEnable` | ✔ `false` | ✔ `false` | `videoDetect_emailTitle0` (w_Send E-Mail) **[v]** | Email on motion. Requires Mail Settings; off. |
| `MotionDetect[0].EventHandler.MMSEnable` | ✔ `false` | **NA** | none **[v]** | MMS on motion. 842 only, inert. |
| `MotionDetect[0].EventHandler.MessageEnable` | ✔ `false` | ✔ `false` | `videoDetect_sendnoteTitle0` (w_noteLink) **[v]** | Push message to a connected client. |
| `MotionDetect[0].EventHandler.BeepEnable` | ✔ `false` | ✔ `false` | none **[v]** | Audible beep. No speaker → inert. |
| `MotionDetect[0].EventHandler.VoiceEnable` | ✔ `false` | ✔ `false` | none **[v]** | Voice prompt on motion. Inert. |
| `MotionDetect[0].EventHandler.FlashEnable` / `.FlashLatch` | ✔ `false` / `10` | ✔ `false` / `10` | `videoDetect_flashLanchDelayTitle` (w_flashDelay) **[v]** | Alarm flash (white light) and latch. |
| `MotionDetect[0].EventHandler.LightingLink.{Enable,FilckerLightType,FilckerTimes,FilckerIntevalTime}` | **NA** | ✔ `false`, `WhiteLight`, `5`, `5` | none **[v]** | White-light strobe linkage. 943B only, inert. (Note the firmware's "Filcker" spelling.) |
| `MotionDetect[0].EventHandler.TourEnable` / `.Tour` / `.TourChannels[n]` | ✔ `false` | ✔ `false` | none **[v]** | Start a PTZ tour. No PTZ → inert. |
| `MotionDetect[0].EventHandler.MatrixEnable` / `.Matrix` / `.MatrixChannels[n]` | ✔ `false` | ✔ `false` | none **[v]** | Video-matrix (spot) output. NVR-only feature → inert. |
| `MotionDetect[0].EventHandler.PtzLinkEnable` / `.PtzLink[n][n]` | ✔ `false` | ✔ `false` | `videoDetect_ptzTitle0` (w_PtzLink) **[v]** | PTZ preset link. Inert. |
| `MotionDetect[0].EventHandler.TipEnable` | ✔ `false` | ✔ `false` | none **[v]** | On-screen tip. |
| `MotionDetect[0].Region[n]` (n = 0-17) | ✔ | ✔ | `videoDetect_setzone` / `videoDetect_savezone` (w_Setting Area) · 943B `v_m_region` **[v]** | The **legacy 18x22 mask**, 18 rows of 22 bits, LSB-first. Edited in the console's Legacy mask tab, not here. |
| `MotionDetect[0].MotionDetectWindow[n].{Id,Name,Region[n],Sensitive,Threshold,Window[n]}` (n = 0-3) | ✔ (`Region0`-`Region3`, `Sensitive` 60) | ✔ (`Region1`-`Region4`, `Sensitive` 81) | `videoDetect_region_name` (w_Name), `videoDetect_Sensitive_label` (w_Sensitivity), `videoDetect_Threshold_label` (w_Threshold) · 943B `v_m_sen` / `v_m_thr` / `v_m_detzone` **[v]** | The newer window/region model: four named regions each with its own mask, sensitivity and threshold. Only window 0 is populated on these cameras; windows 1-3 are all-zero → **inert**. Region naming differs by model (842 `Region0`…, 943B `Region1`…). |
| `MotionDetect[0].PirMotionEnable` | ✔ `false` | **NA** | none **[v]** | PIR-based motion. 842 only, inert. |
| `MotionDetect[0].PirMotionLevel` | ✔ `3` | ✔ `3` | none **[v]** | PIR sensitivity (unused without PIR). |
| `MotionDetect[0].PtzManualEnable` | **NA** | ✔ `true` | none **[v]** | Manual PTZ control allowed. 943B only. |
| `MotionDetect[0].OsdTwinkleEnable` | **NA** | ✔ `false` | none **[v]** | Blink the OSD on motion. 943B only, inert. |
| `MotionDetect[0].BlindDetect[0].EventHandler.SnapshotTimes` | **NA** | ✔ `1` | `videoDetect_tab_blindDetect` (w_Video Shelter tab) **[v]** | Snapshot count for the separate tamper/blind-detect event. 943B only. |
| `MotionDetect[0].RemoteEventHandler.TimeSection[n][n]` | **NA** | ✔ (cam-09 only) | none **[v]** | Schedule for a remote (alarm-server) event handler. 943B only, and only cam-09's firmware. |

The 842 ships both `videoDetectConfig` and `videoDetectConfig_old`
(`use_old_video_detect` picks one); both were read and they expose the same
controls, so the mapping above holds either way. The 943B has only
`videoDetectConfig`. The page also carries a "Video Shelter" (`BlindDetect`)
tab and a manual-trigger area that the console does not model.

---

## Appendix A — built-in web UI pages with no console counterpart

The console is deliberately limited to seven `configManager` sections. These
built-in pages exist but have no console item (from the IP2M-842 menu scraped
above): Network ▸ WIFI, DDNS, PPPOE, Connect Settings, IP Purview, Mail
Settings, UPNP, SNMP, QOS, Bonjour, Multicast, Auto Register, 3G, IEEE802, VPN,
ATMOsd; Camera Setup ▸ Camera Attribute (image/colour/IR), IVS; Memory Manage ▸
Timetable, Recording Control; System ▸ Local Config, User Management, UserSearch,
PTZ Config, Com Config, Default Setting, Collocate I/O, Firmware Upgrade;
System Info ▸ Edition Info, Log, Online Users, VSP Cfg, LDAP.

Notable consequence: **Auto Delete Old Files** (the Auto Maintain setting the
pano log links to image loss) is not reachable from the console at all.

## Appendix B — firmware variation inside a model

The 842 units are not identical, so a few items are present on some units only:

* `Network.bond0.{DefaultGateway,DhcpEnable,DnsAutoGet,Enable,EnableDhcpReservedIP,MTU,NetMode,PhysicalAddress,SubnetMask,Type}` and `Network.eth0/eth2.{DnsAutoGet,Enable,NetMode,Type}` — cam-04 and cam-06 only (41 Network keys vs 23).
* `MotionDetect[0].Region[12..17]` and `MotionDetectWindow[1..3].Region[1..17]` — cam-05 returns a truncated mask (139 MotionDetect keys vs 202).

The 943B units differ only at cam-09: it adds
`Encode…Video.MaxBitrate` (all profiles), `EventHandler.PtzLink[0][2..4]` and
`RemoteEventHandler.TimeSection[0..6][0..5]` (232 Encode / 253 MotionDetect keys
vs 222 / 208).

## Appendix C — sources and verification status

| Source | What it provided | Status |
|---|---|---|
| `amcrest-console/fixtures/cam-NN-*/20261101-*/config-*.json` | Key inventory, per-model presence, example values | Verified (5× 842, 3× 943B; captured 2026-11-01) |
| `amcrest-console/schemas.py`, `cgi_config.py` | Which items are writable, widget types, ranges, danger flags | Verified (source) |
| `http://192.168.2.121/js/set.js` + `/set.htm` (2026-11-08) | IP2M-842 setup menu and each item's `data-filename` → page module | Verified from the camera |
| `/html/<page>.htm` + `/js/<page>.js` for `encodeConfig`, `audioConfig`, `networkConfig`, `videoDetectConfig`(+`_old`), `recordStorageConfig`(+`_old`), `autoMaintainConfig`, `generalConfig` — from **both** 192.168.2.121 and 192.168.2.127 (2026-11-08) | Field-to-widget mapping: element id ↔ config key ↔ label | Verified from the cameras |
| `agent-files/amcrest-cameras-from-log.md` | Menu paths: Network > TCP/IP, Storage > Destination > FTP, System > Auto Maintain, System > General > Date & Time | Verified (screenshots) — and now confirmed by the page modules |

Reading the page modules required one RPC2 login per camera (`global.login`,
then send `DhWebClientSessionID=<session>`); HTTP Basic/Digest alone gets a 301.
Two logins total, read-only, no config writes.

Still unverified:
* Which of `videoDetectConfig` / `videoDetectConfig_old` (and
  `recordStorageConfig` / `_old`) the 842 firmware actually selects — both
  variants were read and expose the same controls, so the mapping holds either
  way.
* The live key sets date from the 2026-11-01 fixtures; a read-only re-read of
  one camera per model would confirm they are still current.
