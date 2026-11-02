---
update: 2026-11-01 16:24 PST
tags: amcrest-plugin, npapi, obsolete-path
---

# Amcrest / Dahua browser plugin (NPMedia)

The "Amcrest browser plugin" is a Dahua **NPMedia NPAPI** plugin (the Flash-era
Netscape Plugin API). It is **not used by pano at runtime**; it only exists to open
a camera's own web admin UI (`http://<cam>/`) in a browser. Pano itself only serves
JPEG snapshots and uploaded videos (`pano/campage.py`, `pano/www/`).

## Artifacts in this repo

* `amcrest-support/npmedia.bundle/` — expanded plugin bundle, version 3.0.0.0
  (MIME `application/media-plugin-version-3.0.0.0`, "Used to play .dav files").
  Same files as `amcrest-support/amcrest-plugin.zip` (`home/ryu/npmedia.bundle/`).
* `amcrest-support/amcrest-camera-support/webplugin_alps.pkg` — macOS installer downloaded by
  the camera's web UI, package id `mac.dahua.macPluginInstall.npmedia3.0.0.2.pkg`,
  installs plugin version 3.0.0.2 (`MediaPlguin-v-3.2.0.289406`).
* `amcrest-support/amcrest-camera-support/Firefox 51.0b9.dmg` — last NPAPI-capable Firefox.
* `amcrest-support/amcrest-camera-support/README.md` — notes: old x86 Mac (e.g. macOS 10.13)
  + Firefox 51 + NP Media plugin.

## Packaging / install

* Both plugin builds are **32-bit i386 Mach-O** bundles (`BRPL`), built with
  Xcode 4.5.2 / MacOSX10.8 SDK around 2015.
* The `.pkg` is an Apple xar archive containing `Distribution`, `npmedia3002.pkg`
  (`PackageInfo`, `Bom`, gzip+cpio `Payload`, `Scripts`). It installs to
  `/Library/Internet Plug-Ins` as root (`auth="root"`).
* The postinstall script is trivial:
  `sudo chmod -R 777 /Library/Internet Plug-Ins/npmedia3.0.0.2.bundle`
* Payload is `npmedia3.0.0.2.bundle` with `Contents/MacOS/npmedia3.0.0.2` plus
  `Contents/Frameworks/*` and BMP/CUR UI resources.

## Browser-glue layer (`Contents/MacOS/npmedia`)

* Implements the NPAPI contract: `NPP_New`, `NPP_Destroy`, `NPP_SetWindow`,
  `NPP_HandleEvent`, `NPP_NewStream`, `NPP_GetValue`, `NPP_Write`, etc., plus
  `NS_PluginInitialize` / `NS_PluginShutdown`. Uses `nsPluginInstanceBase`,
  `nsPluginInstance` and a `ScriptablePluginObject` / `ScriptablePluginObjectBase`.
* Requires the **Cocoa event model**; logs "Cocoa event model not supported,
  can't create a plugin instance." and "CoreAnimation drawing model not
  supported..." if the browser/host is too old. Handles `NPCocoaEvent` mouse,
  keyboard, scroll and draw events.
* Exposes a scriptable JS API (method/property table, ~100 methods) that the
  camera's web page calls: `LoginDevice`, `LoginDeviceEx`, `LoginDeviceSSL`,
  `LogoutDevice`, `ConnectRealVideo`, `ConnectRealVideoEx`, `ConnectAllChannelEx`,
  `DisConnectRealVideo`, `PlayBack`, `PlayBackByRecordFileEx`, `PlayBackByTimeEx`,
  `PausePlayBack`, `FastPlayBack`, `ControlPtz`, `ControlPtzFisheye`,
  `ControlTalking`, `SetIVSConfig`, `ShowIVSDlg`, `GetDevConfig`/`DevConfig`,
  `DownloadByTime`, `DownloadByRecordFile`, `GetChannelTotal`/`GetChannelName`,
  `SetGridNum`, `SetVolume`/`PlaySetVolume`, `OnFullScreenClk`, `AboutBox`, etc.
  Version 3.0.0.2 adds features such as heat maps, video analysis shapes,
  `ControlVideoStable`, `ControlFe`, `GetUserDirectory`, `GetVersion`.

## SDK layers (`Contents/Frameworks/`)

Rendering / player:

* `libdhplay.so` — Dahua player/decoder: bundled FFmpeg-derived decoders
  (`DH_*`, H.264, MJPEG, MPEG4, AAC, AMR), stream parsing, CoreAudio playback,
  YUV/OpenGL render callback (`PLAY_OpenYuvRender`), frame callbacks.
* `libVideoLayer.dylib` — window/grid/overlay renderer using CoreGraphics
  (`CGContext*`), CoreText, QuartzCore/CoreAnimation and OpenGL; OSD and IVS shape
  drawing, window sizing, toolbars (audio, snapshot, local record, zoom, resize).
* `libDHSurveillance.dylib` — surveillance facade; wraps network/playback calls.

Network / device:

* `libdhnetsdk.so` — Dahua network SDK. Key exports: `CLIENT_Init`,
  `CLIENT_LoginEx`, `CLIENT_Logout`, `CLIENT_RealPlayEx`, `CLIENT_StopRealPlay`,
  `CLIENT_PlayBackByTimeEx`, `CLIENT_PlayBackByRecordFileEx`,
  `CLIENT_QueryRecordFile`, `CLIENT_DownloadByTime/ByRecordFile`,
  `CLIENT_PTZControl`/`CLIENT_DHPTZControlEx`, `CLIENT_GetDevConfig`,
  `CLIENT_QueryDevState`, `CLIENT_StartTalkEx`/`CLIENT_TalkSendData`,
  `CLIENT_SetRealDataCallBack`, `CLIENT_SetAutoReconnect`, etc.
  Uses Dahua's private DVRIP protocol (default TCP 37777); config strings include
  `ServicePort`, `HttpPort`, `RtspPort`; `CLIENT_GetDVRIPByResolveSvr` for P2P/DDNS.
* `libdhdvr.so` — older DVR API (legacy devices).
* `libdhjson.so` — JSON config/parsing helper.

## Why Firefox 51 is required

NPAPI support was removed from Chrome 45 and Firefox 52, and these are 32-bit
Intel binaries. So the plugin only loads on x86 macOS with Firefox ≤ 51 (hence the
51.0b9 dmg). It does not work on modern macOS or Apple Silicon (mac-mini-2024);
`agent-files/pano-log-chronology.md` records repeated crashes and the fallback to
the Amcrest iOS app / old x86 Mac.

## Status on macOS 26 (Tahoe) — 2026-11-01

Firefox 51.0b9 does **not** run on an x86 Mac running macOS 26 (Tahoe). The
plugin is 32-bit i386, and macOS 26 has no 32-bit support; Rosetta 2 also does
not support i386. The old "x86 Mac + Firefox 51 + NPMedia" path is therefore
dead on this machine.

The plugin only provides the live-video widget. The camera's login page and CGI
API still work in modern browsers:

* `http://<cam>/` loads and accepts the admin login.
* `http://<cam>/cgi-bin/configManager.cgi?action=getConfig&name=MotionDetect`
  returns the motion config after Basic/Digest auth.
* The old UI's live view/plugin is what fails.

Use the CGI API or the replacement console (`amcrest-console-plan.md`); do not
try to run Firefox 51 on Tahoe.

## Operational notes

* Modern replacement plan (ARM Mac, plugin-free Config + mask-editing Live View):
  see `agent-files/amcrest-modern-access.md` and
  `agent-files/amcrest-console-plan.md`.

* Legacy procedure, only for an old x86 macOS VM/host (e.g. macOS 10.13):
  install Firefox 51, install the NPMedia plugin, browse to the camera's IP,
  log in. This procedure does **not** apply to macOS 26.
* If the plugin misbehaves, clear Firefox history/cookies and relaunch
  (`agent-files/network-and-misc-from-log.md`).
* Firefox 51 must not auto-update (updates break NPAPI).
* On Apple Silicon, a VM/container with x86 macOS High Sierra would be needed
  (discussed but not implemented).
* Pano never imports/invokes the plugin; no code references exist in
  `pano/*.py`, `pano/www/`, or configs.
