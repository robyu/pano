#!/usr/bin/env python3
"""Loopback-only console server for a single Amcrest/Dahua camera.

Phase 1: browser login, in-memory session, and snapshot proxying. The server
binds 127.0.0.1 only. Every route lives under ``/s/<token>/`` and the token is
checked on every request. Host and Origin are checked to block DNS rebinding
and cross-origin writes. Camera credentials are kept in memory only.
"""

from __future__ import annotations

import hmac
import json
import secrets
import sys
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

from camera import AuthError, CameraClient, CameraError, redact_text

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
}
COOKIE_NAME = "amcrest_session"
MAX_BODY = 4096


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: Tuple[str, int],
        camera_config: Dict[str, Any],
        token: str,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(address, ConsoleHandler)
        self.camera_config = camera_config
        self.token = token
        self.name = name or str(camera_config.get("host") or "camera")
        self.session: Optional[Dict[str, Any]] = None
        self.session_lock = threading.Lock()
        host, port = self.server_address[0], self.server_address[1]
        self.allowed_hosts = {
            "{}:{}".format(host, port),
            "localhost:{}".format(port),
            "127.0.0.1:{}".format(port),
            "[::1]:{}".format(port),
        }

    def make_client(self, user: str, password: str) -> CameraClient:
        config = self.camera_config
        return CameraClient(
            config["host"],
            int(config.get("port", 80)),
            user,
            password,
            timeout=float(config.get("timeout", 20.0)),
            auth=str(config.get("auth", "auto")),
            model=config.get("model") or None,
            request_delay=float(config.get("request_delay", 0.0)),
        )

    def get_session(self) -> Optional[Dict[str, Any]]:
        with self.session_lock:
            return self.session

    def set_session(self, session: Optional[Dict[str, Any]]) -> None:
        with self.session_lock:
            self.session = session


class ConsoleHandler(BaseHTTPRequestHandler):
    server: ConsoleServer
    server_version = "AmcrestConsole/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        message = fmt % args
        message = message.replace(self.server.token, "<token>")
        sys.stderr.write("console: {}\n".format(redact_text(message)))

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        if not self._check_host():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad host"})
            return
        route = self._strip_token()
        if route is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if method == "POST" and not self._check_origin():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "bad origin"})
            return
        try:
            if method == "GET":
                self._route_get(route)
            else:
                self._route_post(route)
        except AuthError as error:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)})
        except CameraError as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
        except Exception as error:  # pragma: no cover - defensive
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal error: {}".format(type(error).__name__)},
            )

    def _check_host(self) -> bool:
        host = self.headers.get("Host", "")
        return host in self.server.allowed_hosts

    def _check_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlsplit(origin)
        if parsed.scheme != "http":
            return False
        return parsed.netloc in self.server.allowed_hosts

    def _strip_token(self) -> Optional[str]:
        path = urlsplit(self.path).path
        prefix = "/s/{}/".format(self.server.token)
        if path == "/s/{}".format(self.server.token):
            return "/"
        if not path.startswith(prefix):
            return None
        route = path[len(prefix) - 1:]
        return route or "/"

    def _route_get(self, route: str) -> None:
        if route in ("/", "/index.html"):
            self._send_static("index.html")
        elif route.startswith("/static/"):
            self._send_static(route[len("/static/"):])
        elif route == "/api/session":
            self._send_json(
                HTTPStatus.OK,
                {"authenticated": self.server.get_session() is not None},
            )
        elif route == "/api/camera":
            self._api_camera()
        elif route == "/api/snapshot":
            self._api_snapshot()
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _route_post(self, route: str) -> None:
        if route == "/api/login":
            self._api_login()
        elif route == "/api/logout":
            self._api_logout()
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
        client = self.server.make_client(user, password)
        try:
            client.verify_credentials()
        except AuthError:
            time.sleep(1.0)
            self._send_json(
                HTTPStatus.UNAUTHORIZED, {"error": "invalid credentials"}
            )
            return
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
        content_type = headers.get("Content-Type") or "image/jpeg"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

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
                    "{}={}; Path=/s/{}/; HttpOnly; SameSite=Strict; Max-Age=0".format(
                        COOKIE_NAME, "", self.server.token
                    ),
                )
            else:
                self.send_header(
                    "Set-Cookie",
                    "{}={}; Path=/s/{}/; HttpOnly; SameSite=Strict".format(
                        COOKIE_NAME, cookie, self.server.token
                    ),
                )
        self.end_headers()
        self.wfile.write(body)
