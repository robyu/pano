#!/usr/bin/env python3
"""Shared Amcrest/Dahua CGI client and config helpers.

This module is used by both the phase 0 discovery tool (``discover.py``) and the
phase 1 console server (``server.py``). It is stdlib only so it runs on the
installed Python 3.7 and on pano's Python 3.14.

Auth is explicit: Basic via a preemptive ``Authorization`` header, Digest via a
separate opener. The two are never combined in one opener. The IP2M-842 counts
an unauthenticated ``/cgi-bin`` request as a failed login and can lock the
client out for ~300s, so Basic is sent on the first request for that model.

The IP2M-842 web server is slow and single-connection. ``CameraClient``
serializes all requests with a lock, throttles them, and backs off after a
reset/refusal. Its ``getSoftwareVersion`` action crashes/restarts the web
server, so ``identity()`` skips it for IP2M-842.
"""

from __future__ import annotations

import base64
import http.client
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
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
        backoff_base: float = 2.0,
        backoff_max: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout
        self.base = "http://{}:{}".format(host, port)
        self.model = model
        self.request_delay = max(0.0, request_delay)
        self.backoff_base = max(0.0, backoff_base)
        self.backoff_max = max(0.0, backoff_max)
        self._last_request: Optional[float] = None
        self._backoff = 0.0
        self._auth_scheme: Optional[str] = None
        self._lock = threading.Lock()
        self._identity: Optional[Dict[str, Any]] = None
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
        delay = max(self.request_delay, self._backoff)
        if self._last_request is not None and delay > 0:
            remaining = delay - (time.monotonic() - self._last_request)
            if remaining > 0:
                time.sleep(remaining)

    def _note_success(self) -> None:
        self._backoff = 0.0

    def _note_failure(self) -> None:
        if self.backoff_base <= 0:
            return
        if self._backoff <= 0:
            self._backoff = self.backoff_base
        else:
            self._backoff = min(self.backoff_max, self._backoff * 2)

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
        with self._lock:
            self._throttle()
            try:
                result = self._get(url)
            except CameraError:
                self._note_failure()
                raise
            else:
                self._note_success()
                return result
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

    def verify_credentials(self) -> Dict[str, str]:
        """Prove the credentials work with a harmless identity request.

        Never calls getSoftwareVersion: it crashes/restarts the IP2M-842 web
        server.
        """
        return self.magic("getMachineName")

    def identity(self) -> Dict[str, Any]:
        """Return cached device identity (model/device type/firmware)."""
        if self._identity is not None:
            return self._identity
        identity: Dict[str, Any] = {"magic": {}, "errors": []}
        for action in ("getMachineName", "getDeviceType"):
            try:
                identity["magic"][action] = self.magic(action)
            except CameraError as error:
                identity["errors"].append({"magicBox": action, "error": str(error)})
        device_type = identity["magic"].get("getDeviceType", {})
        if skip_software_version(self.model, device_type.get("type")):
            identity["magic_skipped"] = ["getSoftwareVersion"]
        else:
            try:
                identity["magic"]["getSoftwareVersion"] = self.magic(
                    "getSoftwareVersion"
                )
            except CameraError as error:
                identity["errors"].append(
                    {"magicBox": "getSoftwareVersion", "error": str(error)}
                )
        self._identity = identity
        return identity


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
