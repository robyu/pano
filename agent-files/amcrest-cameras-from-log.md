# Amcrest camera configuration (from Project Panopticon Log)

Source: embedded screenshots in `~/pano-log.pdf` ("Project Panopticon Log"), pages
noted. **Credentials (FTP user/password, admin logins, WiFi password) are omitted.**
These screenshots span several eras, so values may not match the current camera table.

## Camera network identity (Network > TCP/IP)

| Host   | Interface          | Mode             | MAC               | IP             | Subnet        | Gateway     | DNS                 | pg   |
|--------|--------------------|------------------|-------------------|----------------|---------------|-------------|---------------------|------|
| cam-09 | Wireless (default) | DHCP             | 9c:8e:cd:12:f6:c6 | 192.168.2.129  | 255.255.255.0 | 192.168.2.1 | 192.168.2.1 / 1.0.0.1 | p27 |
| cam-09 | Wired (default)    | Static           | 9c:8e:cd:12:f2:ce | 192.168.2.139  | 255.255.255.0 | 192.168.2.1 | 192.168.2.1 / 1.0.0.1 | p28 |
| cam-00 | Wireless (default) | DHCP             | 3c:ef:8c:9c:85:6d | 192.168.2.120  | 255.255.255.0 | 192.168.2.1 | 192.168.2.1 / 0.0.0.0 | p37, p72 |
| cam-03 | Wired (default)    | DHCP             | 9c:8e:cd:09:fd:f9 | 192.168.2.123  | 255.255.255.0 | 192.168.2.1 | 192.168.2.1         | p62  |

- `Enable ARP/Ping to set IP address service` is checked on these pages.
- The wired interface is configured static and set as the default, matching the log
  note that wired addresses are fixed so a cable connection works without DHCP.
- cam-03's MAC here (9c:8e:cd:09:fd:f9) differs from the current camera table
  (4c:11:bf:...), confirming the screenshots span different units/eras.

## FTP upload (Storage > Destination > FTP)

- All cameras upload to the vsftpd server at **192.168.2.8:21**.
- Each camera uses its own **Remote Directory = the camera name** (screenshots: cam-09,
  cam-00, cam-07). Upload `Enable` checked; `Emergency (Store on SD Card)` unchecked.
- Known bug: pressing `Test` returns **"FTP server test failure, list right loss."**
  (Amcrest firmware bug; uploads still work). Manual FTP from another host confirms
  the server is fine.

## Auto Maintain (System > Auto Maintain)

Observed schedules:
- p10: Auto Reboot **off**, Auto Delete Old Files **off**.
- p12 (one cam): Auto Reboot "Everyday" **14:44**; Auto Delete off.
- p12 (another cam): Auto Reboot "Everyday" **10:03**; Auto Delete off.
- p101: Auto Reboot "Everyday" **07:00**; Auto Delete Old Files "Customized **1** day(s) ago".

This matches the log finding that disabling the daily reboot stopped the cameras from
deleting older images; Auto Delete must stay off for multi-day retention.

## Date & Time (System > General > Date & Time)

- p17: Time Zone **GMT-08:00**; format Year-Month-Day; 24-hour; current
  **2022-04-02 10:14:30**; `Sync with NTP Server` checked (server **clock.isc.org**,
  port 123, update every 10 min); DST **off**.
- p63: Time Zone **GMT-07:00**; current **2018-11-15 10:05:02**; NTP clock.isc.org;
  DST off.

Consistent with the log notes on DST being disabled and NTP/DST time drift.

## Video / Encode settings (observed variants)

- p73: Main **1080P (1920x1080)** @10fps, VBR, quality **6 (Best)**, bitrate 2048,
  frame interval 20; Sub-stream enabled, **VGA (640x480)** @10fps, VBR, quality 6,
  bitrate 1024. Watermark "amcrest0".
- p75: Main **720P (1280x720)** @10fps, CBR, bitrate **448**, interval 20; watermark
  "amcrest0".
- p103: Main **720P** @10fps, CBR, bitrate **2048**, interval **40**.
- p112: Main **1080P** @**20fps**, CBR, bitrate **4096**, interval 40 (20~150).

All H.264 (some H.264H). The camera does its own encoding.

## P2P / serial numbers

P2P is enabled and reported Online, with a QR code. Observed serials:
- **AMC0028VA32S795UUB** — matches cam-00 in the camera table (p70, p113).
- **AMC002A34HATK2G7HH** — matches cam-01 (p70).
- **AMC018LLJ49E3GSV0T** — older unit, near the "/123" era (p62).
- **AMC00232F30418811T** — p71.

Serials are device identifiers (used for P2P and for the Google Home app), not
credentials.

## Amcrest mobile app onboarding (Amcrest View) — new camera / serial lookup

Screens p20–p26. Flow:
1. Device Manager → `+` (or `Add Device`).
2. Select Device Type: **WiFi Camera / PoE Camera / DVR/NVR / Search Device**.
3. Connection Type: "Set Up A New Camera On WiFi" → **WiFi Configuration Setup**
   (most common/quickest) or **Ethernet WiFi Setup** (most stable); or "Add An Already
   Connected Camera".
4. Ethernet WiFi Setup: phone on WiFi → connect Ethernet cable router→camera, wait
   ~10 s for green LED → **Scan QR Code** (or `Enter S/N Manually`) → confirm the
   indicator is solid green → enter WiFi password (note: most Amcrest cameras are
   **2.4 GHz only**; IP3M-941B/W and IP3M-HX2B/W support 2.4/5 GHz) → Camera Login:
   name the device (`cam-NN`), provide username/password (default `admin` login,
   max 32 chars) → **"Camera Successfully Connected"** → remove cable, wait 30 s,
   `Start Live View`.
5. Device Manager then lists cams (cam-00..cam-10). Tap a device → edit → details page
   shows **Type: P2P**, Device Name, **S/N**, username, Live View. The S/N is what you
   need to add the camera in the Google Home app.

Notes from the log context: the camera WiFi used is the dedicated 2.4 GHz network
(SSID/password omitted); enabling the substream was needed for iOS app streaming;
disabling daily reboot stopped the cameras deleting older images.
