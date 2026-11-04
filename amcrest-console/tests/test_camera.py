import base64
import hashlib
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import camera


class MockCamera:
    def __init__(self, delay=0.0):
        self.requests = []
        self.active = 0
        self.max_active = 0
        self.delay = delay
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                with outer.lock:
                    outer.active += 1
                    outer.max_active = max(outer.max_active, outer.active)
                try:
                    if outer.delay:
                        time.sleep(outer.delay)
                    outer.requests.append(self.path)
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
                    elif action == "getSoftwareVersion":
                        body = b"table.version=2.212.0000.2.R\n"
                    elif self.path.startswith("/cgi-bin/snapshot.cgi"):
                        body = b"\xff\xd8\xff\xd9"
                    else:
                        body = b"table.ok=1\n"
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                finally:
                    with outer.lock:
                        outer.active -= 1

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


class MirrorTests(unittest.TestCase):
    def test_mirror_region_values(self):
        self.assertEqual(camera.mirror_region_values([1]), [1 << 21])
        self.assertEqual(camera.mirror_region_values([1 << 21]), [1])
        values = [0x3FFFFF, 4194291, 0]
        self.assertEqual(
            camera.mirror_region_values(camera.mirror_region_values(values)),
            values,
        )


class RpcLoginHashTests(unittest.TestCase):
    def test_default_hash_is_uppercase(self):
        h1 = hashlib.md5(b"admin:realm:testpass").hexdigest().upper()
        expected = hashlib.md5(
            "admin:random:{}".format(h1).encode()
        ).hexdigest().upper()
        result = camera.rpc_default_password(
            "admin", "realm", "random", "testpass"
        )
        self.assertEqual(result, expected)
        self.assertTrue(any(char.isalpha() and char.isupper() for char in result))


class LoggingTests(unittest.TestCase):
    def test_loggable_redacts_secrets(self):
        text = camera.loggable(
            {
                "Password": "secret-value",
                "session": "session-value",
                "Cookie": "cookie-value",
                "nested": [{"token": "token-value"}],
                "Region": [1, 2],
            }
        )
        self.assertNotIn("secret-value", text)
        self.assertNotIn("session-value", text)
        self.assertNotIn("cookie-value", text)
        self.assertNotIn("token-value", text)
        self.assertIn("<redacted>", text)

    def test_loggable_truncates(self):
        text = camera.loggable({"data": "x" * 2000}, limit=100)
        self.assertLessEqual(len(text), 140)
        self.assertIn("chars)", text)


class CredentialTests(unittest.TestCase):
    def test_verify_credentials_uses_machine_name(self):
        with MockCamera() as mock:
            client = camera.CameraClient(
                "127.0.0.1", mock.port, "admin", "testpass", timeout=2, auth="basic"
            )
            values = client.verify_credentials()
        self.assertEqual(values.get("MachineName"), "TestCam")
        self.assertTrue(any("getMachineName" in path for path in mock.requests))
        self.assertFalse(any("getSoftwareVersion" in path for path in mock.requests))

    def test_identity_skips_software_version_for_ip2m(self):
        with MockCamera() as mock:
            client = camera.CameraClient(
                "127.0.0.1",
                mock.port,
                "admin",
                "testpass",
                timeout=2,
                auth="basic",
                model="amcrest-ip2m-842",
            )
            identity = client.identity()
        self.assertIn("getSoftwareVersion", identity["magic_skipped"])
        self.assertNotIn("getSoftwareVersion", identity["magic"])

    def test_identity_fetches_software_version_for_ip3m(self):
        with MockCamera() as mock:
            client = camera.CameraClient(
                "127.0.0.1",
                mock.port,
                "admin",
                "testpass",
                timeout=2,
                auth="basic",
                model="amcrest-ip3m-943",
            )
            identity = client.identity()
        self.assertNotIn("magic_skipped", identity)
        self.assertEqual(
            identity["magic"]["getSoftwareVersion"].get("version"),
            "2.212.0000.2.R",
        )

    def test_identity_is_cached(self):
        with MockCamera() as mock:
            client = camera.CameraClient(
                "127.0.0.1", mock.port, "admin", "testpass", timeout=2, auth="basic"
            )
            client.identity()
            count = len(mock.requests)
            client.identity()
        self.assertEqual(len(mock.requests), count)


class BackoffTests(unittest.TestCase):
    def test_backoff_grows_after_failure_and_resets_after_success(self):
        server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        port = server.server_address[1]
        server.server_close()
        client = camera.CameraClient(
            "127.0.0.1",
            port,
            "admin",
            "testpass",
            timeout=1,
            backoff_base=0.01,
            backoff_max=0.02,
        )
        with self.assertRaises(camera.CameraError):
            client.get("/cgi-bin/test")
        self.assertAlmostEqual(client._backoff, 0.01)
        with self.assertRaises(camera.CameraError):
            client.get("/cgi-bin/test")
        self.assertAlmostEqual(client._backoff, 0.02)

        with MockCamera() as mock:
            client.port = mock.port
            client.base = "http://127.0.0.1:{}".format(mock.port)
            client.get("/cgi-bin/test")
        self.assertEqual(client._backoff, 0.0)


class SerializationTests(unittest.TestCase):
    def test_requests_are_serialized(self):
        with MockCamera(delay=0.1) as mock:
            client = camera.CameraClient(
                "127.0.0.1", mock.port, "admin", "testpass", timeout=2, auth="basic"
            )
            threads = [
                threading.Thread(target=client.get, args=("/cgi-bin/test",))
                for _ in range(3)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(mock.max_active, 1)


if __name__ == "__main__":
    unittest.main()
