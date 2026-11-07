import base64
import hashlib
import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import camera
import state
import server

BASE = "/"


class MockCamera:
    def __init__(self):
        self.mask_values = [0x3FFFFF] * 18
        self.set_configs = []
        self.rpc_set_configs = []
        self.rpc_logins = 0
        self.ignore_writes = False
        self.rpc_realm = "Login to TestCam"
        self.rpc_random = "1234567"
        self.rpc_session = 98765
        self.rpc_unauthorized = 0
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def motion_body(self):
                lines = [
                    "table.MotionDetect[0].Enable=true",
                    "table.MotionDetect[0].Level=3",
                ]
                with outer.lock:
                    values = list(outer.mask_values)
                for row, value in enumerate(values):
                    lines.append(
                        "table.MotionDetect[0].Region[{}]={}".format(row, value)
                    )
                lines.extend(
                    [
                        "table.MotionDetect[0].MotionDetectWindow[0].Id=0",
                        "table.MotionDetect[0].MotionDetectWindow[0].Name=Region0",
                        "table.MotionDetect[0].MotionDetectWindow[0].Sensitive=60",
                        "table.MotionDetect[0].MotionDetectWindow[0].Threshold=5",
                    ]
                )
                for row in range(18):
                    lines.append(
                        "table.MotionDetect[0].MotionDetectWindow[0].Region[{}]={}".format(
                            row, values[row]
                        )
                    )
                return ("\n".join(lines) + "\n").encode()

            def rpc_table(self):
                with outer.lock:
                    values = list(outer.mask_values)
                return [
                    {
                        "Enable": True,
                        "Level": 3,
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
                        self.send_json(
                            {
                                "id": payload.get("id"),
                                "result": True,
                                "params": {"table": self.rpc_table()},
                            }
                        )
                        return
                    if method == "configManager.setConfig":
                        table = params.get("table") or []
                        with outer.lock:
                            outer.rpc_set_configs.append(params)
                            if not outer.ignore_writes and table:
                                region = table[0].get("Region")
                                if isinstance(region, list) and len(region) == 18:
                                    outer.mask_values = [
                                        int(value) for value in region
                                    ]
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
                    body = self.motion_body() if name == "MotionDetect" else b"table.ok=1\n"
                elif action == "setConfig":
                    with outer.lock:
                        outer.set_configs.append(query)
                    body = b"Error\n"
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
        self.server = server.ConsoleServer(
            ("127.0.0.1", 0),
            config,
            name="cam-test",
            state_path=self.state_path,
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

    def test_unknown_static_is_not_found(self):
        status, _headers, _body = self.request("GET", BASE + "static/../server.py")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
