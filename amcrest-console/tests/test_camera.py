import base64
import hashlib
import json
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock
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


class ModelDetectionTests(unittest.TestCase):
    def test_detect_model_queries_camera_and_caches(self):
        with MockCamera() as mock:
            client = camera.CameraClient(
                "127.0.0.1", mock.port, "admin", "testpass", timeout=2, auth="basic"
            )
            client.verify_credentials()
            model = client.detect_model()
            identity = client.identity()
        self.assertEqual(model, "IP2M-842")
        self.assertEqual(client.model, "IP2M-842")
        self.assertEqual(identity["magic"]["getDeviceType"]["type"], "IP2M-842")
        self.assertNotIn("getSoftwareVersion", identity["magic"])
        device_requests = [
            path for path in mock.requests if "getDeviceType" in path
        ]
        machine_requests = [
            path for path in mock.requests if "getMachineName" in path
        ]
        self.assertEqual(len(device_requests), 1)
        self.assertEqual(len(machine_requests), 1)

    def test_supplied_model_is_not_queried(self):
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
            model = client.detect_model()
        self.assertEqual(model, "amcrest-ip2m-842")
        self.assertFalse(
            any("getDeviceType" in path for path in mock.requests)
        )

    def test_identity_detects_model_without_argument(self):
        with MockCamera() as mock:
            client = camera.CameraClient(
                "127.0.0.1", mock.port, "admin", "testpass", timeout=2, auth="basic"
            )
            identity = client.identity()
        self.assertEqual(identity["magic"]["getDeviceType"]["type"], "IP2M-842")
        self.assertEqual(client.model, "IP2M-842")
        self.assertNotIn("getSoftwareVersion", identity["magic"])


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


class ProductVersionFormatTests(unittest.TestCase):
    """Version assembly, checked against the values the cameras report."""

    IP2M = {
        "MajorVersion": 2,
        "MinorVersion": 212,
        "OEMVersion": 0,
        "Revision": 2,
        "BuildDate": "2016-08-11",
        "WebVersion": "3.2.1.273284",
        "TypeVersion": "R",
        "VendorAbbr": "00",
    }
    IP3M = {
        "MajorVersion": 2,
        "MinorVersion": 400,
        "OEMVersion": 2,
        "Revision": 15,
        "BuildDate": "2017-07-31",
        "WebVersion": "3.2.1.422026",
        "TypeVersion": "R",
        "VendorAbbr": "AC",
    }

    def test_ip2m_842_version(self):
        self.assertEqual(
            camera.format_product_version(self.IP2M), "2.212.0000.2.R"
        )

    def test_ip3m_943b_version(self):
        self.assertEqual(
            camera.format_product_version(self.IP3M), "2.400.AC02.15.R"
        )

    def test_build_date_is_not_part_of_the_version(self):
        self.assertNotIn(
            "2016-08-11", camera.format_product_version(self.IP2M)
        )

    def test_zero_pads_short_fields(self):
        values = dict(
            self.IP2M,
            MajorVersion=1,
            MinorVersion=7,
            VendorAbbr="AB",
            OEMVersion=5,
            Revision=1,
        )
        self.assertEqual(camera.format_product_version(values), "1.007.AB05.1.R")

    def test_missing_field_returns_none(self):
        reported_separately = ("BuildDate", "WebVersion")
        for field in camera.PRODUCT_DEFINITION_FIELDS:
            if field in reported_separately:
                continue
            values = dict(self.IP2M)
            del values[field]
            self.assertIsNone(camera.format_product_version(values), field)

    def test_missing_build_date_still_reports_a_version(self):
        values = dict(self.IP2M)
        del values["BuildDate"]
        self.assertEqual(camera.format_product_version(values), "2.212.0000.2.R")

    def test_empty_definitions_return_none(self):
        self.assertIsNone(camera.format_product_version({}))

    def test_non_numeric_values_are_not_padded(self):
        values = dict(self.IP2M, MinorVersion="2X")
        self.assertEqual(
            camera.format_product_version(values), "2.2X.0000.2.R"
        )


class ProductVersionClientTests(unittest.TestCase):
    """rpc_product_version(): one multicall, never getSoftwareVersion."""

    def client(self):
        return camera.CameraClient(
            "127.0.0.1",
            80,
            "admin",
            "pw",
            timeout=2,
            auth="basic",
            model="amcrest-ip2m-842",
        )

    def envelope(self, values):
        entries = []
        for index, name in enumerate(camera.PRODUCT_DEFINITION_FIELDS):
            entries.append(
                {
                    "id": 100 + index,
                    "result": True,
                    "params": {"name": name, "definition": values[index]},
                }
            )
        entries.append(
            {
                "id": 199,
                "result": True,
                "params": {"sn": "AMC002A34HATK2G7HH", "no": "AMC002A34HATK2G7HH"},
            }
        )
        return {"id": 1, "result": True, "session": "1", "params": entries}

    def test_reports_version_build_web_and_serial(self):
        client = self.client()
        values = [2, 212, 0, 2, "2016-08-11", "3.2.1.273284", "R", "00"]
        with mock.patch.object(client, "rpc_login", return_value="sess"), mock.patch.object(
            client, "_rpc_post", return_value=self.envelope(values)
        ) as post:
            version = client.rpc_product_version()
        self.assertEqual(version["software"], "2.212.0000.2.R")
        self.assertEqual(version["build"], "2016-08-11")
        self.assertEqual(version["web"], "3.2.1.273284")
        self.assertEqual(version["serial"], "AMC002A34HATK2G7HH")
        body = post.call_args[0][1]
        self.assertEqual(body["method"], "system.multicall")
        self.assertEqual(len(body["params"]), 9)
        for index, name in enumerate(camera.PRODUCT_DEFINITION_FIELDS):
            self.assertEqual(
                body["params"][index],
                {
                    "method": "magicBox.getProductDefinition",
                    "params": {"name": name},
                    "id": 100 + index,
                },
            )
        self.assertNotIn("getSoftwareVersion", json.dumps(post.call_args[0][1]))

    def test_batches_into_one_request(self):
        client = self.client()
        values = [2, 212, 0, 2, "2016-08-11", "3.2.1.273284", "R", "00"]
        with mock.patch.object(client, "rpc_login", return_value="sess"), mock.patch.object(
            client, "_rpc_post", return_value=self.envelope(values)
        ) as post:
            client.rpc_product_version()
        self.assertEqual(post.call_count, 1)

    def test_falls_back_to_single_calls(self):
        client = self.client()
        values = [2, 212, 0, 2, "2016-08-11", "3.2.1.273284", "R", "00"]
        envelopes = self.envelope(values)["params"]
        seen = []

        def fake_post(path, payload):
            seen.append(payload["method"])
            if payload.get("method") == "system.multicall":
                raise camera.CameraError("Method not allowed")
            for entry in envelopes:
                if entry["id"] == payload.get("id"):
                    return entry
            raise CameraError("no such id")

        with mock.patch.object(client, "rpc_login", return_value="sess"), mock.patch.object(
            client, "_rpc_post", side_effect=fake_post
        ):
            version = client.rpc_product_version()
        self.assertEqual(version["software"], "2.212.0000.2.R")
        self.assertEqual(seen.count("system.multicall"), 1)
        self.assertEqual(seen.count("magicBox.getProductDefinition"), 8)
        self.assertEqual(seen.count("magicBox.getSerialNo"), 1)

    def test_rpc_request_tolerates_list_params(self):
        client = self.client()
        payload = {"method": "system.multicall", "params": [], "id": 1, "session": "s"}
        with mock.patch.object(client, "_rpc_post", return_value=self.envelope(
            [2, 212, 0, 2, "2016-08-11", "3.2.1.273284", "R", "00"]
        )):
            result = client._rpc_request("/RPC2", payload)
        self.assertTrue(result["result"])


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


class SectionConfigTests(unittest.TestCase):
    def client(self):
        return camera.CameraClient(
            "127.0.0.1", 80, "admin", "testpass", timeout=2, auth="basic"
        )

    def test_get_section_returns_revision(self):
        client = self.client()
        values = {"NTP.Enable": "true", "NTP.Address": "clock.isc.org"}
        with mock.patch.object(
            client, "get_config", return_value=(values, [], "raw")
        ):
            section = client.get_section("NTP")
        self.assertEqual(section["name"], "NTP")
        self.assertEqual(section["values"], values)
        self.assertEqual(section["raw"], "raw")
        self.assertEqual(len(section["revision"]), 64)

    def test_set_section_changes_uses_cgi_when_accepted(self):
        client = self.client()
        with mock.patch.object(
            client, "cgi_text", return_value="OK"
        ) as cgi_text:
            with mock.patch.object(client, "rpc_get_config") as rpc_get:
                result = client.set_section_changes(
                    "NTP", {"NTP.Address": "pool.ntp.org"}
                )
        self.assertEqual(result, "OK")
        params = cgi_text.call_args[0][1]
        self.assertEqual(params["action"], "setConfig")
        self.assertEqual(params["NTP.Address"], "pool.ntp.org")
        rpc_get.assert_not_called()

    def test_set_section_changes_falls_back_to_rpc2(self):
        client = self.client()
        table = {"eth0": {"IPAddress": "192.168.2.10", "MTU": 1500}}
        with mock.patch.object(client, "cgi_text", return_value="Error"):
            with mock.patch.object(
                client, "rpc_get_config", return_value=table
            ):
                with mock.patch.object(client, "rpc_set_config") as rpc_set:
                    result = client.set_section_changes(
                        "Network", {"Network.eth0.IPAddress": "192.168.2.20"}
                    )
        self.assertEqual(result, "OK (RPC2)")
        self.assertEqual(table["eth0"]["IPAddress"], "192.168.2.20")
        self.assertEqual(table["eth0"]["MTU"], 1500)
        rpc_set.assert_called_once_with("Network", table)

    def test_motion_settings_send_all_rows(self):
        client = self.client()
        values = {"MotionDetect[0].Enable": "true", "MotionDetect[0].Level": "3"}
        for row in range(18):
            values["MotionDetect[0].Region[{}]".format(row)] = str(row)
        with mock.patch.object(
            client, "get_config", return_value=(values, [], "raw")
        ):
            with mock.patch.object(
                client, "cgi_text", return_value="OK"
            ) as cgi_text:
                result = client.write_motion_settings(
                    {"MotionDetect[0].Level": "5"}
                )
        self.assertEqual(result, "OK")
        params = cgi_text.call_args[0][1]
        self.assertEqual(params["MotionDetect[0].Level"], "5")
        region_keys = [
            key for key in params
            if key.startswith("MotionDetect[0].Region[")
        ]
        self.assertEqual(len(region_keys), 18)

    def test_motion_settings_refuse_incomplete_rows(self):
        client = self.client()
        values = {"MotionDetect[0].Enable": "true"}
        for row in range(12):
            values["MotionDetect[0].Region[{}]".format(row)] = str(row)
        with mock.patch.object(
            client, "get_config", return_value=(values, [], "raw")
        ):
            with self.assertRaises(camera.CameraError):
                client.write_motion_settings(
                    {"MotionDetect[0].Level": "5"}
                )

    def test_motion_settings_fallback_preserves_regions(self):
        client = self.client()
        values = {"MotionDetect[0].Enable": "true", "MotionDetect[0].Level": "3"}
        for row in range(18):
            values["MotionDetect[0].Region[{}]".format(row)] = str(row)
        table = [
            {
                "Enable": True,
                "Level": 3,
                "Region": list(range(18)),
                "MotionDetectWindow": [{"Sensitive": 60}],
            }
        ]
        with mock.patch.object(
            client, "get_config", return_value=(values, [], "raw")
        ):
            with mock.patch.object(client, "cgi_text", return_value="Error"):
                with mock.patch.object(
                    client, "rpc_get_config", return_value=table
                ):
                    with mock.patch.object(
                        client, "rpc_set_config"
                    ) as rpc_set:
                        result = client.write_motion_settings(
                            {"MotionDetect[0].Level": "5"}
                        )
        self.assertEqual(result, "OK (RPC2)")
        self.assertEqual(table[0]["Level"], 5)
        self.assertEqual(table[0]["Region"], list(range(18)))
        self.assertEqual(table[0]["MotionDetectWindow"][0]["Sensitive"], 60)
        rpc_set.assert_called_once_with("MotionDetect", table)


if __name__ == "__main__":
    unittest.main()
