import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import console
import test_configfile


class LoggingTestCase(unittest.TestCase):
    def tearDown(self):
        logger = logging.getLogger("amcrest")
        for handler in logger.handlers[:]:
            handler.close()
        logger.handlers[:] = []
        logger.setLevel(logging.NOTSET)


class DefaultLogPathTests(LoggingTestCase):
    def test_uses_name(self):
        path = console.default_log_path(
            Path("/tmp/state"), "cam-01", "192.168.2.121"
        )
        self.assertEqual(path, Path("/tmp/state/log-cam-01.log"))

    def test_falls_back_to_host(self):
        path = console.default_log_path(Path("/tmp/state"), None, "192.168.2.121")
        self.assertEqual(path, Path("/tmp/state/log-192.168.2.121.log"))

    def test_slugifies_name(self):
        path = console.default_log_path(Path("/tmp/state"), "Cam 01!", "10.0.0.1")
        self.assertEqual(path.name, "log-cam-01.log")


class SetupLoggingTests(LoggingTestCase):
    def test_creates_parent_and_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "log-cam-01.log"
            console.setup_logging("INFO", path)
            logging.getLogger("amcrest").info("hello")
            self.assertTrue(path.exists())
            self.assertIn("hello", path.read_text(encoding="utf-8"))

    def test_file_mode_is_0600(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log-cam-01.log"
            console.setup_logging("INFO", path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class MainLogDestinationTests(LoggingTestCase):
    def run_main(self, argv):
        fake_server = mock.MagicMock()
        fake_server.server_address = ("127.0.0.1", 8765)
        with mock.patch("console.check_reachable", return_value=None), mock.patch(
            "console.ConsoleServer", return_value=fake_server
        ):
            return console.main(argv)

    def test_default_path_uses_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = self.run_main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--name",
                    "cam-01",
                    "--state-dir",
                    tmp,
                    "--no-browser",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((Path(tmp) / "log-cam-01.log").exists())

    def test_default_path_uses_ip_without_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = self.run_main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--state-dir",
                    tmp,
                    "--no-browser",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((Path(tmp) / "log-192.168.2.121.log").exists())

    def test_log_file_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp) / "custom.log"
            rc = self.run_main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--name",
                    "cam-01",
                    "--state-dir",
                    tmp,
                    "--log-file",
                    str(custom),
                    "--no-browser",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(custom.exists())
            self.assertFalse((Path(tmp) / "log-cam-01.log").exists())

    def test_state_file_does_not_move_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = self.run_main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--name",
                    "cam-01",
                    "--state-dir",
                    tmp,
                    "--state-file",
                    str(Path(tmp) / "explicit.json"),
                    "--no-browser",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((Path(tmp) / "log-cam-01.log").exists())

    def test_bind_and_allow_host_are_forwarded(self):
        fake_server = mock.MagicMock()
        fake_server.server_address = ("127.0.0.1", 8765)
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "console.check_reachable", return_value=None
        ), mock.patch(
            "console.ConsoleServer", return_value=fake_server
        ) as constructor:
            rc = console.main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--state-dir",
                    tmp,
                    "--bind",
                    "127.0.0.1",
                    "--allow-host",
                    "cam.local:8765",
                    "--no-browser",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(constructor.call_args[0][0], ("127.0.0.1", 8765))
        self.assertEqual(
            constructor.call_args[1]["allow_hosts"], ["cam.local:8765"]
        )

    def test_backup_dir_is_forwarded(self):
        fake_server = mock.MagicMock()
        fake_server.server_address = ("127.0.0.1", 8765)
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "console.check_reachable", return_value=None
        ), mock.patch(
            "console.ConsoleServer", return_value=fake_server
        ) as constructor:
            backup_dir = Path(tmp) / "backups"
            rc = console.main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--state-dir",
                    tmp,
                    "--backup-dir",
                    str(backup_dir),
                    "--no-browser",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(constructor.call_args[1]["backup_dir"], backup_dir)


class ModelOptionTests(LoggingTestCase):
    def run_with_model(self, model_args):
        fake_server = mock.MagicMock()
        fake_server.server_address = ("127.0.0.1", 8765)
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "console.check_reachable", return_value=None
        ), mock.patch(
            "console.ConsoleServer", return_value=fake_server
        ) as constructor:
            rc = console.main(
                [
                    "--ip",
                    "192.168.2.121",
                    "--state-dir",
                    tmp,
                    "--no-browser",
                ] + model_args
            )
        self.assertEqual(rc, 0)
        return constructor.call_args[0][1]["request_delay"]

    def test_unknown_model_uses_safe_delay(self):
        self.assertEqual(self.run_with_model([]), 1.0)

    def test_supplied_non_ip2m_model_uses_zero_delay(self):
        self.assertEqual(
            self.run_with_model(["--model", "amcrest-ip3m-943"]), 0.0
        )

    def test_supplied_ip2m_model_uses_safe_delay(self):
        self.assertEqual(
            self.run_with_model(["--model", "amcrest-ip2m-842"]), 1.0
        )


class BatchModeTests(LoggingTestCase):
    """--noui --config {read,write}: no server, no browser, one shot."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_dir = Path(self.tmp.name) / "state"
        self.backup_dir = Path(self.tmp.name) / "backups"
        self.client = test_configfile.FakeClient()

    def base_argv(self, extra):
        return [
            "--ip",
            "192.168.2.10",
            "--name",
            "cam-test",
            "--state-dir",
            str(self.state_dir),
            "--backup-dir",
            str(self.backup_dir),
        ] + extra

    def run_console(self, extra, client=None):
        client = client or self.client
        with mock.patch("console.check_reachable", return_value=None), mock.patch(
            "console.CameraClient", return_value=client
        ), mock.patch(
            "credentials.resolve_credentials",
            return_value=("cam-test", "admin", "pw", ""),
        ), mock.patch(
            "console.ConsoleServer"
        ) as server_constructor:
            rc = console.main(self.base_argv(extra))
        return rc, server_constructor

    def write_document(self, sections=None, name="config-cam-test.json"):
        path = self.state_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = test_configfile.document(sections)
        path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
        return path

    def test_noui_requires_config(self):
        with self.assertRaises(SystemExit) as caught:
            console.main(self.base_argv(["--noui"]))
        self.assertEqual(caught.exception.code, 2)

    def test_config_requires_noui(self):
        with self.assertRaises(SystemExit) as caught:
            console.main(self.base_argv(["--config", "read", "--no-browser"]))
        self.assertEqual(caught.exception.code, 2)

    def test_noui_rejects_server_options(self):
        for extra in (["--port", "9000"], ["--bind", "127.0.0.1"]):
            with self.assertRaises(SystemExit) as caught:
                console.main(
                    self.base_argv(["--noui", "--config", "read"] + extra)
                )
            self.assertEqual(caught.exception.code, 2)

    def test_noui_rejects_no_browser_and_allow_host(self):
        for extra in (["--no-browser"], ["--allow-host", "cam.local"]):
            with self.assertRaises(SystemExit) as caught:
                console.main(
                    self.base_argv(["--noui", "--config", "write"] + extra)
                )
            self.assertEqual(caught.exception.code, 2)

    def test_dry_run_requires_write(self):
        with self.assertRaises(SystemExit) as caught:
            console.main(
                self.base_argv(["--noui", "--config", "read", "--dry-run"])
            )
        self.assertEqual(caught.exception.code, 2)

    def test_include_secrets_requires_read(self):
        with self.assertRaises(SystemExit) as caught:
            console.main(
                self.base_argv(
                    ["--noui", "--config", "write", "--include-secrets"]
                )
            )
        self.assertEqual(caught.exception.code, 2)

    def test_read_writes_the_default_config_file_and_no_server(self):
        rc, server_constructor = self.run_console(["--noui", "--config", "read"])
        self.assertEqual(rc, 0)
        server_constructor.assert_not_called()
        path = self.state_dir / "config-cam-test.json"
        self.assertTrue(path.exists())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["kind"], "amcrest-console-backup")
        self.assertTrue(doc["complete"])
        self.assertEqual(
            sorted(doc["sections"]), sorted(test_configfile.base_sections())
        )

    def test_read_redacts_secrets_by_default(self):
        self.run_console(["--noui", "--config", "read"])
        doc = json.loads(
            (self.state_dir / "config-cam-test.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            doc["sections"]["NAS"]["values"]["NAS[0].Password"], "<redacted>"
        )

    def test_read_include_secrets_stores_real_values(self):
        self.run_console(["--noui", "--config", "read", "--include-secrets"])
        doc = json.loads(
            (self.state_dir / "config-cam-test.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            doc["sections"]["NAS"]["values"]["NAS[0].Password"], "ftppass"
        )

    def test_read_updates_the_mirror(self):
        self.run_console(["--noui", "--config", "read"])
        mirror = json.loads(
            (self.state_dir / "cam-test.json").read_text(encoding="utf-8")
        )
        self.assertIn("MotionDetectConfig", mirror["configuration"])
        self.assertIn("Network", mirror["configuration"])

    def test_read_uses_an_explicit_config_file(self):
        target = Path(self.tmp.name) / "elsewhere.json"
        self.run_console(
            ["--noui", "--config", "read", "--config-file", str(target)]
        )
        self.assertTrue(target.exists())

    def test_write_missing_file_exits_six(self):
        rc, _server = self.run_console(
            [
                "--noui",
                "--config",
                "write",
                "--config-file",
                str(self.state_dir / "nope.json"),
            ]
        )
        self.assertEqual(rc, 6)
        self.assertEqual(self.client.writes, [])

    def test_write_aborts_when_network_differs(self):
        sections = test_configfile.base_sections()
        sections["Network"]["Network.eth0.IPAddress"] = "192.168.2.99"
        path = self.write_document(sections)
        rc, _server = self.run_console(
            ["--noui", "--config", "write", "--config-file", str(path)]
        )
        self.assertEqual(rc, 7)
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.motion_writes, [])
        self.assertFalse(
            self.backup_dir.exists() and list(self.backup_dir.glob("*.json"))
        )

    def test_write_aborts_when_the_file_has_no_network_section(self):
        doc = test_configfile.document()
        del doc["sections"]["Network"]
        path = self.state_dir / "config-cam-test.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
        rc, _server = self.run_console(["--noui", "--config", "write"])
        self.assertEqual(rc, 6)
        self.assertEqual(self.client.writes, [])

    def test_dry_run_reports_without_writing(self):
        sections = test_configfile.base_sections()
        sections["NTP"]["NTP.Address"] = "time.example"
        path = self.write_document(sections)
        rc, _server = self.run_console(
            ["--noui", "--config", "write", "--dry-run", "--config-file", str(path)]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.motion_writes, [])
        self.assertFalse(self.backup_dir.exists())

    def test_write_applies_changes_and_backs_up(self):
        sections = test_configfile.base_sections()
        sections["NTP"]["NTP.Address"] = "time.example"
        sections["MotionDetect"]["MotionDetect[0].Level"] = "5"
        path = self.write_document(sections)
        rc, _server = self.run_console(
            ["--noui", "--config", "write", "--config-file", str(path)]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.client.writes, [("NTP", {"NTP.Address": "time.example"})])
        self.assertEqual(
            self.client.motion_writes, [{"MotionDetect[0].Level": "5"}]
        )
        backups = list(self.backup_dir.glob("cam-test-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            self.client.sections["NTP"]["NTP.Address"], "time.example"
        )
        mirror = json.loads(
            (self.state_dir / "cam-test.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            mirror["configuration"]["NTP"]["values"]["NTP.Address"],
            "time.example",
        )

    def test_write_is_a_noop_when_the_camera_matches(self):
        path = self.write_document()
        rc, _server = self.run_console(
            ["--noui", "--config", "write", "--config-file", str(path)]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.motion_writes, [])

    def test_write_reports_failure_when_the_camera_rejects(self):
        sections = test_configfile.base_sections()
        sections["NTP"]["NTP.Address"] = "time.example"
        path = self.write_document(sections)
        self.client.reject_writes.add("NTP")
        rc, _server = self.run_console(
            ["--noui", "--config", "write", "--config-file", str(path)]
        )
        self.assertEqual(rc, 8)


class ConsoleUrlTests(LoggingTestCase):
    def test_specific_bind(self):
        self.assertEqual(
            console.console_urls("127.0.0.1", 8765), ["http://127.0.0.1:8765/"]
        )

    def test_lan_bind_lists_addresses_and_loopback(self):
        with mock.patch(
            "console.local_ip_addresses",
            return_value=["127.0.1.1", "192.168.2.5"],
        ):
            urls = console.console_urls("0.0.0.0", 8765)
        self.assertEqual(
            urls,
            ["http://192.168.2.5:8765/", "http://127.0.0.1:8765/"],
        )


if __name__ == "__main__":
    unittest.main()
