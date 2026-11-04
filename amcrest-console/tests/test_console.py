import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import console


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
                    "--camera-ip",
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
                    "--camera-ip",
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
                    "--camera-ip",
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
                    "--camera-ip",
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
                    "--camera-ip",
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
