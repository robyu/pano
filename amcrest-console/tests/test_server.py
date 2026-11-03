import base64
import http.client
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server

TOKEN = "testtoken"
BASE = "/s/{}/".format(TOKEN)


class MockCamera:
    def __init__(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

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
        self.server = server.ConsoleServer(
            ("127.0.0.1", 0), config, TOKEN, name="cam-test"
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.mock.__exit__(None, None, None)

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


class SecurityTests(ServerTestCase):
    def test_wrong_token_is_not_found(self):
        status, _headers, _body = self.request("GET", "/s/wrong/api/session")
        self.assertEqual(status, 404)

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


class LoginTests(ServerTestCase):
    def test_login_success_sets_hardened_cookie(self):
        status, headers, cookie = self.login()
        self.assertEqual(status, 200)
        set_cookie = headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=Strict", set_cookie)
        self.assertIn("Path=/s/{}/".format(TOKEN), set_cookie)
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


class StaticTests(ServerTestCase):
    def test_index_is_served(self):
        status, headers, body = self.request("GET", BASE)
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"Amcrest Console", body)

    def test_unknown_static_is_not_found(self):
        status, _headers, _body = self.request("GET", BASE + "static/../server.py")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
