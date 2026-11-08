#!/usr/bin/env python3
"""Phase 0 discovery for Amcrest/Dahua cameras.

Read-only by default. It fetches device identity, selected config sections, and
a snapshot, then writes sanitized JSON/text fixtures for later development.

Auth is handled explicitly: Basic via a preemptive Authorization header, Digest
via a separate opener. Basic is sent on the first request because the IP2M-842
counts an unauthenticated /cgi-bin request as a failed login and can lock out
the client for ~300s. With --auth auto, the camera model is used to choose
Basic (IP2M-842) or Digest (IP3M-943); without a model, Basic is tried first and
Digest is used only if the camera challenges for it. The IP2M-842 web server is
slow/single-connection, so avoid rapid parallel requests, add --request-delay,
and use a long timeout. Its getSoftwareVersion action crashes/restarts the web
server, so that action is skipped for IP2M-842 and fetched only for other
models.

The only code path that writes to the camera is --verify-mask-write, which
requires --yes. It toggles exactly one bit in the legacy Region[0] while sending
all 18 rows (this camera resets omitted rows), reads the full mask back, and
restores the original 18 rows. Do not use it unless you accept that temporary
mask change. The 4-window MotionDetectWindow model is read-only here: writing
window Region values returns OK but does not persist and can reset the legacy
mask.

Examples:
  python3 discover.py --ip 192.168.2.123 --name cam-03 \\
      --pano-config ../pano/pano-docker.json

  AMCREST_PASSWORD=... python3 discover.py --ip 192.168.2.123

Password precedence: --pano-config, then $AMCREST_PASSWORD, then an interactive
getpass prompt. Passwords are never written to fixtures or printed.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from camera import (
    COLS,
    ROWS,
    SECTIONS,
    AuthError,
    CameraClient,
    CameraError,
    ascii_mask,
    decode_region_rows,
    jpeg_dimensions,
    parse_kv,
    parse_mask,
    redact_text,
    sanitize,
    skip_software_version,
)
import credentials

# Re-exported from credentials so existing callers keep working.
load_pano_camera = credentials.load_pano_camera
resolve_credentials = credentials.resolve_credentials


def verify_legacy_mask(client: CameraClient, mask: Dict[str, Any]) -> None:
    if not mask.get("legacy"):
        print(
            "No legacy mask found; window-only write verification is not "
            "supported on this camera."
        )
        return
    original = [int(value) for value in mask["legacy"]]
    trial = list(original)
    trial[0] ^= 1
    print(
        "Trial write MotionDetect[0].Region[0]: {} -> {} (all 18 rows)".format(
            original[0], trial[0]
        )
    )
    response = client.set_legacy_regions(trial)
    print("  setConfig response: {}".format(redact_text(response)))
    try:
        after = client.get_motion()
        read_back = after.get("legacy")
        print(
            "  read-back matches trial: {}".format(read_back == trial)
        )
    finally:
        restore = client.set_legacy_regions(original)
        print("  restore response: {}".format(redact_text(restore)))
        final = client.get_motion()
        print(
            "  restored original: {}".format(final.get("legacy") == original)
        )


def verify_mask_write(
    client: CameraClient,
    mask: Dict[str, Any],
    confirmed: bool,
) -> None:
    if not confirmed:
        print("Not verifying mask write: pass --yes to allow one temporary cell toggle.")
        return
    verify_legacy_mask(client, mask)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(sanitize(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Amcrest/Dahua camera discovery (phase 0).",
    )
    parser.add_argument("--ip", required=True, help="camera IPv4/IPv6 address")
    parser.add_argument("--name", help="camera label for output and pano lookup")
    parser.add_argument("--camera-port", type=int, default=80)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password-env", default="AMCREST_PASSWORD")
    parser.add_argument(
        "--pano-config",
        help="read credentials for --ip from a pano JSON config",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--auth",
        choices=("auto", "basic", "digest"),
        default="auto",
        help="HTTP auth: auto uses the model, else Basic then Digest challenge",
    )
    parser.add_argument(
        "--model",
        help="camera model, used by --auth auto (e.g. amcrest-ip2m-842)",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=None,
        help="seconds between requests (default: 1.0 for IP2M-842, else 0)",
    )
    parser.add_argument(
        "--sections",
        default=",".join(SECTIONS),
        help="comma-separated config section names",
    )
    parser.add_argument("--no-snapshot", action="store_true")
    parser.add_argument(
        "--output-dir",
        help="fixture directory (default: amcrest-console/fixtures/<name>-<ip>/<timestamp>)",
    )
    parser.add_argument(
        "--verify-mask-write",
        action="store_true",
        help=(
            "toggle one legacy mask cell using a full 18-row write, read it "
            "back, and restore it (requires --yes)"
        ),
    )
    parser.add_argument("--yes", action="store_true", help="confirm mask write")
    args = parser.parse_args(argv)

    try:
        camera_ip = str(ipaddress.ip_address(args.ip))
    except ValueError as error:
        parser.error("invalid --ip: {}".format(error))

    try:
        name, user, password, model = credentials.resolve_credentials(args)
        request_delay = args.request_delay
        if request_delay is None:
            request_delay = 1.0 if "ip2m" in model.lower() else 0.0
        client = CameraClient(
            camera_ip,
            args.camera_port,
            user,
            password,
            timeout=args.timeout,
            auth=args.auth,
            model=model or None,
            request_delay=request_delay,
        )
        started = datetime.now().astimezone().isoformat(timespec="seconds")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = (
                Path(__file__).resolve().parent
                / "fixtures"
                / "{}-{}".format(name, camera_ip)
                / timestamp
            )
        output_dir.mkdir(parents=True, exist_ok=True)

        metadata: Dict[str, Any] = {
            "started": started,
            "camera": {
                "name": name,
                "ip": camera_ip,
                "port": args.camera_port,
                "model": model or None,
            },
            "auth": {"requested": args.auth, "used": None},
            "magic": {},
            "errors": [],
        }
        for action in ("getMachineName", "getDeviceType"):
            try:
                metadata["magic"][action] = client.magic(action)
            except CameraError as error:
                metadata["errors"].append(
                    {"magicBox": action, "error": str(error)}
                )

        device_type = metadata["magic"].get("getDeviceType", {})
        if skip_software_version(model, device_type.get("type")):
            metadata["magic_skipped"] = ["getSoftwareVersion"]
        else:
            try:
                metadata["magic"]["getSoftwareVersion"] = client.magic(
                    "getSoftwareVersion"
                )
            except CameraError as error:
                metadata["errors"].append(
                    {"magicBox": "getSoftwareVersion", "error": str(error)}
                )

        sections_requested = [s.strip() for s in args.sections.split(",") if s.strip()]
        section_data: Dict[str, Any] = {}
        section_configs: Dict[str, Dict[str, str]] = {}
        for section in sections_requested:
            try:
                values, duplicates, raw = client.get_config(section)
                section_configs[section] = values
                section_data[section] = {
                    "duplicates": duplicates,
                    "values": values,
                    "raw": raw,
                }
                write_json(output_dir / "config-{}.json".format(section), section_data[section])
            except CameraError as error:
                metadata["errors"].append(
                    {"section": section, "error": str(error)}
                )

        mask = None
        if "MotionDetect" in section_configs:
            mask = parse_mask(section_configs["MotionDetect"])
            write_json(output_dir / "mask.json", mask)
            if mask.get("legacy"):
                (output_dir / "mask-legacy.txt").write_text(
                    ascii_mask(decode_region_rows(mask["legacy"])) + "\n",
                    encoding="utf-8",
                )
            for index, window in enumerate(mask.get("windows") or []):
                if window.get("regions"):
                    (output_dir / "mask-window-{}.txt".format(index)).write_text(
                        ascii_mask(decode_region_rows(window["regions"])) + "\n",
                        encoding="utf-8",
                    )

        snapshot_info: Dict[str, Any] = {}
        if not args.no_snapshot:
            try:
                headers, body = client.snapshot()
                snapshot_path = output_dir / "snapshot.jpg"
                snapshot_path.write_bytes(body)
                dimensions = jpeg_dimensions(body)
                snapshot_info = {
                    "path": str(snapshot_path),
                    "bytes": len(body),
                    "content_type": headers.get("Content-Type"),
                    "dimensions": list(dimensions) if dimensions else None,
                }
            except CameraError as error:
                metadata["errors"].append({"snapshot": str(error)})

        metadata["auth"]["used"] = client.auth_scheme
        metadata["sections"] = sections_requested
        metadata["snapshot"] = snapshot_info
        write_json(output_dir / "metadata.json", metadata)

        print("Camera: {} ({}) at {}".format(name, camera_ip, started))
        print(
            "Model: {}  Auth: {} (requested {})  Request delay: {}s".format(
                model or "(unknown)", client.auth_scheme, args.auth, request_delay
            )
        )
        if metadata.get("magic_skipped"):
            print(
                "Skipped: {} (IP2M-842 firmware crashes/restarts its web server)".format(
                    ", ".join(metadata["magic_skipped"])
                )
            )
        if metadata["magic"]:
            print("Identity:")
            for action, values in metadata["magic"].items():
                print("  {}: {}".format(action, sanitize(values)))
        print("Fixtures: {}".format(output_dir))
        print("Sections: {}".format(", ".join(sorted(section_configs)) or "(none)"))
        if mask:
            print(
                "Motion mask model: legacy={} windows={}".format(
                    bool(mask.get("legacy")), len(mask.get("windows") or [])
                )
            )
            if mask.get("legacy"):
                print("Legacy mask (18x22, #=monitored):")
                print(ascii_mask(decode_region_rows(mask["legacy"])))
            for index, window in enumerate(mask.get("windows") or []):
                if window.get("regions"):
                    print(
                        "Window {} ({}, sensitive={}, threshold={}):".format(
                            index,
                            window.get("name"),
                            window.get("sensitive"),
                            window.get("threshold"),
                        )
                    )
                    print(ascii_mask(decode_region_rows(window["regions"])))
        if snapshot_info:
            print(
                "Snapshot: {} bytes, dimensions={}".format(
                    snapshot_info.get("bytes"), snapshot_info.get("dimensions")
                )
            )
        if metadata["errors"]:
            print("Warnings:")
            for error in metadata["errors"]:
                print("  {}".format(sanitize(error)))
        if args.verify_mask_write and mask:
            verify_mask_write(client, mask, args.yes)
        return 0
    except AuthError as error:
        print("Authentication error: {}".format(error), file=sys.stderr)
        return 2
    except CameraError as error:
        print("Camera error: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
