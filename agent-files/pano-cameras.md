---
update: 2026-11-08 PST
tags: camera-inventory
---

# Project Panopticon — cameras

**This table is the inventory of record** for camera identity (model, location, MACs,
IPs, firmware, serial). Up/down observations are a dated snapshot; the current probe
log is `amcrest-camera-contact.md`.

Provenance: base table is the source doc's "Project Panopticon Cameras", imported via
`pano-log-overview.md`, from which this file was extracted on 2026-11-08. Model, auth,
active IP and firmware were added from the 2026-11-01/11-06 probes and
`pano/pano-docker.json`.

Status columns are **as of the 2026-11-01 sweep**, with `*` = CGI read verified again on
2026-11-06. Interfaces are up/down per that sweep; see `amcrest-camera-contact.md` for
the latest probe.

| Name | Model | Iface | Location | Pano desc | WiFi MAC | WiFi IP | WiFi status | Wired MAC | Wired IP | Wired status | Active IP | Auth | In config | Firmware | Serial |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cam-00 | IP2M-842 | | front looking south | front looking south (`@camera_list`, commented) | 3c:ef:8c:9c:85:6d | 192.168.2.120 | down | 9c:8e:cd:00:a4:b5 | 192.168.2.130 | down | — | Basic | no | | AMC0028VA32S795UUB |
| cam-01 | IP2M-842 | wifi | porch | porch | 4c:11:bf:f5:89:a0 | 192.168.2.121 | up; Basic CGI OK* | 3c:ef:8c:64:fa:93 | 192.168.2.131 | down | 192.168.2.121 | Basic | yes | 2.212.0000.2.R (2016-08-11) | AMC002A34HATK2G7HH |
| cam-02 | IP2M-842 | | | — | 3c:ef:8c:9c:85:c5 | 192.168.2.122 | down | 9c:8e:cd:00:a4:4c | 192.168.2.132 | down | — | Basic | no | | AMC002768U5C4RHDK5 |
| cam-03 | IP2M-842 | wifi | alley/look south | alley looking south | 4c:11:bf:f4:48:91 | 192.168.2.123 | up; Basic CGI OK* | 4c:11:bf:e4:7b:b7 | 192.168.2.133 | down | 192.168.2.123 | Basic | yes | | AMC0027049793x76D1 |
| cam-04 | IP2M-842 | both | alley/look north | alley looking north | 3c:ef:8c:87:3c:2d | 192.168.2.124 | up; Basic CGI OK* | 3c:ef:8c:96:1b:19 | 192.168.2.134 | up; CGI OK* | 192.168.2.134 | Basic | yes | | AMC002A47KTRBGDT10 |
| cam-05 | IP2M-842 | wifi | deck | side deck | 3c:ef:8c:9c:87:86 | 192.168.2.125 | up; Basic CGI OK* | 9c:8e:cd:00:a2:a2 | 192.168.2.135 | down | 192.168.2.125 | Basic | yes | | AMC0021AFXD4837U12 |
| cam-06 | IP2M-842 | wifi | backyard/look N | back yard/look-north | 3c:ef:8c:9c:83:43 | 192.168.2.126 | up; Basic CGI OK* | 9c:8e:cd:00:a6:e7 | 192.168.2.136 | down | 192.168.2.126 | Basic | yes | | AMC002U5127780784R |
| cam-07 | IP3M-943B | wifi | front/look north | front/look-north/2021 | 9c:8e:cd:0d:2b:56 | 192.168.2.127 | up; CGI OK* | 9c:8e:cd:0d:27:6e | 192.168.2.137 | down | 192.168.2.127 | Digest | yes | 2.400.AC02.15.R (2017-07-31) | AMC0184DF01N44 |
| cam-08 | IP3M-943B | both | front/look north | front/look-north/2022 | 9c:8e:cd:0d:3a:89 | 192.168.2.128 | up; CGI OK* | 9c:8e:cd:0d:36:a1 | 192.168.2.138 | up; CGI OK* | 192.168.2.138 | Digest | yes | 2.400.AC02.15.R (2017-07-31) | AMC018T127Y2F424P2 |
| cam-09 | IP3M-943B | wifi | front/look south | front/look-south/2022 | 9c:8e:cd:12:f6:c6 | 192.168.2.129 | up; CGI OK* | 9c:8e:cd:12:f2:ce | 192.168.2.139 | intermittent (up, then down) | 192.168.2.129 | Digest | yes | 2.400.AC02.15.R (2017-07-31) | AMC01861PG72172R3Q |
| cam-10 | IP3M-943B? | | | — | ? | 192.168.2.119 | down | 9c:8e:cd:0f:c9:71 | 192.168.2.140 | down | — | Digest? | no | | AMC018GK64Q92016DM |
| cam-11 | IP3M-943B? | | | — | 9c:8e:cd:0f:cf:be | 192.168.2.118 | down | 9c:8e:cd:0f:cb:d6 | 192.168.2.141 | down | — | Digest? | no | | AMC018X9031328K52C |

Column notes:

- **Model** — hardware model from the probe; `?` means never contacted, inferred from the
  serial family. `pano/pano-docker.json` uses the slugs `amcrest-ip2m-842` /
  `amcrest-ip3m-943`.
- **Location / Pano desc** — Location is the source doc's label; Pano desc is the
  `description` field in `camera_list`.
- **Active IP** — the address `pano/pano-docker.json` actually contacts (`admin_url`).
  cam-04 and cam-08 are reached on their **wired** addresses; the rest on Wi-Fi.
- **Auth** — Basic (IP2M-842) or Digest (IP3M-943B). The IP2M-842 counts an
  unauthenticated `/cgi-bin` request as a failed login, so send Basic preemptively.
- **Firmware** — blank where unrecorded. The IP2M-842's
  `magicBox.cgi?action=getSoftwareVersion` crashes its web server, so cam-01's version
  was read from the camera's own web page; the IP3M-943B version came from the CGI.
- **cam-00** is in the doc with no location; the value here is recovered from the
  commented-out `@camera_list` entry in `pano-docker.json`. It is not in the active
  config.

Notes (from the doc):

- WiFi addresses are DHCP (reserved via the Google WiFi router app; see robertyu.org
  network notes).
- All wired addresses are statically configured on the camera itself, **not** from the
  router app (redundant settings cause no communications). This lets you always reach a
  camera over a cable even if the router is down.
- Values above were reconstructed from the rendered page (the raw `pdftotext` output
  scrambles the table's multi-line cells). They match the source.
- **Source error:** cam-10's WiFi MAC (`9c:8e:cd:12:f6:c6`) is identical to cam-09's —
  an obvious author copy/paste typo. cam-10's real WiFi MAC is unverified, so the cell
  is left as `?`.
- **Dropped 2026-11-08:** the source table's `Reboot` column held each camera's daily
  auto-reboot time (cam-01 7:20, cam-03 13:33, cam-04 14:22, cam-05 15:55, cam-06 16:06,
  cam-07 14:44, cam-08 10:03, cam-09 11:11). It duplicates the live
  `AutoMaintain.AutoReboot*` config, so see `amcrest-config-reference.md` and
  `amcrest-cameras-from-log.md` instead of a stale copy here.

## Related

- `pano-log-overview.md` — pano-log quick reference (endpoints, directories, external
  links, BUGS/ENHANCEMENTS).
- `amcrest-camera-contact.md` — dated probe results (reachability, auth, ARP).
- `amcrest-config-reference.md` — per-item camera Configuration-tab reference.
- `pano-procedures.md` — procedure for adding a camera / editing `pano-docker.json`.
