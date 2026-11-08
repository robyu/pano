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
import hashlib
import http.client
import http.cookiejar
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import cgi_config

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
    r"(password|passwd|pwd|secret|token|credential|private|session|cookie)",
    re.IGNORECASE,
)
SENSITIVE_LINE_RE = re.compile(
    r"(?im)^([^=\r\n]*(?:password|passwd|pwd|secret|token|credential|private"
    r"|session|cookie)[^=\r\n]*)=.*$"
)
SENSITIVE_PARAM_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|credential|private|session"
    r"|cookie)(=)[^&\s]+"
)
USERINFO_RE = re.compile(r"://[^/@\s]+@")

_PACKAGE_LOG = logging.getLogger("amcrest")
if not _PACKAGE_LOG.handlers:
    _PACKAGE_LOG.addHandler(logging.NullHandler())

LOG = logging.getLogger("amcrest.camera")


class CameraError(RuntimeError):
    pass


class AuthError(CameraError):
    pass


def cgi_response_is_error(text: str) -> bool:
    return "error" in text.lower()


def mirror_region_values(values: List[int]) -> List[int]:
    """Horizontally mirror legacy 22-bit Region rows.

    On the IP2M-842, ``MotionDetectWindow[0].Region`` is the exact horizontal
    mirror of the legacy ``Region`` model. When both models are present, keep
    them consistent so whichever one the firmware uses gets the edited mask.
    """
    mirrored: List[int] = []
    for value in values:
        value = int(value)
        result = 0
        for col in range(COLS):
            if (value >> col) & 1:
                result |= 1 << (COLS - 1 - col)
        mirrored.append(result)
    return mirrored


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


def loggable(value: Any, limit: int = 1200) -> str:
    """Return a redacted, truncated string safe for protocol logs."""
    try:
        safe = sanitize(value)
        text = json.dumps(safe, sort_keys=True, default=str)
    except (TypeError, ValueError):
        text = repr(value)
    text = redact_text(text)
    if len(text) > limit:
        text = text[:limit] + "... ({} chars)".format(len(text))
    return text


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


def rpc_default_password(
    user: str, realm: str, random_value: str, password: str
) -> str:
    """Return the Dahua ``Default`` RPC2 password hash.

    The camera's ``jsCore/md5.js`` returns uppercase hex, and the firmware
    compares the string exactly, so both hashes must be uppercase.
    """
    digest = hashlib.md5(
        "{}:{}:{}".format(user, realm, password).encode("utf-8")
    ).hexdigest().upper()
    return hashlib.md5(
        "{}:{}:{}".format(user, random_value, digest).encode("utf-8")
    ).hexdigest().upper()


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
        logger: Optional[logging.Logger] = None,
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
        self.log = logger or LOG
        self._last_request: Optional[float] = None
        self._backoff = 0.0
        self._auth_scheme: Optional[str] = None
        self._lock = threading.RLock()
        self._identity: Optional[Dict[str, Any]] = None
        self._rpc_session: Optional[Any] = None
        self._rpc_id = 100
        self._rpc_lock = threading.Lock()
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
        # RPC2 sessions are bound to the DhWebClientSessionID cookie. This
        # firmware never sends Set-Cookie; its web UI sets the cookie in JS
        # from the login session, so the client must send it explicitly.
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookie_jar)
        )
        self._digest_opener: Optional[urllib.request.OpenerDirector] = None
        self.log.info(
            "camera client ready host=%s port=%s auth=%s model=%s timeout=%.1fs delay=%.2fs",
            host,
            port,
            self.auth_scheme,
            self.model or "unknown",
            self.timeout,
            self.request_delay,
        )

    @property
    def auth_scheme(self) -> str:
        return self._auth_scheme or "auto"

    def _throttle(self) -> None:
        delay = max(self.request_delay, self._backoff)
        if self._last_request is not None and delay > 0:
            remaining = delay - (time.monotonic() - self._last_request)
            if remaining > 0:
                self.log.debug(
                    "camera throttle waiting %.2fs (delay=%.2fs backoff=%.2fs)",
                    remaining,
                    delay,
                    self._backoff,
                )
                time.sleep(remaining)

    def _note_success(self) -> None:
        if self._backoff:
            self.log.info("camera backoff reset after success")
        self._backoff = 0.0

    def _note_failure(self) -> None:
        if self.backoff_base <= 0:
            return
        if self._backoff <= 0:
            self._backoff = self.backoff_base
        else:
            self._backoff = min(self.backoff_max, self._backoff * 2)
        self.log.warning("camera backoff now %.2fs after failure", self._backoff)

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
        data: Optional[bytes] = None,
    ) -> Tuple[int, Dict[str, str], bytes]:
        request = urllib.request.Request(url, data=data, headers=headers or {})
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
        safe_url = redact_text(url)
        with self._lock:
            self._throttle()
            started = time.monotonic()
            self.log.info(
                "CGI request GET %s params=%s", safe_url, loggable(params or {})
            )
            try:
                result = self._get(url)
            except CameraError as error:
                self.log.warning(
                    "CGI request failed %s after %.3fs: %s",
                    safe_url,
                    time.monotonic() - started,
                    redact_text(str(error)),
                )
                self._note_failure()
                raise
            else:
                status, _headers, body = result
                elapsed = time.monotonic() - started
                preview = redact_text(body.decode("utf-8", "replace"))[:300]
                self.log.info(
                    "CGI response %s -> %s %dB in %.3fs body=%r",
                    safe_url,
                    status,
                    len(body),
                    elapsed,
                    preview,
                )
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
            if self._auth_scheme != "basic":
                self.log.info("camera auth scheme selected: basic")
            self._auth_scheme = "basic"
            return status, headers, body
        challenge = header_value(headers, "WWW-Authenticate")
        scheme = challenge.split(None, 1)[0].lower() if challenge else ""
        self.log.info(
            "camera auth challenge scheme=%s for %s", scheme or "none", redact_text(url)
        )
        if scheme == "digest":
            if self._auth_scheme != "digest":
                self.log.info("camera auth scheme selected: digest")
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
        self.log.info("CGI config request name=%s", name)
        text = self.cgi_text(
            "/cgi-bin/configManager.cgi",
            {"action": "getConfig", "name": name},
        )
        values, duplicates = parse_kv(text)
        self.log.info(
            "CGI config %s keys=%d duplicates=%d bytes=%d",
            name,
            len(values),
            len(duplicates),
            len(text),
        )
        if duplicates:
            self.log.warning(
                "CGI config %s has duplicate keys=%s", name, duplicates[:10]
            )
        return values, duplicates, text

    def get_section(self, name: str) -> Dict[str, Any]:
        values, duplicates, text = self.get_config(name)
        return {
            "name": name,
            "values": values,
            "duplicates": duplicates,
            "raw": text,
            "revision": cgi_config.revision(values),
        }

    def set_section_changes(self, name: str, changes: Dict[str, str]) -> str:
        if not changes:
            return "OK (no changes)"
        params = cgi_config.params_for_cgi(changes)
        self.log.info(
            "CGI section write name=%s keys=%d changed=%s",
            name,
            len(changes),
            sorted(changes),
        )
        response = self.cgi_text("/cgi-bin/configManager.cgi", params).strip()
        self.log.info(
            "CGI section write response name=%s response=%r",
            name,
            redact_text(response)[:300],
        )
        if not cgi_response_is_error(response):
            return response
        self.log.warning(
            "CGI section write rejected name=%s; falling back to RPC2", name
        )
        return self.set_section_via_rpc(name, changes)

    def set_section_via_rpc(self, name: str, changes: Dict[str, str]) -> str:
        table = self.rpc_get_config(name)
        if not isinstance(table, (dict, list)):
            raise CameraError(
                "camera returned no {} table for RPC2 write".format(name)
            )
        for key, value in changes.items():
            try:
                cgi_config.set_table_value(table, name, key, value)
            except cgi_config.ConfigError as error:
                raise CameraError(str(error))
        self.rpc_set_config(name, table)
        self.log.info(
            "RPC2 section write completed name=%s keys=%d",
            name,
            len(changes),
        )
        return "OK (RPC2)"

    def write_motion_settings(self, changes: Dict[str, str]) -> str:
        values, _duplicates, _text = self.get_config("MotionDetect")
        regions: List[str] = []
        for row in range(ROWS):
            key = "MotionDetect[0].Region[{}]".format(row)
            if key not in values:
                raise CameraError(
                    "camera did not return all 18 legacy motion rows; "
                    "refusing to change motion settings"
                )
            regions.append(values[key])
        params: Dict[str, str] = {"action": "setConfig"}
        for row, value in enumerate(regions):
            params["MotionDetect[0].Region[{}]".format(row)] = value
        params.update(changes)
        self.log.info(
            "CGI motion settings write keys=%d changed=%s",
            len(changes),
            sorted(changes),
        )
        response = self.cgi_text("/cgi-bin/configManager.cgi", params).strip()
        self.log.info(
            "CGI motion settings response=%r", redact_text(response)[:300]
        )
        if not cgi_response_is_error(response):
            return response
        self.log.warning(
            "CGI motion settings rejected; falling back to RPC2"
        )
        return self.set_section_via_rpc("MotionDetect", changes)

    def get_motion(self, channel: int = 0) -> Dict[str, Any]:
        values, _duplicates, _text = self.get_config("MotionDetect")
        motion = parse_mask(values, channel)
        legacy = motion.get("legacy")
        self.log.info(
            "CGI motion channel=%d enable=%s level=%s legacy_rows=%s windows=%d",
            channel,
            motion.get("enable"),
            motion.get("level"),
            len(legacy) if isinstance(legacy, list) else "none",
            len(motion.get("windows") or []),
        )
        if not legacy:
            self.log.warning(
                "CGI motion channel=%d returned no complete legacy Region rows",
                channel,
            )
        return motion

    def snapshot(self, channel: int = 0) -> Tuple[Dict[str, str], bytes]:
        self.log.info("CGI snapshot request channel=%d", channel)
        _status, headers, body = self.get(
            "/cgi-bin/snapshot.cgi", {"channel": str(channel)}
        )
        self.log.info(
            "CGI snapshot channel=%d bytes=%d content_type=%s",
            channel,
            len(body),
            headers.get("Content-Type"),
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
        self.log.info(
            "CGI motion write channel=%d rows=%d keys=%d",
            channel,
            len(regions),
            len(params),
        )
        response = self.cgi_text("/cgi-bin/configManager.cgi", params).strip()
        self.log.info(
            "CGI motion write response channel=%d response=%r",
            channel,
            redact_text(response)[:300],
        )
        return response

    def _rpc_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Request": "JSON",
        }
        headers.update(self._headers)
        session = payload.get("session")
        if session is not None and not path.startswith("/RPC2_Login"):
            headers["Cookie"] = "DhWebClientSessionID={}".format(session)
        url = self.base + path
        try:
            _status, _headers, body = self._open(
                self._opener, url, headers, self.timeout, data=data
            )
        except urllib.error.HTTPError as error:
            body = error.read()
            if not body:
                raise CameraError(
                    "HTTP {} for {}".format(error.code, redact_text(url))
                )
        except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
            raise self._reach_error(error)
        text = body.decode("utf-8-sig", "replace")
        try:
            value = json.loads(text)
        except ValueError:
            raise CameraError(
                "invalid RPC2 JSON from {}: {}".format(
                    redact_text(url), redact_text(text)[:200]
                )
            )
        if not isinstance(value, dict):
            raise CameraError(
                "invalid RPC2 response from {}".format(redact_text(url))
            )
        return value

    def _rpc_request(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        method = payload.get("method")
        with self._lock:
            self._throttle()
            started = time.monotonic()
            self.log.info(
                "RPC2 request %s method=%s payload=%s",
                path,
                method,
                loggable(payload),
            )
            try:
                result = self._rpc_post(path, payload)
            except CameraError as error:
                self.log.warning(
                    "RPC2 request failed %s method=%s after %.3fs: %s",
                    path,
                    method,
                    time.monotonic() - started,
                    redact_text(str(error)),
                )
                self._note_failure()
                raise
            else:
                error = result.get("error") or {}
                params = result.get("params") or {}
                self.log.info(
                    "RPC2 response %s method=%s result=%s error_code=%s "
                    "error=%s params_error=%s in %.3fs",
                    path,
                    method,
                    result.get("result"),
                    error.get("code"),
                    error.get("message"),
                    params.get("error"),
                    time.monotonic() - started,
                )
                self._note_success()
                return result
            finally:
                self._last_request = time.monotonic()

    def rpc_login(self, force: bool = False) -> Any:
        """Log in to the camera's RPC2 API and cache the session.

        RPC2 is needed for models (IP2M-842) whose CGI ``setConfig`` rejects
        MotionDetect writes. The camera requests a realm/random challenge and
        uses the standard Dahua doubled-MD5 digest.
        """
        with self._rpc_lock:
            if self._rpc_session is not None and not force:
                return self._rpc_session
            first = self._rpc_request(
                "/RPC2_Login",
                {
                    "method": "global.login",
                    "params": {
                        "userName": self.user,
                        "password": "",
                        "clientType": "Web3.0",
                    },
                    "id": 10000,
                },
            )
            session = first.get("session")
            params = first.get("params") or {}
            error = first.get("error") or {}
            self.log.info(
                "RPC2 login challenge result=%s error_code=%s error=%s "
                "session_present=%s encryption=%s realm_present=%s random_present=%s",
                first.get("result"),
                error.get("code"),
                error.get("message"),
                session is not None,
                params.get("encryption"),
                bool(params.get("realm")),
                bool(params.get("random")),
            )
            if first.get("result") and session is not None:
                self._rpc_session = session
                return session
            if session is None:
                raise CameraError("RPC2 login challenge did not return a session")
            encryption = params.get("encryption")
            if encryption == "Default":
                realm = str(params.get("realm") or "")
                random_value = str(params.get("random") or "")
                password = rpc_default_password(
                    self.user, realm, random_value, self.password
                )
            elif encryption == "Basic":
                password = base64.b64encode(
                    "{}:{}".format(self.user, self.password).encode("utf-8")
                ).decode("ascii")
            elif encryption:
                password = self.password
            else:
                raise CameraError(
                    "RPC2 login returned no encryption method"
                )
            self.log.info(
                "RPC2 login using encryption=%s (password not logged)",
                encryption,
            )
            second = self._rpc_request(
                "/RPC2_Login",
                {
                    "method": "global.login",
                    "session": session,
                    "params": {
                        "userName": self.user,
                        "password": password,
                        "clientType": "Web3.0",
                    },
                    "id": 10000,
                },
            )
            if not second.get("result"):
                error = (
                    (second.get("params") or {}).get("error")
                    or (second.get("error") or {}).get("message")
                    or "unknown error"
                )
                self.log.warning("RPC2 login failed: %s", error)
                hint = ""
                if str(error) in ("HasBeenLocked", "InBlackList"):
                    hint = " (camera login lockout; wait several minutes)"
                elif str(error) == "PasswordNotValid":
                    hint = (
                        " (wrong web/RPC2 password, or an active login lockout;"
                        " wait for LockFailLockTime to expire before retrying)"
                    )
                raise CameraError(
                    "RPC2 login failed: {}{}".format(error, hint)
                )
            self._rpc_session = second.get("session") or session
            self.log.info("RPC2 login succeeded; session cached")
            return self._rpc_session

    def rpc_call(
        self, method: str, params: Optional[Any] = None
    ) -> Dict[str, Any]:
        session = self.rpc_login()
        with self._rpc_lock:
            request_id = self._rpc_id
            self._rpc_id += 1
        result = self._rpc_request(
            "/RPC2",
            {
                "method": method,
                "params": params,
                "session": session,
                "id": request_id,
            },
        )
        if not result.get("result"):
            error = (
                (result.get("params") or {}).get("error")
                or (result.get("error") or {}).get("message")
                or "unknown error"
            )
            if (result.get("error") or {}).get("code") == 401:
                self.log.warning(
                    "RPC2 %s returned 401; clearing cached session", method
                )
                self._rpc_session = None
            self.log.warning("RPC2 %s failed: %s", method, error)
            raise CameraError(
                "RPC2 {} failed: {}".format(method, error)
            )
        return result

    def rpc_get_config(self, name: str) -> Any:
        self.log.info("RPC2 getConfig name=%s", name)
        result = self.rpc_call(
            "configManager.getConfig", {"name": name}
        )
        table = (result.get("params") or {}).get("table")
        self.log.info(
            "RPC2 getConfig %s table_type=%s", name, type(table).__name__
        )
        return table

    def rpc_set_config(self, name: str, table: Any) -> None:
        self.log.info(
            "RPC2 setConfig name=%s table_type=%s",
            name,
            type(table).__name__,
        )
        self.rpc_call(
            "configManager.setConfig",
            {"name": name, "table": table, "options": ""},
        )
        self.log.info("RPC2 setConfig %s accepted", name)

    def set_motion_via_rpc(self, regions: List[int], channel: int = 0) -> str:
        """Write the legacy Region rows through the RPC2 config API."""
        values = [int(value) for value in regions]
        if len(values) != ROWS:
            raise ValueError("expected {} regions".format(ROWS))
        self.log.info(
            "RPC2 motion write channel=%d rows=%d", channel, len(values)
        )
        table = self.rpc_get_config("MotionDetect")
        if (
            not isinstance(table, list)
            or channel >= len(table)
            or not isinstance(table[channel], dict)
        ):
            raise CameraError("camera returned no MotionDetect channel")
        current = table[channel].get("Region")
        if not isinstance(current, list) or len(current) != ROWS:
            raise CameraError("camera returned no legacy MotionDetect Region")
        table[channel]["Region"] = values
        self.rpc_set_config("MotionDetect", table)
        self.log.info("RPC2 motion write completed channel=%d", channel)
        return "OK (RPC2)"

    def write_motion_mask(self, regions: List[int], channel: int = 0) -> str:
        """Write all 18 rows via CGI, falling back to RPC2 if rejected.

        The IP2M-842 accepts the CGI read but returns ``Error`` for every
        MotionDetect ``setConfig``; its web API (RPC2) is the writable path.
        """
        self.log.info(
            "motion write attempt via CGI channel=%d rows=%d",
            channel,
            len(regions),
        )
        response = self.set_legacy_regions(regions, channel)
        if not cgi_response_is_error(response):
            self.log.info("CGI motion write accepted channel=%d", channel)
            return response
        self.log.warning(
            "CGI motion write rejected; falling back to RPC2 response=%r",
            redact_text(response)[:200],
        )
        try:
            result = self.set_motion_via_rpc(regions, channel)
        except CameraError as error:
            self.log.error(
                "RPC2 motion fallback failed channel=%d: %s", channel, error
            )
            raise CameraError(
                "CGI motion write rejected ({}); RPC2 fallback failed: {}".format(
                    redact_text(response)[:80], error
                )
            )
        self.log.info("RPC2 motion fallback succeeded channel=%d", channel)
        return result

    def verify_credentials(self) -> Dict[str, str]:
        """Prove the credentials work with a harmless identity request.

        Never calls getSoftwareVersion: it crashes/restarts the IP2M-842 web
        server.
        """
        self.log.info("verifying camera credentials via magicBox getMachineName")
        values = self.magic("getMachineName")
        self.log.info(
            "camera credentials verified; machine_name_present=%s",
            bool(values.get("MachineName")),
        )
        return values

    def identity(self) -> Dict[str, Any]:
        """Return cached device identity (model/device type/firmware)."""
        if self._identity is not None:
            self.log.debug("camera identity served from cache")
            return self._identity
        identity: Dict[str, Any] = {"magic": {}, "errors": []}
        for action in ("getMachineName", "getDeviceType"):
            try:
                self.log.debug("camera identity request action=%s", action)
                identity["magic"][action] = self.magic(action)
            except CameraError as error:
                self.log.warning(
                    "camera identity action=%s failed: %s", action, error
                )
                identity["errors"].append({"magicBox": action, "error": str(error)})
        device_type = identity["magic"].get("getDeviceType", {})
        if skip_software_version(self.model, device_type.get("type")):
            self.log.info("camera identity skipping getSoftwareVersion for model")
            identity["magic_skipped"] = ["getSoftwareVersion"]
        else:
            try:
                self.log.debug("camera identity request action=getSoftwareVersion")
                identity["magic"]["getSoftwareVersion"] = self.magic(
                    "getSoftwareVersion"
                )
            except CameraError as error:
                self.log.warning(
                    "camera identity action=getSoftwareVersion failed: %s", error
                )
                identity["errors"].append(
                    {"magicBox": "getSoftwareVersion", "error": str(error)}
                )
        self.log.info(
            "camera identity done actions=%s errors=%d",
            ",".join(sorted(identity["magic"].keys())) or "none",
            len(identity["errors"]),
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
