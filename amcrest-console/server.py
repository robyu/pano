#!/usr/bin/env python3
"""LAN-accessible console server for a single Amcrest/Dahua camera.

Phase 1: browser login, in-memory session, and snapshot proxying. Phase 2 adds
the legacy motion-mask editor and a per-camera JSON configuration mirror. The
camera remains the source of truth; the mirror is updated after every successful
read and every verified write.

Routes are served from ``/`` (no URL token). Camera APIs require the browser
session; only one browser may be signed in at a time. Host is checked against
local/allowlisted names to block DNS rebinding, and Origin must match Host to
block cross-origin writes. Camera credentials are kept in memory only.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import secrets
import socket
import sys
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

import mask
import state
from camera import AuthError, CameraClient, CameraError, redact_text

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
}
COOKIE_NAME = "amcrest_session"
MAX_BODY = 4096

LOG = logging.getLogger("amcrest.server")


def _clean_address(value: str) -> str:
    return str(value).split("%", 1)[0]


def local_ip_addresses() -> list:
    """Best-effort list of this host's addresses (loopback included)."""
    addresses = set()
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None)
    except OSError:
        infos = []
    for info in infos:
        addresses.add(_clean_address(info[4][0]))
    for family, target in (
        (socket.AF_INET, ("8.8.8.8", 80)),
        (socket.AF_INET6, ("2001:4860:4860::8888", 80)),
    ):
        try:
            probe = socket.socket(family, socket.SOCK_DGRAM)
            try:
                probe.connect(target)
                addresses.add(_clean_address(probe.getsockname()[0]))
            finally:
                probe.close()
        except OSError:
            pass
    addresses.discard("0.0.0.0")
    addresses.discard("::")
    return sorted(addresses)


def split_host(value: str) -> Tuple[str, str]:
    """Split ``host[:port]`` or ``[ipv6][:port]`` into (host, port)."""
    value = str(value or "").strip().lower()
    if not value:
        return "", ""
    if value.startswith("["):
        closing = value.find("]")
        if closing == -1:
            return "", ""
        host = value[1:closing]
        rest = value[closing + 1:]
        return host, rest[1:] if rest.startswith(":") else ""
    if value.count(":") == 1:
        host, port = value.rsplit(":", 1)
        return host, port
    return value, ""


def normalize_host(value: str, port: int) -> str:
    host, explicit_port = split_host(value)
    if not host:
        return ""
    if ":" in host:
        host = "[{}]".format(host)
    return "{}:{}".format(host, explicit_port or port)


def build_allowed_hosts(
    bind_host: str, port: int, extra: Optional[list] = None
) -> set:
    hosts = set()
    for value in ("localhost", "127.0.0.1", "::1"):
        hosts.add(normalize_host(value, port))
    if bind_host not in ("", "0.0.0.0", "::"):
        hosts.add(normalize_host(bind_host, port))
    for address in local_ip_addresses():
        hosts.add(normalize_host(address, port))
    for value in extra or ():
        normalized = normalize_host(value, port)
        if normalized:
            hosts.add(normalized)
    return hosts


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: Tuple[str, int],
        camera_config: Dict[str, Any],
        name: Optional[str] = None,
        state_path: Optional[Path] = None,
        allow_hosts: Optional[list] = None,
    ) -> None:
        super().__init__(address, ConsoleHandler)
        self.camera_config = camera_config
        self.name = name or str(camera_config.get("host") or "camera")
        self.state_path = Path(state_path) if state_path else None
        self.session: Optional[Dict[str, Any]] = None
        self.session_lock = threading.Lock()
        self.login_failures: Dict[str, int] = {}
        self.login_lock = threading.Lock()
        host, port = self.server_address[0], self.server_address[1]
        self.allowed_hosts = build_allowed_hosts(host, port, allow_hosts)
        LOG.info(
            "console server ready name=%s camera=%s:%s model=%s auth=%s "
            "mirror=%s listen=%s:%s allowed_hosts=%s",
            self.name,
            self.camera_config.get("host"),
            self.camera_config.get("port", 80),
            self.camera_config.get("model") or "unknown",
            self.camera_config.get("auth", "auto"),
            self.state_path,
            host,
            port,
            ",".join(sorted(self.allowed_hosts)),
        )

    def note_login_failure(self, address: str) -> float:
        with self.login_lock:
            count = self.login_failures.get(address, 0) + 1
            self.login_failures[address] = count
        return min(5.0, float(count))

    def clear_login_failures(self, address: str) -> None:
        with self.login_lock:
            self.login_failures.pop(address, None)

    def make_client(self, user: str, password: str) -> CameraClient:
        config = self.camera_config
        LOG.info(
            "creating camera client host=%s port=%s model=%s auth=%s "
            "timeout=%s delay=%s",
            config.get("host"),
            config.get("port", 80),
            config.get("model") or "unknown",
            config.get("auth", "auto"),
            config.get("timeout", 20.0),
            config.get("request_delay", 0.0),
        )
        return CameraClient(
            config["host"],
            int(config.get("port", 80)),
            user,
            password,
            timeout=float(config.get("timeout", 20.0)),
            auth=str(config.get("auth", "auto")),
            model=config.get("model") or None,
            request_delay=float(config.get("request_delay", 0.0)),
            logger=logging.getLogger("amcrest.camera"),
        )

    def get_session(self) -> Optional[Dict[str, Any]]:
        with self.session_lock:
            return self.session

    def set_session(self, session: Optional[Dict[str, Any]]) -> None:
        with self.session_lock:
            self.session = session
            if session:
                LOG.info(
                    "console session established user=%s", session.get("user")
                )
            else:
                LOG.info("console session cleared")

    def load_mirror(self) -> Optional[Dict[str, Any]]:
        if self.state_path is None:
            return None
        return state.load(self.state_path)

    def camera_meta(self) -> Dict[str, Any]:
        config = self.camera_config
        existing = self.load_mirror() or {}
        previous = existing.get("camera") or {}
        return {
            "name": self.name,
            "host": config.get("host"),
            "port": int(config.get("port", 80)),
            "model": config.get("model") or previous.get("model"),
            "firmware": previous.get("firmware"),
        }

    def build_motion(self, motion: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "enable": motion.get("enable"),
            "level": motion.get("level"),
            "legacy": None,
            "windows": [],
        }
        legacy = motion.get("legacy")
        if legacy and len(legacy) == mask.ROWS:
            try:
                values = [int(value) for value in legacy]
                rows = mask.decode(values)
            except (TypeError, ValueError) as error:
                raise CameraError(
                    "camera returned a malformed legacy motion mask: {}".format(
                        error
                    )
                )
            result["legacy"] = {
                "region_values": values,
                "rows": rows,
                "revision": mask.revision_from_regions(values),
                "ascii": mask.ascii(rows),
            }
        for window in motion.get("windows") or []:
            item = {
                "id": window.get("id"),
                "name": window.get("name"),
                "sensitive": window.get("sensitive"),
                "threshold": window.get("threshold"),
                "readonly": True,
            }
            regions = window.get("regions")
            if regions:
                try:
                    item["rows"] = mask.decode([int(value) for value in regions])
                except (mask.MaskError, TypeError, ValueError):
                    item["rows"] = None
            result["windows"].append(item)
        return result

    def save_motion(
        self,
        motion: Dict[str, Any],
        verified: bool = True,
        last_apply: Optional[str] = None,
        stale: bool = False,
    ) -> Dict[str, Any]:
        existing = self.load_mirror() or {}
        configuration = dict(existing.get("configuration") or {})
        configuration["MotionDetect"] = self.build_motion(motion)
        doc = state.new_mirror(
            self.camera_meta(),
            configuration,
            stale=stale,
            verified=verified,
            last_apply=last_apply,
        )
        if self.state_path is not None:
            state.save(self.state_path, doc)
        return doc

    def mirror_meta(
        self, doc: Optional[Dict[str, Any]] = None, stale: bool = False
    ) -> Dict[str, Any]:
        mirror = (doc or {}).get("mirror") or {}
        return {
            "path": str(self.state_path) if self.state_path else None,
            "updated": mirror.get("updated"),
            "last_apply": mirror.get("last_apply"),
            "stale": bool(stale or mirror.get("stale")),
        }


class ConsoleHandler(BaseHTTPRequestHandler):
    server: ConsoleServer
    server_version = "AmcrestConsole/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        LOG.info("http %s", redact_text(fmt % args))

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def _dispatch(self, method: str) -> None:
        if not self._check_host():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad host"})
            return
        route = urlsplit(self.path).path or "/"
        if method != "GET" and not self._check_origin():
            LOG.warning(
                "request rejected: bad origin method=%s route=%s",
                method,
                route,
            )
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "bad origin"})
            return
        LOG.debug("dispatch method=%s route=%s", method, route)
        try:
            if method == "GET":
                self._route_get(route)
            elif method == "PUT":
                self._route_put(route)
            else:
                self._route_post(route)
        except AuthError as error:
            LOG.warning("authentication error route=%s: %s", route, error)
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)})
        except CameraError as error:
            LOG.warning("camera error route=%s: %s", route, error)
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
        except Exception as error:  # pragma: no cover - defensive
            LOG.exception("unexpected error route=%s", route)
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal error: {}".format(type(error).__name__)},
            )

    def _check_host(self) -> bool:
        host = self.headers.get("Host", "").lower()
        if host in self.server.allowed_hosts:
            return True
        name, port = split_host(host)
        if not name:
            return False
        if port and port != str(self.server.server_address[1]):
            return False
        try:
            address = ipaddress.ip_address(name)
        except ValueError:
            return False
        return address.is_private or address.is_loopback or address.is_link_local

    def _check_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlsplit(origin)
        if parsed.scheme != "http" or not parsed.netloc:
            return False
        return parsed.netloc.lower() == self.headers.get("Host", "").lower()

    def _route_get(self, route: str) -> None:
        if route in ("/", "/index.html"):
            self._send_static("index.html")
        elif route.startswith("/static/"):
            self._send_static(route[len("/static/"):])
        elif route == "/api/session":
            self._send_json(
                HTTPStatus.OK,
                {"authenticated": self._session_client() is not None},
            )
        elif route == "/api/camera":
            self._api_camera()
        elif route == "/api/snapshot":
            self._api_snapshot()
        elif route == "/api/motion":
            self._api_motion_get()
        elif route == "/api/state":
            self._api_state()
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _route_post(self, route: str) -> None:
        if route == "/api/login":
            self._api_login()
        elif route == "/api/logout":
            self._api_logout()
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _route_put(self, route: str) -> None:
        if route == "/api/motion":
            self._api_motion_put()
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _session_client(self) -> Optional[CameraClient]:
        session = self.server.get_session()
        if not session:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        morsel = cookie.get(COOKIE_NAME)
        if morsel is None:
            return None
        if not hmac.compare_digest(morsel.value, session.get("cookie", "")):
            return None
        return session.get("client")

    def _require_session(self) -> Optional[CameraClient]:
        client = self._session_client()
        if client is None:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "not logged in"})
        return client

    def _api_login(self) -> None:
        body = self._read_json()
        if body is None:
            return
        user = str(body.get("user") or "").strip()
        password = str(body.get("password") or "")
        if not user or not password:
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "username and password required"}
            )
            return
        LOG.info("login attempt user=%s", user)
        client = self.server.make_client(user, password)
        address = self.client_address[0]
        try:
            client.verify_credentials()
        except AuthError as error:
            delay = self.server.note_login_failure(address)
            LOG.warning(
                "login failed user=%s address=%s delay=%.1fs: %s",
                user,
                address,
                delay,
                error,
            )
            time.sleep(delay)
            self._send_json(
                HTTPStatus.UNAUTHORIZED, {"error": "invalid credentials"}
            )
            return
        except CameraError as error:
            LOG.warning("login failed user=%s: %s", user, error)
            raise
        self.server.clear_login_failures(address)
        LOG.info("login succeeded user=%s", user)
        cookie = secrets.token_hex(32)
        self.server.set_session(
            {"cookie": cookie, "user": user, "client": client}
        )
        self._send_json(
            HTTPStatus.OK,
            {"authenticated": True, "user": user},
            cookie=cookie,
        )

    def _api_logout(self) -> None:
        if (
            self.server.get_session() is not None
            and self._session_client() is None
        ):
            LOG.warning("logout rejected: no matching session cookie")
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "not logged in"})
            return
        LOG.info("logout requested")
        self.server.set_session(None)
        self._send_json(
            HTTPStatus.OK,
            {"authenticated": False},
            cookie="",
            expire_cookie=True,
        )

    def _api_camera(self) -> None:
        client = self._require_session()
        if client is None:
            return
        LOG.info("camera info requested")
        identity = client.identity()
        magic = identity.get("magic", {})
        device_type = magic.get("getDeviceType", {})
        software = magic.get("getSoftwareVersion", {})
        self._send_json(
            HTTPStatus.OK,
            {
                "name": self.server.name,
                "host": self.server.camera_config.get("host"),
                "model": self.server.camera_config.get("model")
                or device_type.get("type"),
                "device_type": device_type.get("type"),
                "firmware": software.get("version"),
                "auth": client.auth_scheme,
                "identity_errors": identity.get("errors", []),
            },
        )

    def _api_snapshot(self) -> None:
        client = self._require_session()
        if client is None:
            return
        headers, body = client.snapshot()
        LOG.debug("snapshot response bytes=%d", len(body))
        content_type = headers.get("Content-Type") or "image/jpeg"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _api_motion_get(self) -> None:
        client = self._require_session()
        if client is None:
            return
        LOG.info("motion read requested")
        try:
            motion = client.get_motion()
        except AuthError:
            raise
        except CameraError as error:
            LOG.warning(
                "motion read failed; serving stale mirror if available: %s", error
            )
            doc = self.server.load_mirror()
            stored = ((doc or {}).get("configuration") or {}).get("MotionDetect")
            if not stored:
                raise
            payload = dict(stored)
            payload["stale"] = True
            self._send_json(
                HTTPStatus.OK,
                {
                    "motion": payload,
                    "mirror": self.server.mirror_meta(doc, stale=True),
                },
            )
            return
        doc = self.server.save_motion(motion)
        LOG.info(
            "motion read ok revision=%s",
            ((doc.get("configuration") or {}).get("MotionDetect") or {})
            .get("legacy", {})
            .get("revision"),
        )
        self._send_json(
            HTTPStatus.OK,
            {
                "motion": doc["configuration"]["MotionDetect"],
                "mirror": self.server.mirror_meta(doc, stale=False),
            },
        )

    def _api_state(self) -> None:
        client = self._require_session()
        if client is None:
            return
        LOG.debug("state requested")
        doc = self.server.load_mirror()
        if doc is None:
            LOG.warning("state requested but no mirror exists")
            self._send_json(
                HTTPStatus.NOT_FOUND, {"error": "no configuration mirror"}
            )
            return
        self._send_json(
            HTTPStatus.OK,
            {
                "state": doc,
                "mirror": self.server.mirror_meta(doc, stale=bool(doc["mirror"].get("stale"))),
            },
        )

    def _api_motion_put(self) -> None:
        body = self._read_json()
        if body is None:
            return
        unknown = set(body) - {"rows", "revision", "confirm"}
        if unknown:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "unexpected fields: {}".format(", ".join(sorted(unknown)))},
            )
            return
        if body.get("confirm") is not True:
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "confirmation required"}
            )
            return
        try:
            grid = mask.validate(body.get("rows"))
        except mask.MaskError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        revision = body.get("revision")
        if not isinstance(revision, str) or not revision:
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "revision required"}
            )
            return
        client = self._require_session()
        if client is None:
            return

        current = client.get_motion()
        legacy = current.get("legacy")
        if not legacy or len(legacy) != mask.ROWS:
            raise CameraError("camera did not return a legacy motion mask")
        try:
            current_values = [int(value) for value in legacy]
        except (TypeError, ValueError):
            raise CameraError("camera returned a malformed legacy motion mask")
        current_revision = mask.revision_from_regions(current_values)

        if revision != current_revision:
            LOG.warning(
                "motion apply rejected: stale revision expected=%s current=%s",
                revision,
                current_revision,
            )
            doc = self.server.save_motion(current)
            self._send_json(
                HTTPStatus.CONFLICT,
                {
                    "error": "camera mask changed; reload before applying",
                    "motion": doc["configuration"]["MotionDetect"],
                    "mirror": self.server.mirror_meta(doc),
                },
            )
            return

        new_values = mask.encode(grid)
        LOG.info(
            "motion apply requested current_revision=%s changed=%s",
            current_revision,
            new_values != current_values,
        )
        if new_values == current_values:
            LOG.info("motion apply no-op; mask already matches")
            doc = self.server.save_motion(current)
            self._send_json(
                HTTPStatus.OK,
                {
                    "changed": False,
                    "verified": True,
                    "motion": doc["configuration"]["MotionDetect"],
                    "mirror": self.server.mirror_meta(doc),
                },
            )
            return

        response = client.write_motion_mask(new_values)
        LOG.info("motion write response=%r", redact_text(response)[:200])
        if "ErrorID" in response or "error" in response.lower():
            raise CameraError(
                "camera rejected motion write: {}".format(redact_text(response)[:300])
            )

        LOG.info("motion write sent; re-reading for verification")
        after = client.get_motion()
        after_legacy = after.get("legacy")
        try:
            after_values = (
                [int(value) for value in after_legacy]
                if after_legacy is not None
                else None
            )
        except (TypeError, ValueError):
            after_values = None
        if after_values != new_values:
            LOG.error(
                "motion write verification failed expected=%s actual=%s",
                mask.revision_from_regions(new_values),
                (
                    mask.revision_from_regions(after_values)
                    if after_values is not None
                    else None
                ),
            )
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {
                    "error": "mask write verification failed",
                    "verified": False,
                    "expected": new_values,
                    "actual": after_values,
                    "mirror": self.server.mirror_meta(self.server.load_mirror()),
                },
            )
            return

        doc = self.server.save_motion(
            after, verified=True, last_apply=state.now_iso()
        )
        LOG.info(
            "motion apply verified revision=%s",
            ((doc.get("configuration") or {}).get("MotionDetect") or {})
            .get("legacy", {})
            .get("revision"),
        )
        self._send_json(
            HTTPStatus.OK,
            {
                "changed": True,
                "verified": True,
                "motion": doc["configuration"]["MotionDetect"],
                "mirror": self.server.mirror_meta(doc),
            },
        )

    def _read_json(self) -> Optional[Dict[str, Any]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad request body"})
            return None
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid json"})
            return None
        if not isinstance(value, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid json"})
            return None
        return value

    def _send_static(self, name: str) -> None:
        if name not in STATIC_FILES:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        path = STATIC_DIR / name
        try:
            body = path.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", STATIC_FILES[name])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(
        self,
        status: int,
        value: Dict[str, Any],
        cookie: Optional[str] = None,
        expire_cookie: bool = False,
    ) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            if expire_cookie:
                self.send_header(
                    "Set-Cookie",
                    "{}={}; Path=/; HttpOnly; SameSite=Strict; Max-Age=0".format(
                        COOKIE_NAME, ""
                    ),
                )
            else:
                self.send_header(
                    "Set-Cookie",
                    "{}={}; Path=/; HttpOnly; SameSite=Strict".format(
                        COOKIE_NAME, cookie
                    ),
                )
        self.end_headers()
        self.wfile.write(body)
