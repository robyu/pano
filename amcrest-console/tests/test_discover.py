import base64
import hashlib
import json
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import discover


class ParseTests(unittest.TestCase):
    def test_parse_kv_strips_table_and_tracks_duplicates(self):
        values, duplicates = discover.parse_kv(
            "table.MotionDetect[0].Enable=true\n"
            "table.MotionDetect[0].Level=3\n"
            "garbage line\n"
            "table.MotionDetect[0].Level=4\n"
        )
        self.assertEqual(values["MotionDetect[0].Enable"], "true")
        self.assertEqual(values["MotionDetect[0].Level"], "4")
        self.assertEqual(duplicates, ["MotionDetect[0].Level"])

    def test_region_decode_lsb_is_leftmost(self):
        rows = discover.decode_region_rows([0, 1, 3, 0x3FFFFF] + [0] * 14)
        self.assertEqual(rows[0], [0] * discover.COLS)
        self.assertEqual(rows[1][0], 1)
        self.assertEqual(sum(rows[1]), 1)
        self.assertEqual(rows[2][:3], [1, 1, 0])
        self.assertEqual(rows[3], [1] * discover.COLS)

    def test_ascii_mask(self):
        rows = [[1] * discover.COLS, [0] * discover.COLS]
        text = discover.ascii_mask(rows)
        self.assertEqual(text.splitlines()[0], "#" * discover.COLS)
        self.assertEqual(text.splitlines()[1], "." * discover.COLS)

    def test_redaction(self):
        raw = (
            "table.FTP.Password=secret1\n"
            "live_url=rtsp://admin:secret2@192.168.2.1:80/x\n"
            "action=setConfig&Email.Password=secret3&x=1\n"
        )
        clean = discover.redact_text(raw)
        self.assertNotIn("secret1", clean)
        self.assertNotIn("secret2", clean)
        self.assertNotIn("secret3", clean)
        self.assertIn("<redacted>", clean)

    def test_sanitize_nested(self):
        value = {"Password": "x", "nested": [{"token": "y"}], "ok": "z"}
        clean = discover.sanitize(value)
        self.assertEqual(clean["Password"], "<redacted>")
        self.assertEqual(clean["nested"][0]["token"], "<redacted>")
        self.assertEqual(clean["ok"], "z")

    def test_parse_legacy_mask(self):
        config = {"MotionDetect[0].Enable": "true", "MotionDetect[0].Level": "3"}
        for row in range(discover.ROWS):
            config["MotionDetect[0].Region[{}]".format(row)] = "3"
        mask = discover.parse_mask(config)
        self.assertTrue(mask["legacy"])
        self.assertEqual(len(mask["legacy"]), discover.ROWS)
        self.assertEqual(mask["legacy"][0], 3)
        self.assertEqual(mask["windows"], [])

    def test_parse_window_mask(self):
        config = {"MotionDetect[0].Enable": "true"}
        for row in range(discover.ROWS):
            config[
                "MotionDetect[0].MotionDetectWindow[0].Region[{}]".format(row)
            ] = "1"
        config["MotionDetect[0].MotionDetectWindow[0].Id"] = "0"
        config["MotionDetect[0].MotionDetectWindow[0].Name"] = "Region0"
        mask = discover.parse_mask(config)
        self.assertIsNone(mask["legacy"])
        self.assertEqual(len(mask["windows"]), 1)
        self.assertEqual(mask["windows"][0]["regions"][0], 1)


class PanoConfigTests(unittest.TestCase):
    def test_loads_credentials_by_ip(self):
        payload = {
            "camera_list": [
                {
                    "name": "cam-03",
                    "live_url": "rtsp://admin:p%40ss@192.168.2.123:80/x",
                    "admin_url": "http://192.168.2.123",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pano.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            camera = discover.load_pano_camera(path, "192.168.2.123", None)
        self.assertEqual(camera["name"], "cam-03")
        self.assertEqual(camera["user"], "admin")
        self.assertEqual(camera["password"], "p@ss")

    def test_skips_at_prefixed_key(self):
        payload = {
            "@camera_list": [
                {
                    "name": "cam-03",
                    "live_url": "rtsp://admin:pass@192.168.2.123/x",
                    "admin_url": "http://192.168.2.123",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pano.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(discover.CameraError):
                discover.load_pano_camera(path, "192.168.2.123", None)

    def test_loads_model(self):
        payload = {
            "camera_list": [
                {
                    "name": "cam-03",
                    "model": "amcrest-ip2m-842",
                    "live_url": "rtsp://admin:pass@192.168.2.123/x",
                    "admin_url": "http://192.168.2.123",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pano.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            camera = discover.load_pano_camera(path, "192.168.2.123", None)
        self.assertEqual(camera["model"], "amcrest-ip2m-842")


class IdentityTests(unittest.TestCase):
    def test_skip_software_version_for_ip2m_model(self):
        self.assertTrue(
            discover.skip_software_version("amcrest-ip2m-842", "")
        )

    def test_skip_software_version_for_ip2m_device_type(self):
        self.assertTrue(discover.skip_software_version("", "IP2M-842"))

    def test_software_version_for_ip3m_model(self):
        self.assertFalse(
            discover.skip_software_version("amcrest-ip3m-943", "")
        )

    def test_software_version_for_ip3m_device_type(self):
        self.assertFalse(discover.skip_software_version("", "IP3M-943B"))

    def test_skip_software_version_when_type_unknown(self):
        self.assertTrue(discover.skip_software_version("", ""))


class AuthServer:
    def __init__(self, mode):
        self.mode = mode
        self.requests = []
        self.auth_headers = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                outer.requests.append(self.path)
                outer.auth_headers.append(self.headers.get("Authorization"))
                if outer.mode == "basic":
                    outer.handle_basic(self)
                else:
                    outer.handle_digest(self)

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

    def handle_basic(self, handler):
        expected = "Basic " + base64.b64encode(b"admin:testpass").decode()
        if handler.headers.get("Authorization") != expected:
            handler.send_response(401)
            handler.send_header("WWW-Authenticate", 'Basic realm="Device_CGI"')
            handler.end_headers()
            return
        handler.send_response(200)
        handler.end_headers()
        handler.wfile.write(b"table.test=ok\n")

    def handle_digest(self, handler):
        header = handler.headers.get("Authorization", "")
        if not header.startswith("Digest "):
            handler.send_response(401)
            handler.send_header(
                "WWW-Authenticate",
                'Digest realm="test", nonce="abc123", qop="auth", opaque="xyz"',
            )
            handler.end_headers()
            return
        params = dict(re.findall(r'(\w+)=("[^"]*"|[^,]+)', header[len("Digest "):]))
        params = {k: v.strip('"') for k, v in params.items()}
        ha1 = hashlib.md5(b"admin:test:testpass").hexdigest()
        ha2 = hashlib.md5(
            "{}:{}".format(handler.command, params.get("uri", "")).encode()
        ).hexdigest()
        expected = hashlib.md5(
            "{}:{}:{}:{}:{}:{}".format(
                ha1,
                params.get("nonce"),
                params.get("nc"),
                params.get("cnonce"),
                params.get("qop"),
                ha2,
            ).encode()
        ).hexdigest()
        if params.get("response") != expected:
            handler.send_response(401)
            handler.send_header(
                "WWW-Authenticate",
                'Digest realm="test", nonce="abc123", qop="auth", opaque="xyz"',
            )
            handler.end_headers()
            return
        handler.send_response(200)
        handler.end_headers()
        handler.wfile.write(b"table.test=ok\n")


class AuthTests(unittest.TestCase):
    def test_basic_auth_is_preemptive(self):
        with AuthServer("basic") as server:
            client = discover.CameraClient(
                "127.0.0.1",
                server.port,
                "admin",
                "testpass",
                timeout=2,
                auth="basic",
            )
            status, _headers, body = client.get("/cgi-bin/test")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"table.test=ok\n")
        self.assertEqual(len(server.requests), 1)
        self.assertTrue(server.auth_headers[0].startswith("Basic "))

    def test_auto_uses_preemptive_basic(self):
        with AuthServer("basic") as server:
            client = discover.CameraClient(
                "127.0.0.1", server.port, "admin", "testpass", timeout=2
            )
            status, _headers, body = client.get("/cgi-bin/test")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"table.test=ok\n")
        self.assertEqual(len(server.requests), 1)
        self.assertTrue(server.auth_headers[0].startswith("Basic "))
        self.assertEqual(client.auth_scheme, "basic")

    def test_digest_auth(self):
        with AuthServer("digest") as server:
            client = discover.CameraClient(
                "127.0.0.1",
                server.port,
                "admin",
                "testpass",
                timeout=2,
                auth="digest",
            )
            status, _headers, body = client.get("/cgi-bin/test?action=getConfig")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"table.test=ok\n")
        self.assertGreaterEqual(len(server.requests), 2)
        self.assertIsNone(server.auth_headers[0])

    def test_auto_falls_back_to_digest(self):
        with AuthServer("digest") as server:
            client = discover.CameraClient(
                "127.0.0.1", server.port, "admin", "testpass", timeout=2
            )
            status, _headers, body = client.get("/cgi-bin/test")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"table.test=ok\n")
        self.assertTrue(server.auth_headers[0].startswith("Basic "))
        self.assertEqual(client.auth_scheme, "digest")

    def test_model_ip2m_uses_basic(self):
        with AuthServer("basic") as server:
            client = discover.CameraClient(
                "127.0.0.1",
                server.port,
                "admin",
                "testpass",
                timeout=2,
                model="amcrest-ip2m-842",
            )
            status, _headers, _body = client.get("/cgi-bin/test")
        self.assertEqual(status, 200)
        self.assertEqual(len(server.requests), 1)
        self.assertTrue(server.auth_headers[0].startswith("Basic "))
        self.assertEqual(client.auth_scheme, "basic")

    def test_model_ip3m_uses_digest(self):
        with AuthServer("digest") as server:
            client = discover.CameraClient(
                "127.0.0.1",
                server.port,
                "admin",
                "testpass",
                timeout=2,
                model="amcrest-ip3m-943",
            )
            status, _headers, _body = client.get("/cgi-bin/test")
        self.assertEqual(status, 200)
        self.assertIsNone(server.auth_headers[0])
        self.assertEqual(client.auth_scheme, "digest")

    def test_connection_refused_mentions_lockout(self):
        server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        port = server.server_address[1]
        server.server_close()
        client = discover.CameraClient(
            "127.0.0.1", port, "admin", "testpass", timeout=2
        )
        with self.assertRaises(discover.CameraError) as context:
            client.get("/cgi-bin/test")
        self.assertIn("login lockout", str(context.exception))


class WriteTests(unittest.TestCase):
    def test_set_legacy_regions_writes_all_18_rows(self):
        with AuthServer("basic") as server:
            client = discover.CameraClient(
                "127.0.0.1", server.port, "admin", "testpass", timeout=2
            )
            client.set_legacy_regions([1] * discover.ROWS)
        query = parse_qs(urlparse(server.requests[-1]).query)
        region_keys = [key for key in query if key.startswith("MotionDetect[0].Region[")]
        self.assertEqual(len(region_keys), discover.ROWS)
        self.assertEqual(query["action"], ["setConfig"])


class JpegTests(unittest.TestCase):
    def test_minimal_jpeg_dimensions(self):
        data = bytearray(b"\xff\xd8")
        data += b"\xff\xc0\x00\x11\x08\x00\x48\x00\xb0\x03"
        data += b"\x00" * 9
        data += b"\xff\xd9"
        self.assertEqual(discover.jpeg_dimensions(bytes(data)), (176, 72))


if __name__ == "__main__":
    unittest.main()
