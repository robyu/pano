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
  python3 discover.py --camera-ip 192.168.2.123 --name cam-03 \\
      --pano-config ../pano/pano-docker.json

  AMCREST_PASSWORD=... python3 discover.py --camera-ip 192.168.2.123

Password precedence: --pano-config, then $AMCREST_PASSWORD, then an interactive
getpass prompt. Passwords are never written to fixtures or printed.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import http.client
import ipaddress
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROWS = 18
COLS = 22
SECTIONS = [
    "General",
    "Network",
    "NAS",
    "NTP",
    "Encode",
    "AutoMaintain",
    "MotionDetect",
]
SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|pwd|secret|token|credential|private)", re.IGNORECASE
)
SENSITIVE_LINE_RE = re.compile(
    r"(?im)^([^=\r\n]*(?:password|passwd|pwd|secret|token|credential|private)"
    r"[^=\r\n]*)=.*$"
)
SENSITIVE_PARAM_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|credential|private)(=)[^&\s]+"
)
USERINFO_RE = re.compile(r"://[^/@\s]+@")


class CameraError(RuntimeError):
    pass


class AuthError(CameraError):
    pass


def redact_text(text: str) -> str:
    text = SENSITIVE_LINE_RE.sub(r"\1=<redacted>", text)
    text = SENSITIVE_PARAM_RE.sub(r"\1\2<redacted>", text)
    text = USERINFO_RE.sub("://<redacted>@", text)
    return text


def header_value(headers: Any, name: str) -> str:
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return ""


def skip_software_version(model: Optional[str], device_type: Optional[str]) -> bool:
    known_type = (model or "").lower()
    if not known_type:
        known_type = (device_type or "").lower()
    return (not known_type) or ("ip2m" in known_type)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): ("<redacted>" if SENSITIVE_KEY_RE.search(str(k)) else sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def parse_kv(text: str) -> Tuple[Dict[str, str], List[str]]:
    """Parse Dahua key=value lines, stripping the table. prefix."""
    values: Dict[str, str] = {}
    duplicates: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("table."):
            key = key[len("table."):]
        if key in values:
            duplicates.append(key)
        values[key] = value
    return values, duplicates


def decode_region_rows(region_values: List[int]) -> List[List[int]]:
    return [[(int(value) >> col) & 1 for col in range(COLS)] for value in region_values]


def ascii_mask(rows: List[List[int]]) -> str:
    lines = ["".join("#" if bit else "." for bit in row) for row in rows]
    return "\n".join(lines)


def parse_mask(config: Dict[str, str], channel: int = 0) -> Dict[str, Any]:
    prefix = "MotionDetect[{}]".format(channel)
    result: Dict[str, Any] = {
        "enable": config.get(prefix + ".Enable"),
        "level": config.get(prefix + ".Level"),
        "legacy": None,
        "windows": [],
    }

    legacy_values: List[int] = []
    for row in range(ROWS):
        key = "{}.Region[{}]".format(prefix, row)
        if key not in config:
            legacy_values = []
            break
        try:
            legacy_values.append(int(config[key], 0))
        except ValueError:
            legacy_values = []
            break
    if len(legacy_values) == ROWS:
        result["legacy"] = legacy_values

    for window in range(4):
        wprefix = "{}.MotionDetectWindow[{}]".format(prefix, window)
        if wprefix + ".Id" not in config and wprefix + ".Region[0]" not in config:
            continue
        window_values: List[int] = []
        for row in range(ROWS):
            key = "{}.Region[{}]".format(wprefix, row)
            try:
                window_values.append(int(config[key], 0))
            except (KeyError, ValueError):
                window_values = []
                break
        result["windows"].append(
            {
                "id": config.get(wprefix + ".Id"),
                "name": config.get(wprefix + ".Name"),
                "sensitive": config.get(wprefix + ".Sensitive"),
                "threshold": config.get(wprefix + ".Threshold"),
                "regions": window_values if len(window_values) == ROWS else None,
            }
        )
    return result


class CameraClient:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout: float = 15.0,
        auth: str = "auto",
        model: Optional[str] = None,
        request_delay: float = 0.0,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout
        self.base = "http://{}:{}".format(host, port)
        self.model = model
        self.request_delay = max(0.0, request_delay)
        self._last_request: Optional[float] = None
        self._auth_scheme: Optional[str] = None
        if auth in ("basic", "digest"):
            self._auth_scheme = auth
        elif auth == "auto" and model:
            lowered = model.lower()
            if "ip2m-842" in lowered:
                self._auth_scheme = "basic"
            elif "ip3m-943" in lowered:
                self._auth_scheme = "digest"
        self._headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Connection": "close",
        }
        self._opener = urllib.request.build_opener()
        self._digest_opener: Optional[urllib.request.OpenerDirector] = None

    @property
    def auth_scheme(self) -> str:
        return self._auth_scheme or "auto"

    def _throttle(self) -> None:
        if self._last_request is not None and self.request_delay > 0:
            remaining = self.request_delay - (time.monotonic() - self._last_request)
            if remaining > 0:
                time.sleep(remaining)

    def _reach_error(self, error: BaseException) -> CameraError:
        reason = getattr(error, "reason", error)
        hint = ""
        if isinstance(
            error,
            (ConnectionResetError, ConnectionRefusedError, http.client.RemoteDisconnected),
        ) or isinstance(
            reason, (ConnectionResetError, ConnectionRefusedError, http.client.RemoteDisconnected)
        ):
            hint = (
                " (IP2M-842 may be in a login lockout, or its web server may "
                "be restarting after a bad CGI action; stop probing, wait "
                "several minutes, then retry once)"
            )
        return CameraError(
            "cannot reach {}: {}{}".format(self.base, reason, hint)
        )

    def _digest_opener_for(self) -> urllib.request.OpenerDirector:
        if self._digest_opener is None:
            password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(
                None, self.base + "/", self.user, self.password
            )
            self._digest_opener = urllib.request.build_opener(
                urllib.request.HTTPDigestAuthHandler(password_manager)
            )
        return self._digest_opener

    @staticmethod
    def _open(
        opener: urllib.request.OpenerDirector,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ) -> Tuple[int, Dict[str, str], bytes]:
        request = urllib.request.Request(url, headers=headers or {})
        with opener.open(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()

    def _basic_get(
        self, url: str, allow_401: bool = False
    ) -> Tuple[int, Dict[str, str], bytes]:
        token = base64.b64encode(
            "{}:{}".format(self.user, self.password).encode("utf-8")
        ).decode("ascii")
        headers = {"Authorization": "Basic " + token}
        headers.update(self._headers)
        try:
            return self._open(self._opener, url, headers, self.timeout)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                if allow_401:
                    return error.code, dict(error.headers), error.read()
                raise AuthError(
                    "basic authentication failed (401) for {}".format(
                        redact_text(url)
                    )
                )
            body = error.read().decode("utf-8", "replace")
            raise CameraError(
                "HTTP {} for {}: {}".format(
                    error.code, redact_text(url), redact_text(body)[:300]
                )
            )
        except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
            raise self._reach_error(error)

    def _digest_get(self, url: str) -> Tuple[int, Dict[str, str], bytes]:
        try:
            return self._open(
                self._digest_opener_for(), url, dict(self._headers), self.timeout
            )
        except urllib.error.HTTPError as error:
            if error.code == 401:
                challenge = header_value(error.headers, "WWW-Authenticate")
                raise AuthError(
                    "digest authentication failed (401); challenge: {}".format(
                        redact_text(challenge)
                    )
                )
            body = error.read().decode("utf-8", "replace")
            raise CameraError(
                "HTTP {} for {}: {}".format(
                    error.code, redact_text(url), redact_text(body)[:300]
                )
            )
        except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
            raise self._reach_error(error)

    def get(self, path: str, params: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        self._throttle()
        try:
            return self._get(url)
        finally:
            self._last_request = time.monotonic()

    def _get(self, url: str) -> Tuple[int, Dict[str, str], bytes]:
        if self._auth_scheme == "basic":
            return self._basic_get(url)
        if self._auth_scheme == "digest":
            return self._digest_get(url)

        status, headers, body = self._basic_get(url, allow_401=True)
        if status != 401:
            self._auth_scheme = "basic"
            return status, headers, body
        challenge = header_value(headers, "WWW-Authenticate")
        scheme = challenge.split(None, 1)[0].lower() if challenge else ""
        if scheme == "digest":
            self._auth_scheme = "digest"
            return self._digest_get(url)
        if scheme == "basic":
            raise AuthError(
                "basic authentication failed (401) for {}".format(
                    redact_text(url)
                )
            )
        raise AuthError(
            "unsupported or missing auth challenge from {}: {}".format(
                redact_text(url), redact_text(challenge)
            )
        )

    def cgi_text(self, path: str, params: Optional[Dict[str, str]] = None) -> str:
        _status, _headers, body = self.get(path, params)
        return body.decode("utf-8", "replace")

    def magic(self, action: str) -> Dict[str, str]:
        values, _duplicates = parse_kv(
            self.cgi_text("/cgi-bin/magicBox.cgi", {"action": action})
        )
        return values

    def get_config(self, name: str) -> Tuple[Dict[str, str], List[str], str]:
        text = self.cgi_text(
            "/cgi-bin/configManager.cgi",
            {"action": "getConfig", "name": name},
        )
        values, duplicates = parse_kv(text)
        return values, duplicates, text

    def get_motion(self, channel: int = 0) -> Dict[str, Any]:
        values, _duplicates, _text = self.get_config("MotionDetect")
        return parse_mask(values, channel)

    def snapshot(self, channel: int = 0) -> Tuple[Dict[str, str], bytes]:
        _status, headers, body = self.get(
            "/cgi-bin/snapshot.cgi", {"channel": str(channel)}
        )
        return headers, body

    def set_legacy_regions(self, regions: List[int], channel: int = 0) -> str:
        """Write all 18 legacy rows together.

        This camera resets omitted rows when a partial Region array is written,
        so callers must always send the complete mask.
        """
        if len(regions) != ROWS:
            raise ValueError("expected {} regions".format(ROWS))
        params = {"action": "setConfig"}
        for row, value in enumerate(regions):
            params[
                "MotionDetect[{}].Region[{}]".format(channel, row)
            ] = str(value)
        return self.cgi_text("/cgi-bin/configManager.cgi", params).strip()


def load_pano_camera(path: Path, camera_ip: str, name: Optional[str]) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    candidates: List[Dict[str, Any]] = []
    for key, value in config.items():
        if key.startswith("@"):
            continue
        if key.endswith("camera_list") and isinstance(value, list):
            for camera in value:
                if isinstance(camera, dict):
                    candidates.append(camera)
    for camera in candidates:
        if name and camera.get("name") != name:
            continue
        for key in ("admin_url", "live_url"):
            url = camera.get(key) or ""
            try:
                host = urllib.parse.urlsplit(url).hostname
            except ValueError:
                host = None
            if host == camera_ip:
                parsed = urllib.parse.urlsplit(url)
                if parsed.username and parsed.password:
                    return {
                        "name": str(camera.get("name") or name or camera_ip),
                        "user": urllib.parse.unquote(parsed.username),
                        "password": urllib.parse.unquote(parsed.password),
                        "model": str(camera.get("model") or ""),
                    }
    raise CameraError(
        "no camera with credentials found for ip {} in {}".format(camera_ip, path)
    )


def resolve_credentials(args: argparse.Namespace) -> Tuple[str, str, str, str]:
    name = args.name or args.camera_ip
    model = getattr(args, "model", None) or ""
    if args.pano_config:
        camera = load_pano_camera(Path(args.pano_config), args.camera_ip, args.name)
        return (
            camera["name"],
            args.user or camera["user"],
            camera["password"],
            model or camera.get("model", ""),
        )
    password = os.environ.get(args.password_env)
    if password:
        return name, args.user, password, model
    if sys.stdin.isatty():
        password = getpass.getpass(
            "Password for {}@{}: ".format(args.user, args.camera_ip)
        )
        return name, args.user, password, model
    raise CameraError(
        "no password: set ${} or pass --pano-config".format(args.password_env)
    )


def jpeg_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in (0xD8, 0xD9):
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index:index + 2], "big")
        if segment_length < 2:
            return None
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if index + 7 > len(data):
                return None
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            return width, height
        index += segment_length
    return None


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
    parser.add_argument("--camera-ip", required=True, help="camera IPv4/IPv6 address")
    parser.add_argument("--name", help="camera label for output and pano lookup")
    parser.add_argument("--camera-port", type=int, default=80)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password-env", default="AMCREST_PASSWORD")
    parser.add_argument(
        "--pano-config",
        help="read credentials for --camera-ip from a pano JSON config",
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
        camera_ip = str(ipaddress.ip_address(args.camera_ip))
    except ValueError as error:
        parser.error("invalid --camera-ip: {}".format(error))

    try:
        name, user, password, model = resolve_credentials(args)
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
