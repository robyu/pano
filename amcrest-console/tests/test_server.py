import base64
import copy
import hashlib
import http.client
import json
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import camera
import state
import server

BASE = "/"


class MockCamera:
    def __init__(self):
        self.mask_values = [0x3FFFFF] * 18
        self.motion_enable = "true"
        self.motion_level = "3"
        self.set_configs = []
        self.rpc_set_configs = []
        self.rpc_logins = 0
        self.ignore_writes = False
        self.reject_cgi_sections = set()
        self.rpc_realm = "Login to TestCam"
        self.rpc_random = "1234567"
        self.rpc_session = 98765
        self.rpc_unauthorized = 0
        self.lock = threading.Lock()
        self.sections = {
            "General": {
                "General.LocalNo": "8",
                "General.MachineName": "AMC00270_3X76D1",
            },
            "Network": {
                "Network.DefaultInterface": "eth0",
                "Network.Domain": "IPC",
                "Network.Hostname": "cam-test",
                "Network.eth0.DhcpEnable": "false",
                "Network.eth0.IPAddress": "192.168.2.10",
                "Network.eth0.SubnetMask": "255.255.255.0",
                "Network.eth0.DefaultGateway": "192.168.2.1",
                "Network.eth0.MTU": "1500",
                "Network.eth0.DnsServers[0]": "192.168.2.1",
                "Network.eth0.DnsServers[1]": "0.0.0.0",
            },
            "NAS": {
                "NAS[0].Address": "192.168.2.8",
                "NAS[0].Port": "21",
                "NAS[0].Protocol": "FTP",
                "NAS[0].Enable": "true",
                "NAS[0].Directory": "cam-test",
                "NAS[0].UserName": "upload",
                "NAS[0].Password": "ftppass",
                "NAS[0].CharacterEncoding": "UTF-8",
                "NAS[0].TimeOut": "0",
            },
            "NTP": {
                "NTP.Address": "clock.isc.org",
                "NTP.Enable": "true",
                "NTP.Port": "123",
                "NTP.TimeZone": "28",
                "NTP.UpdatePeriod": "10",
            },
            "Encode": {
                "Encode[0].MainFormat[0].Video.FPS": "20",
                "Encode[0].MainFormat[0].Video.resolution": "1920x1080",
                "Encode[0].MainFormat[0].Video.Width": "1920",
                "Encode[0].MainFormat[0].Video.Height": "1080",
            },
            "AutoMaintain": {
                "AutoMaintain.AutoRebootEnable": "true",
                "AutoMaintain.AutoRebootDay": "7",
                "AutoMaintain.AutoRebootHour": "7",
                "AutoMaintain.AutoRebootMinute": "20",
            },
        }
        self.rpc_tables = {
            "Network": {
                "DefaultInterface": "eth0",
                "Domain": "IPC",
                "Hostname": "cam-test",
                "eth0": {
                    "DhcpEnable": False,
                    "IPAddress": "192.168.2.10",
                    "SubnetMask": "255.255.255.0",
                    "DefaultGateway": "192.168.2.1",
                    "MTU": 1500,
                },
            },
            "NTP": {
                "Address": "clock.isc.org",
                "Enable": True,
                "Port": 123,
                "TimeZone": 28,
                "UpdatePeriod": 10,
            },
        }
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def values_for(self, name):
                if name == "MotionDetect":
                    with outer.lock:
                        values = list(outer.mask_values)
                        enable = outer.motion_enable
                        level = outer.motion_level
                    result = {
                        "MotionDetect[0].Enable": enable,
                        "MotionDetect[0].Level": level,
                    }
                    for row, value in enumerate(values):
                        result[
                            "MotionDetect[0].Region[{}]".format(row)
                        ] = str(value)
                    result[
                        "MotionDetect[0].MotionDetectWindow[0].Id"
                    ] = "0"
                    result[
                        "MotionDetect[0].MotionDetectWindow[0].Name"
                    ] = "Region0"
                    result[
                        "MotionDetect[0].MotionDetectWindow[0].Sensitive"
                    ] = "60"
                    result[
                        "MotionDetect[0].MotionDetectWindow[0].Threshold"
                    ] = "5"
                    for row, value in enumerate(values):
                        result[
                            "MotionDetect[0].MotionDetectWindow[0].Region[{}]".format(
                                row
                            )
                        ] = str(value)
                    return result
                with outer.lock:
                    return dict(outer.sections.get(name, {}))

            def config_body(self, name):
                values = self.values_for(name)
                lines = [
                    "table.{}={}".format(key, value)
                    for key, value in values.items()
                ]
                return ("\n".join(lines) + "\n").encode()

            def motion_body(self):
                return self.config_body("MotionDetect")

            def rpc_table(self):
                with outer.lock:
                    values = list(outer.mask_values)
                    enable = outer.motion_enable == "true"
                    level = int(outer.motion_level)
                return [
                    {
                        "Enable": enable,
                        "Level": level,
                        "Region": values,
                        "MotionDetectWindow": [
                            {
                                "Id": 0,
                                "Name": "Region0",
                                "Sensitive": 60,
                                "Threshold": 5,
                                "Region": camera.mirror_region_values(values),
                            }
                        ],
                    }
                ]

            def rpc_table_for(self, name):
                if name == "MotionDetect":
                    return self.rpc_table()
                with outer.lock:
                    return copy.deepcopy(outer.rpc_tables.get(name))

            def send_json(self, value, headers=None):
                body = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                for name, header_value in (headers or {}).items():
                    self.send_header(name, header_value)
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    self.send_response(400)
                    self.end_headers()
                    return
                if self.path.startswith("/RPC2_Login"):
                    params = payload.get("params") or {}
                    if not params.get("password"):
                        with outer.lock:
                            outer.rpc_logins += 1
                        self.send_json(
                            {
                                "error": {"code": 401, "message": "unauthorized"},
                                "id": payload.get("id"),
                                "params": {
                                    "encryption": "Default",
                                    "realm": outer.rpc_realm,
                                    "random": outer.rpc_random,
                                },
                                "result": False,
                                "session": outer.rpc_session,
                            }
                        )
                        return
                    digest = hashlib.md5(
                        "{}:{}:{}".format(
                            "admin", outer.rpc_realm, "testpass"
                        ).encode()
                    ).hexdigest().upper()
                    expected = hashlib.md5(
                        "{}:{}:{}".format(
                            "admin", outer.rpc_random, digest
                        ).encode()
                    ).hexdigest().upper()
                    ok = params.get("password") == expected
                    body = {
                        "id": payload.get("id"),
                        "result": ok,
                        "session": outer.rpc_session,
                    }
                    if not ok:
                        body["error"] = {"code": 401, "message": "unauthorized"}
                        body["params"] = {"error": "PasswordNotValid"}
                    self.send_json(body)
                    return
                if self.path.startswith("/RPC2"):
                    cookie = self.headers.get("Cookie", "")
                    expected_cookie = "DhWebClientSessionID={}".format(
                        outer.rpc_session
                    )
                    if expected_cookie not in cookie:
                        with outer.lock:
                            outer.rpc_unauthorized += 1
                        body = (
                            b"<!DOCTYPE html>\n<html><head><title></title>"
                            b"</head></html>\n"
                        )
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    method = payload.get("method")
                    params = payload.get("params") or {}
                    if method == "configManager.getConfig":
                        name = params.get("name")
                        table = self.rpc_table_for(name)
                        if table is None:
                            table = {}
                        self.send_json(
                            {
                                "id": payload.get("id"),
                                "result": True,
                                "params": {"table": table},
                            }
                        )
                        return
                    if method == "configManager.setConfig":
                        name = params.get("name")
                        table = params.get("table") or []
                        with outer.lock:
                            outer.rpc_set_configs.append(params)
                            if not outer.ignore_writes and table:
                                if name == "MotionDetect" and isinstance(table, list):
                                    region = table[0].get("Region")
                                    if isinstance(region, list) and len(region) == 18:
                                        outer.mask_values = [
                                            int(value) for value in region
                                        ]
                                    enable = table[0].get("Enable")
                                    if isinstance(enable, bool):
                                        outer.motion_enable = (
                                            "true" if enable else "false"
                                        )
                                    level = table[0].get("Level")
                                    if isinstance(level, int):
                                        outer.motion_level = str(level)
                                elif name in outer.rpc_tables:
                                    outer.rpc_tables[name] = copy.deepcopy(table)
                        self.send_json(
                            {
                                "id": payload.get("id"),
                                "result": True,
                                "params": {},
                            }
                        )
                        return
                self.send_response(404)
                self.end_headers()

            def do_GET(self):
                expected = "Basic " + base64.b64encode(b"admin:testpass").decode()
                if self.headers.get("Authorization") != expected:
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="Device_CGI"')
                    self.end_headers()
                    return
                query = parse_qs(urlparse(self.path).query)
                action = (query.get("action") or [""])[0]
                if action == "getMachineName":
                    body = b"table.MachineName=TestCam\n"
                elif action == "getDeviceType":
                    body = b"table.type=IP2M-842\n"
                elif action == "getConfig":
                    name = (query.get("name") or [""])[0]
                    if name == "MotionDetect":
                        body = self.motion_body()
                    elif name in outer.sections:
                        body = self.config_body(name)
                    else:
                        body = b"table.ok=1\n"
                elif action == "setConfig":
                    with outer.lock:
                        outer.set_configs.append(query)
                    keys = [key for key in query if key != "action"]
                    section = ""
                    if keys:
                        section = re.split(r"[.\[]", keys[0], 1)[0]
                    if section == "MotionDetect":
                        if not outer.ignore_writes:
                            for row in range(18):
                                key = "MotionDetect[0].Region[{}]".format(row)
                                if key in query:
                                    outer.mask_values[row] = int(query[key][0])
                            if "MotionDetect[0].Enable" in query:
                                outer.motion_enable = query[
                                    "MotionDetect[0].Enable"
                                ][0]
                            if "MotionDetect[0].Level" in query:
                                outer.motion_level = query[
                                    "MotionDetect[0].Level"
                                ][0]
                        body = b"Error\n"
                    elif section in outer.reject_cgi_sections:
                        body = b"Error\n"
                    else:
                        if not outer.ignore_writes:
                            target = outer.sections.setdefault(section, {})
                            for key in keys:
                                target[key] = query[key][0]
                        body = b"OK\n"
                elif self.path.startswith("/cgi-bin/snapshot.cgi"):
                    body = b"\xff\xd8\xff\xd9"
                else:
                    body = b"table.ok=1\n"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

    @property
    def port(self):
        return self.httpd.server_address[1]


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.mock = MockCamera()
        self.mock.__enter__()
        config = {
            "host": "127.0.0.1",
            "port": self.mock.port,
            "auth": "basic",
            "model": "amcrest-ip2m-842",
            "timeout": 2,
            "request_delay": 0,
        }
        self.temp = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp.name) / "cam-test.json"
        self.backup_dir = Path(self.temp.name) / "backups"
        self.server = server.ConsoleServer(
            ("127.0.0.1", 0),
            config,
            name="cam-test",
            state_path=self.state_path,
            backup_dir=self.backup_dir,
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.mock.__exit__(None, None, None)
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_address[1], timeout=5
        )
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        data = response.read()
        result = (response.status, dict(response.getheaders()), data)
        conn.close()
        return result

    def login(self, password="testpass"):
        body = json.dumps({"user": "admin", "password": password})
        status, headers, _data = self.request(
            "POST",
            BASE + "api/login",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        cookie = headers.get("Set-Cookie", "").split(";", 1)[0]
        return status, headers, cookie

    def put_json(self, path, value, cookie=None, origin=None):
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        if origin is not None:
            headers["Origin"] = origin
        return self.request(
            "PUT", BASE + path, body=json.dumps(value), headers=headers
        )

    def get_motion(self, cookie):
        status, _headers, body = self.request(
            "GET", BASE + "api/motion", headers={"Cookie": cookie}
        )
        return status, json.loads(body)

    def get_json(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        status, response_headers, body = self.request(
            "GET", BASE + path, headers=headers
        )
        return status, response_headers, json.loads(body)

    def post_json(self, path, value, cookie=None, origin=None):
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        if origin is not None:
            headers["Origin"] = origin
        return self.request(
            "POST", BASE + path, body=json.dumps(value), headers=headers
        )


class SecurityTests(ServerTestCase):
    def test_old_token_path_is_not_found(self):
        status, _headers, _body = self.request("GET", "/s/wrong/api/session")
        self.assertEqual(status, 404)

    def test_private_ip_host_is_allowed(self):
        host = "192.168.2.50:{}".format(self.server.server_address[1])
        status, _headers, _body = self.request(
            "GET", BASE + "api/session", headers={"Host": host}
        )
        self.assertEqual(status, 200)

    def test_ip_host_with_wrong_port_is_rejected(self):
        status, _headers, _body = self.request(
            "GET", BASE + "api/session", headers={"Host": "192.168.2.50:1"}
        )
        self.assertEqual(status, 400)

    def test_bad_host_is_rejected(self):
        status, _headers, _body = self.request(
            "GET", BASE + "api/session", headers={"Host": "evil.example"}
        )
        self.assertEqual(status, 400)

    def test_bad_origin_is_rejected(self):
        body = json.dumps({"user": "admin", "password": "testpass"})
        status, _headers, _body = self.request(
            "POST",
            BASE + "api/login",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://evil.example",
            },
        )
        self.assertEqual(status, 403)

    def test_session_starts_unauthenticated(self):
        status, _headers, body = self.request("GET", BASE + "api/session")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"authenticated": False})

    def test_snapshot_requires_login(self):
        status, _headers, _body = self.request("GET", BASE + "api/snapshot")
        self.assertEqual(status, 401)

    def test_snapshot_rejects_wrong_cookie(self):
        self.login()
        status, _headers, _body = self.request(
            "GET", BASE + "api/snapshot", headers={"Cookie": "amcrest_session=wrong"}
        )
        self.assertEqual(status, 401)

    def test_logout_requires_matching_cookie(self):
        _status, _headers, cookie = self.login()
        status, _headers, _body = self.request("POST", BASE + "api/logout")
        self.assertEqual(status, 401)
        status, _headers, _body = self.request(
            "GET", BASE + "api/snapshot", headers={"Cookie": cookie}
        )
        self.assertEqual(status, 200)


class LoginTests(ServerTestCase):
    def test_login_success_sets_hardened_cookie(self):
        status, headers, cookie = self.login()
        self.assertEqual(status, 200)
        set_cookie = headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=Strict", set_cookie)
        self.assertIn("Path=/;", set_cookie)
        self.assertTrue(cookie.startswith("amcrest_session="))

    def test_login_failure_is_generic(self):
        body = json.dumps({"user": "admin", "password": "wrong"})
        status, _headers, response = self.request(
            "POST",
            BASE + "api/login",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(response), {"error": "invalid credentials"})

    def test_snapshot_after_login(self):
        _status, _headers, cookie = self.login()
        status, headers, body = self.request(
            "GET", BASE + "api/snapshot", headers={"Cookie": cookie}
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "image/jpeg")
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(body, b"\xff\xd8\xff\xd9")

    def test_camera_info_after_login(self):
        _status, _headers, cookie = self.login()
        status, _headers, body = self.request(
            "GET", BASE + "api/camera", headers={"Cookie": cookie}
        )
        self.assertEqual(status, 200)
        info = json.loads(body)
        self.assertEqual(info["name"], "cam-test")
        self.assertEqual(info["device_type"], "IP2M-842")
        self.assertEqual(info["auth"], "basic")

    def test_second_login_invalidates_first_browser(self):
        _status, _headers, first = self.login()
        _status, _headers, second = self.login()
        self.assertNotEqual(first, second)
        status, _headers, _body = self.request(
            "GET", BASE + "api/snapshot", headers={"Cookie": first}
        )
        self.assertEqual(status, 401)
        status, _headers, _body = self.request(
            "GET", BASE + "api/snapshot", headers={"Cookie": second}
        )
        self.assertEqual(status, 200)
        status, _headers, body = self.request(
            "GET", BASE + "api/session", headers={"Cookie": first}
        )
        self.assertEqual(json.loads(body), {"authenticated": False})
        status, _headers, body = self.request(
            "GET", BASE + "api/session", headers={"Cookie": second}
        )
        self.assertEqual(json.loads(body), {"authenticated": True})

    def test_logout_clears_session(self):
        _status, _headers, cookie = self.login()
        status, headers, _body = self.request(
            "POST", BASE + "api/logout", headers={"Cookie": cookie}
        )
        self.assertEqual(status, 200)
        self.assertIn("Max-Age=0", headers.get("Set-Cookie", ""))
        status, _headers, body = self.request(
            "GET", BASE + "api/session", headers={"Cookie": cookie}
        )
        self.assertEqual(json.loads(body), {"authenticated": False})


class MotionTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        _status, _headers, self.cookie = self.login()
        self.origin = "http://127.0.0.1:{}".format(self.server.server_address[1])

    def rows(self):
        status, body = self.get_motion(self.cookie)
        self.assertEqual(status, 200)
        return body["motion"]["legacy"]["rows"], body["motion"]["legacy"]["revision"]

    def test_motion_requires_login(self):
        status, _headers, _body = self.request("GET", BASE + "api/motion")
        self.assertEqual(status, 401)

    def test_motion_get_creates_mirror(self):
        rows, revision = self.rows()
        self.assertEqual(len(rows), 18)
        self.assertEqual(len(rows[0]), 22)
        self.assertTrue(revision)
        self.assertTrue(self.state_path.exists())
        saved = state.load(self.state_path)
        self.assertEqual(
            saved["configuration"]["MotionDetect"]["legacy"]["revision"],
            revision,
        )
        self.assertEqual(len(saved["configuration"]["MotionDetect"]["windows"]), 1)
        self.assertTrue(saved["configuration"]["MotionDetect"]["windows"][0]["readonly"])

    def test_motion_falls_back_to_stale_mirror(self):
        self.rows()
        closed = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        closed_port = closed.server_address[1]
        closed.server_close()
        client = self.server.get_session()["client"]
        client.port = closed_port
        client.base = "http://127.0.0.1:{}".format(closed_port)
        status, body = self.get_motion(self.cookie)
        self.assertEqual(status, 200)
        self.assertTrue(body["motion"]["stale"])
        self.assertTrue(body["mirror"]["stale"])
        self.assertTrue(body["motion"]["legacy"]["revision"])

    def test_apply_requires_login(self):
        rows, revision = self.rows()
        status, _headers, _body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision, "confirm": True},
            origin=self.origin,
        )
        self.assertEqual(status, 401)

    def test_apply_rejects_bad_origin(self):
        rows, revision = self.rows()
        status, _headers, _body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision, "confirm": True},
            cookie=self.cookie,
            origin="http://evil.example",
        )
        self.assertEqual(status, 403)

    def test_apply_requires_confirm(self):
        rows, revision = self.rows()
        status, _headers, _body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision},
            cookie=self.cookie,
            origin=self.origin,
        )
        self.assertEqual(status, 400)

    def test_apply_rejects_unknown_fields(self):
        rows, revision = self.rows()
        status, _headers, _body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision, "confirm": True, "window": 0},
            cookie=self.cookie,
            origin=self.origin,
        )
        self.assertEqual(status, 400)

    def test_apply_rejects_bad_shape(self):
        _rows, revision = self.rows()
        status, _headers, _body = self.put_json(
            "api/motion",
            {"rows": [[0] * 21] * 18, "revision": revision, "confirm": True},
            cookie=self.cookie,
            origin=self.origin,
        )
        self.assertEqual(status, 400)

    def test_stale_revision_conflicts_without_write(self):
        rows, _revision = self.rows()
        status, _headers, body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": "0" * 64, "confirm": True},
            cookie=self.cookie,
            origin=self.origin,
        )
        self.assertEqual(status, 409)
        self.assertEqual(self.mock.set_configs, [])
        self.assertIn("motion", json.loads(body))

    def test_unchanged_mask_does_not_write(self):
        rows, revision = self.rows()
        status, _headers, body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision, "confirm": True},
            cookie=self.cookie,
            origin=self.origin,
        )
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["changed"])
        self.assertEqual(self.mock.set_configs, [])

    def test_apply_writes_all_rows_and_verifies(self):
        rows, revision = self.rows()
        rows[0][0] = 0
        status, _headers, body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision, "confirm": True},
            cookie=self.cookie,
            origin=self.origin,
        )
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(result["changed"])
        self.assertTrue(result["verified"])
        self.assertEqual(len(self.mock.set_configs), 1)
        sent = self.mock.set_configs[0]
        region_keys = [
            key for key in sent if key.startswith("MotionDetect[0].Region[")
        ]
        self.assertEqual(len(region_keys), 18)
        self.assertFalse(any("MotionDetectWindow" in key for key in sent))
        self.assertEqual(len(self.mock.rpc_set_configs), 1)
        self.assertGreaterEqual(self.mock.rpc_logins, 1)
        self.assertEqual(self.mock.rpc_unauthorized, 0)
        rpc_table = self.mock.rpc_set_configs[0]["table"]
        self.assertEqual(len(rpc_table[0]["Region"]), 18)
        self.assertEqual(rpc_table[0]["Region"][0] & 1, 0)
        saved = state.load(self.state_path)
        self.assertIsNotNone(saved["mirror"]["last_apply"])
        self.assertEqual(
            saved["configuration"]["MotionDetect"]["legacy"]["rows"][0][0], 0
        )

    def test_verification_failure_returns_502_and_skips_mirror(self):
        rows, revision = self.rows()
        self.mock.ignore_writes = True
        rows[0][0] = 0
        status, _headers, body = self.put_json(
            "api/motion",
            {"rows": rows, "revision": revision, "confirm": True},
            cookie=self.cookie,
            origin=self.origin,
        )
        result = json.loads(body)
        self.assertEqual(status, 502)
        self.assertFalse(result["verified"])
        saved = state.load(self.state_path)
        self.assertIsNone(saved["mirror"]["last_apply"])

    def test_state_endpoint(self):
        status, _headers, _body = self.request(
            "GET", BASE + "api/state", headers={"Cookie": self.cookie}
        )
        self.assertEqual(status, 404)
        self.rows()
        status, _headers, body = self.request(
            "GET", BASE + "api/state", headers={"Cookie": self.cookie}
        )
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["state"]["camera"]["name"], "cam-test")


class StaticTests(ServerTestCase):
    def test_index_is_served(self):
        status, headers, body = self.request("GET", BASE)
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"Amcrest Console", body)
        self.assertIn(b"mask-legend", body)
        self.assertIn(b"motion-sensitive", body)
        self.assertIn(b"unpainted cells are ignored", body)
        self.assertIn(b"Legacy mask", body)
        self.assertIn(b"Region masks", body)
        self.assertIn(b"Region masks are read-only", body)
        self.assertIn(b"region-overlay", body)
        self.assertIn(b"Configuration", body)
        self.assertIn(b"config-form", body)
        self.assertIn(b"Download backup", body)
        self.assertIn(b"Raw configuration", body)

    def test_unknown_static_is_not_found(self):
        status, _headers, _body = self.request("GET", BASE + "static/../server.py")
        self.assertEqual(status, 404)



class ConfigTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        _status, _headers, self.cookie = self.login()
        self.origin = "http://127.0.0.1:{}".format(self.server.server_address[1])

    def get_config(self, name, cookie=None):
        status, _headers, body = self.get_json(
            "api/config?name={}".format(name), cookie=cookie or self.cookie
        )
        return status, body

    def post_config(self, value):
        return self.post_json(
            "api/config", value, cookie=self.cookie, origin=self.origin
        )

    def test_config_requires_login(self):
        status, _headers, _body = self.request("GET", BASE + "api/config")
        self.assertEqual(status, 401)

    def test_config_index_lists_allowlisted_sections(self):
        status, _headers, body = self.get_json(
            "api/config", cookie=self.cookie
        )
        self.assertEqual(status, 200)
        names = [section["name"] for section in body["sections"]]
        self.assertEqual(
            names,
            ["General", "Network", "NAS", "NTP", "Encode", "AutoMaintain",
             "MotionDetect"],
        )
        network = [s for s in body["sections"] if s["name"] == "Network"][0]
        self.assertTrue(network["dangerous"])
        self.assertEqual(network["confirm_text"], "APPLY NETWORK")

    def test_config_get_sanitizes_secrets(self):
        status, body = self.get_config("NAS")
        self.assertEqual(status, 200)
        section = body["section"]
        self.assertEqual(section["values"]["NAS[0].Password"], "<redacted>")
        self.assertIn("NAS[0].Password", section["redacted"])
        password = [
            field for field in section["fields"]
            if field["key"] == "NAS[0].Password"
        ][0]
        self.assertTrue(password["secret"])
        self.assertIsNone(password["value"])
        self.assertTrue(password["has_value"])

    def test_config_get_creates_mirror(self):
        status, body = self.get_config("NTP")
        self.assertEqual(status, 200)
        saved = state.load(self.state_path)
        entry = saved["configuration"]["NTP"]
        self.assertEqual(entry["values"]["NTP.Address"], "clock.isc.org")
        self.assertEqual(entry["revision"], body["section"]["revision"])

    def test_config_get_unknown_section_is_not_found(self):
        status, _body = self.get_config("FTP")
        self.assertEqual(status, 404)

    def test_config_get_falls_back_to_stale_mirror(self):
        self.get_config("NTP")
        closed = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        closed_port = closed.server_address[1]
        closed.server_close()
        client = self.server.get_session()["client"]
        client.port = closed_port
        client.base = "http://127.0.0.1:{}".format(closed_port)
        status, body = self.get_config("NTP")
        self.assertEqual(status, 200)
        self.assertTrue(body["section"]["stale"])
        self.assertTrue(body["mirror"]["stale"])

    def test_config_apply_rejects_unknown_fields(self):
        _status, body = self.get_config("NTP")
        status, _headers, _body = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "pool.ntp.org"},
                "revision": body["section"]["revision"],
                "confirm": True,
                "extra": True,
            }
        )
        self.assertEqual(status, 400)

    def test_config_apply_requires_confirm_and_revision(self):
        _status, body = self.get_config("NTP")
        status, _headers, _body = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "pool.ntp.org"},
                "revision": body["section"]["revision"],
            }
        )
        self.assertEqual(status, 400)
        status, _headers, _body = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "pool.ntp.org"},
                "confirm": True,
            }
        )
        self.assertEqual(status, 400)

    def test_config_apply_rejects_general_and_unknown(self):
        status, _headers, _body = self.post_config(
            {"name": "General", "changes": {"General.LocalNo": "9"},
             "revision": "x", "confirm": True}
        )
        self.assertEqual(status, 400)
        status, _headers, _body = self.post_config(
            {"name": "System", "changes": {"System.X": "1"},
             "revision": "x", "confirm": True}
        )
        self.assertEqual(status, 400)

    def test_config_apply_rejects_non_writable_field(self):
        _status, body = self.get_config("MotionDetect")
        status, _headers, _body = self.post_config(
            {
                "name": "MotionDetect",
                "changes": {"MotionDetect[0].Region[0]": "0"},
                "revision": body["section"]["revision"],
                "confirm": True,
            }
        )
        self.assertEqual(status, 400)

    def test_config_apply_stale_revision_conflicts(self):
        self.get_config("NTP")
        status, _headers, _body = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "pool.ntp.org"},
                "revision": "0" * 64,
                "confirm": True,
            }
        )
        self.assertEqual(status, 409)
        self.assertEqual(self.mock.set_configs, [])

    def test_config_apply_ntp_verifies_and_updates_mirror(self):
        _status, body = self.get_config("NTP")
        status, _headers, raw = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "pool.ntp.org"},
                "revision": body["section"]["revision"],
                "confirm": True,
            }
        )
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertTrue(result["changed"])
        self.assertTrue(result["verified"])
        self.assertEqual(self.mock.sections["NTP"]["NTP.Address"], "pool.ntp.org")
        saved = state.load(self.state_path)
        self.assertEqual(
            saved["configuration"]["NTP"]["values"]["NTP.Address"],
            "pool.ntp.org",
        )

    def test_config_apply_noop_does_not_write(self):
        _status, body = self.get_config("NTP")
        status, _headers, raw = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "clock.isc.org"},
                "revision": body["section"]["revision"],
                "confirm": True,
            }
        )
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertFalse(result["changed"])
        self.assertEqual(self.mock.set_configs, [])

    def test_config_apply_bad_value_is_rejected(self):
        _status, body = self.get_config("NTP")
        status, _headers, _body = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Port": "not-a-port"},
                "revision": body["section"]["revision"],
                "confirm": True,
            }
        )
        self.assertEqual(status, 400)

    def test_config_apply_nas_preserves_blank_secret(self):
        _status, body = self.get_config("NAS")
        status, _headers, raw = self.post_config(
            {
                "name": "NAS",
                "changes": {"NAS[0].UserName": "upload2"},
                "revision": body["section"]["revision"],
                "confirm": True,
                "confirm_text": "APPLY NAS",
            }
        )
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertTrue(result["verified"])
        self.assertEqual(
            self.mock.sections["NAS"]["NAS[0].Password"], "ftppass"
        )
        self.assertEqual(
            result["section"]["values"]["NAS[0].Password"], "<redacted>"
        )
        saved = state.load(self.state_path)
        self.assertEqual(
            saved["configuration"]["NAS"]["values"]["NAS[0].Password"],
            "<redacted>",
        )

    def test_config_secret_verification_failure_is_redacted(self):
        _status, body = self.get_config("NAS")
        self.mock.ignore_writes = True
        status, _headers, raw = self.post_config(
            {
                "name": "NAS",
                "changes": {"NAS[0].Password": "new-secret"},
                "revision": body["section"]["revision"],
                "confirm": True,
                "confirm_text": "APPLY NAS",
            }
        )
        text = raw.decode("utf-8")
        self.assertEqual(status, 502)
        self.assertNotIn("new-secret", text)
        self.assertNotIn("ftppass", text)
        result = json.loads(text)
        self.assertEqual(
            result["mismatches"]["NAS[0].Password"],
            {"expected": "<redacted>", "actual": "<redacted>"},
        )

    def test_config_apply_network_requires_phrase(self):
        _status, body = self.get_config("Network")
        payload = {
            "name": "Network",
            "changes": {"Network.Hostname": "cam-new"},
            "revision": body["section"]["revision"],
            "confirm": True,
        }
        status, _headers, _body = self.post_config(payload)
        self.assertEqual(status, 400)
        payload["confirm_text"] = "WRONG"
        status, _headers, _body = self.post_config(payload)
        self.assertEqual(status, 400)

    def test_config_apply_network_backs_up_and_verifies(self):
        _status, body = self.get_config("Network")
        status, _headers, raw = self.post_config(
            {
                "name": "Network",
                "changes": {"Network.Hostname": "cam-new"},
                "revision": body["section"]["revision"],
                "confirm": True,
                "confirm_text": "APPLY NETWORK",
            }
        )
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertTrue(result["verified"])
        self.assertTrue(result["backup"])
        self.assertTrue(Path(result["backup"]).exists())
        backups = list(self.backup_dir.glob("cam-test-*.json"))
        self.assertEqual(len(backups), 1)
        saved = state.load(self.state_path)
        self.assertEqual(
            saved["configuration"]["Network"]["values"]["Network.Hostname"],
            "cam-new",
        )

    def test_config_apply_network_disconnect_reports_unverified(self):
        _status, body = self.get_config("Network")
        client = self.server.get_session()["client"]
        closed = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        closed_port = closed.server_address[1]
        closed.server_close()
        original = client.set_section_changes

        def write_and_disconnect(name, changes):
            result = original(name, changes)
            client.port = closed_port
            client.base = "http://127.0.0.1:{}".format(closed_port)
            return result

        with mock.patch.object(
            client, "set_section_changes", side_effect=write_and_disconnect
        ):
            status, _headers, raw = self.post_config(
                {
                    "name": "Network",
                    "changes": {"Network.eth0.IPAddress": "192.168.2.99"},
                    "revision": body["section"]["revision"],
                    "confirm": True,
                    "confirm_text": "APPLY NETWORK",
                }
            )
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertFalse(result["verified"])
        self.assertTrue(result["disconnected"])
        self.assertTrue(result["backup"])
        self.assertTrue(result["mirror"]["stale"])

    def test_config_apply_verification_failure_returns_502(self):
        _status, body = self.get_config("NTP")
        self.mock.ignore_writes = True
        status, _headers, raw = self.post_config(
            {
                "name": "NTP",
                "changes": {"NTP.Address": "pool.ntp.org"},
                "revision": body["section"]["revision"],
                "confirm": True,
            }
        )
        result = json.loads(raw)
        self.assertEqual(status, 502)
        self.assertFalse(result["verified"])
        self.assertIn("NTP.Address", result["mismatches"])
        saved = state.load(self.state_path)
        self.assertEqual(
            saved["configuration"]["NTP"]["values"]["NTP.Address"],
            "clock.isc.org",
        )

    def test_config_apply_motion_enable_and_level(self):
        _status, body = self.get_config("MotionDetect")
        status, _headers, raw = self.post_config(
            {
                "name": "MotionDetect",
                "changes": {
                    "MotionDetect[0].Enable": "false",
                    "MotionDetect[0].Level": "5",
                },
                "revision": body["section"]["revision"],
                "confirm": True,
            }
        )
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertTrue(result["verified"])
        self.assertEqual(self.mock.motion_enable, "false")
        self.assertEqual(self.mock.motion_level, "5")
        saved = state.load(self.state_path)
        entry = saved["configuration"]["MotionDetectConfig"]
        self.assertEqual(entry["values"]["MotionDetect[0].Level"], "5")

    def test_config_apply_backup_failure_aborts_write(self):
        _status, body = self.get_config("Network")
        with mock.patch.object(
            self.server,
            "write_backup",
            side_effect=server.CameraError("backup failed"),
        ):
            status, _headers, _body = self.post_config(
                {
                    "name": "Network",
                    "changes": {"Network.Hostname": "cam-new"},
                    "revision": body["section"]["revision"],
                    "confirm": True,
                    "confirm_text": "APPLY NETWORK",
                }
            )
        self.assertEqual(status, 502)
        self.assertEqual(self.mock.set_configs, [])

    def test_config_apply_duplicate_keys_refused(self):
        client = self.server.get_session()["client"]
        duplicate = {
            "name": "NTP",
            "values": {"NTP.Address": "clock.isc.org"},
            "duplicates": ["NTP.Address"],
            "raw": "",
            "revision": "a" * 64,
        }
        with mock.patch.object(client, "get_section", return_value=duplicate):
            status, _headers, _body = self.post_config(
                {
                    "name": "NTP",
                    "changes": {"NTP.Address": "pool.ntp.org"},
                    "revision": "a" * 64,
                    "confirm": True,
                }
            )
        self.assertEqual(status, 409)

    def test_backup_download(self):
        status, headers, body = self.get_json(
            "api/backup", cookie=self.cookie
        )
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        self.assertEqual(body["kind"], state.BACKUP_KIND)
        self.assertTrue(body["complete"])
        self.assertEqual(len(body["sections"]), 7)
        self.assertEqual(
            body["sections"]["NAS"]["values"]["NAS[0].Password"],
            "<redacted>",
        )

    def test_backup_requires_login(self):
        status, _headers, _body = self.request("GET", BASE + "api/backup")
        self.assertEqual(status, 401)

    def test_backup_incomplete_marks_stale(self):
        self.get_config("NTP")
        client = self.server.get_session()["client"]
        with mock.patch.object(
            client,
            "get_section",
            side_effect=server.CameraError("camera offline"),
        ):
            status, headers, body = self.get_json(
                "api/backup", cookie=self.cookie
            )
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        self.assertFalse(body["complete"])
        self.assertTrue(body["stale"])
        self.assertIn("NTP", body["sections"])
        self.assertTrue(body["errors"])


if __name__ == "__main__":
    unittest.main()
