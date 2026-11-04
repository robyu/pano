import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import state


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()


class PathTests(StateTestCase):
    def test_slugify(self):
        self.assertEqual(state.slugify("cam-01"), "cam-01")
        self.assertEqual(state.slugify("Cam 01 / Porch"), "cam-01-porch")
        self.assertEqual(state.slugify("192.168.2.121"), "192.168.2.121")
        self.assertEqual(state.slugify("::1"), "1")
        self.assertEqual(state.slugify(""), "camera")

    def test_one_file_per_camera(self):
        first = state.mirror_path(self.dir, "cam-01", "192.168.2.121")
        second = state.mirror_path(self.dir, "cam-02", "192.168.2.122")
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, self.dir)
        self.assertEqual(first.name, "cam-01.json")

    def test_falls_back_to_host(self):
        path = state.mirror_path(self.dir, None, "192.168.2.121")
        self.assertEqual(path.name, "192.168.2.121.json")


class SaveLoadTests(StateTestCase):
    def sample(self, password="secret"):
        return state.new_mirror(
            {"name": "cam-01", "host": "192.168.2.121", "model": "IP2M-842"},
            {
                "MotionDetect": {"legacy": {"revision": "abc"}},
                "NAS": {"Password": password, "UserName": "ftp"},
            },
            updated="2026-11-03T12:00:00-08:00",
        )

    def test_save_load_round_trip(self):
        path = state.mirror_path(self.dir, "cam-01", "192.168.2.121")
        state.save(path, self.sample())
        data = state.load(path)
        self.assertEqual(data["schema_version"], state.SCHEMA_VERSION)
        self.assertEqual(data["camera"]["name"], "cam-01")
        self.assertEqual(
            data["configuration"]["MotionDetect"]["legacy"]["revision"], "abc"
        )

    def test_file_mode_is_private(self):
        path = state.mirror_path(self.dir, "cam-01", "192.168.2.121")
        state.save(path, self.sample())
        mode = stat.S_IMODE(os.stat(str(path)).st_mode)
        self.assertEqual(mode, 0o600)

    def test_secrets_are_redacted(self):
        path = state.mirror_path(self.dir, "cam-01", "192.168.2.121")
        state.save(path, self.sample(password="hunter2"))
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("hunter2", text)
        data = json.loads(text)
        self.assertEqual(data["configuration"]["NAS"]["Password"], "<redacted>")

    def test_no_temp_files_left(self):
        path = state.mirror_path(self.dir, "cam-01", "192.168.2.121")
        state.save(path, self.sample())
        leftovers = [p.name for p in self.dir.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_missing_returns_none(self):
        self.assertIsNone(state.load(self.dir / "missing.json"))

    def test_corrupt_file_is_quarantined(self):
        path = self.dir / "cam-01.json"
        path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(state.load(path))
        self.assertFalse(path.exists())
        bad = list(self.dir.glob("cam-01.json.bad-*"))
        self.assertEqual(len(bad), 1)

    def test_wrong_schema_is_quarantined(self):
        path = self.dir / "cam-01.json"
        path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
        self.assertIsNone(state.load(path))
        self.assertFalse(path.exists())

    def test_save_creates_lock_file(self):
        path = state.mirror_path(self.dir, "cam-01", "192.168.2.121")
        state.save(path, self.sample())
        self.assertTrue((self.dir / "cam-01.json.lock").exists())


if __name__ == "__main__":
    unittest.main()
