import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cgi_config


LIVE = {
    "NTP.Enable": "true",
    "NTP.Address": "clock.isc.org",
    "NTP.Port": "123",
    "Network.eth0.IPAddress": "192.168.2.10",
    "NAS[0].Password": "old-secret",
    "NAS[0].UserName": "upload",
    "MotionDetect[0].Enable": "true",
    "MotionDetect[0].Level": "3",
}


class RevisionTests(unittest.TestCase):
    def test_canonical_is_sorted(self):
        self.assertEqual(
            cgi_config.canonical({"b": "2", "a": "1"}), "a=1\nb=2"
        )

    def test_revision_is_stable(self):
        first = cgi_config.revision({"a": "1", "b": "2"})
        second = cgi_config.revision({"b": "2", "a": "1"})
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, cgi_config.revision({"a": "2", "b": "2"}))


class DiffTests(unittest.TestCase):
    def test_valid_changes_are_normalized(self):
        changes = cgi_config.diff_changes(
            "NTP",
            LIVE,
            {"NTP.Enable": "off", "NTP.Address": " pool.ntp.org "},
        )
        self.assertEqual(
            changes, {"NTP.Enable": "false", "NTP.Address": "pool.ntp.org"}
        )

    def test_unchanged_and_blank_secret_are_omitted(self):
        changes = cgi_config.diff_changes(
            "NAS",
            LIVE,
            {"NAS[0].Password": "", "NAS[0].UserName": "upload"},
        )
        self.assertEqual(changes, {})

    def test_new_secret_is_kept(self):
        changes = cgi_config.diff_changes(
            "NAS", LIVE, {"NAS[0].Password": "new-secret"}
        )
        self.assertEqual(changes, {"NAS[0].Password": "new-secret"})

    def test_non_writable_field_is_rejected(self):
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.diff_changes(
                "MotionDetect", LIVE, {"MotionDetect[0].Region[0]": "0"}
            )

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.diff_changes("NTP", LIVE, {"NTP.Unknown": "1"})

    def test_absent_field_is_rejected(self):
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.diff_changes("NTP", LIVE, {"NTP.TimeZone": "28"})

    def test_bad_value_is_rejected(self):
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.diff_changes(
                "Network", LIVE, {"Network.eth0.IPAddress": "bad"}
            )

    def test_unknown_section_is_rejected(self):
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.diff_changes("System", LIVE, {})

    def test_apply_and_params(self):
        merged = cgi_config.apply_changes(
            "NTP", LIVE, {"NTP.Port": "124"}
        )
        self.assertEqual(merged["NTP.Address"], "clock.isc.org")
        self.assertEqual(merged["NTP.Port"], "124")
        params = cgi_config.params_for_cgi({"NTP.Port": "124"})
        self.assertEqual(
            params, {"action": "setConfig", "NTP.Port": "124"}
        )


class RpcTableTests(unittest.TestCase):
    def test_sets_nested_dict_value(self):
        table = {"eth0": {"IPAddress": "192.168.2.10", "MTU": 1500}}
        cgi_config.set_table_value(
            table, "Network", "Network.eth0.IPAddress", "192.168.2.20"
        )
        self.assertEqual(table["eth0"]["IPAddress"], "192.168.2.20")
        self.assertEqual(table["eth0"]["MTU"], 1500)

    def test_sets_list_value_with_rpc_types(self):
        table = [
            {
                "Enable": True,
                "Level": 3,
                "MotionDetectWindow": [{"Sensitive": 60}],
            }
        ]
        cgi_config.set_table_value(
            table, "MotionDetect", "MotionDetect[0].Enable", "false"
        )
        cgi_config.set_table_value(
            table, "MotionDetect", "MotionDetect[0].Level", "5"
        )
        self.assertIs(table[0]["Enable"], False)
        self.assertEqual(table[0]["Level"], 5)
        self.assertEqual(table[0]["MotionDetectWindow"][0]["Sensitive"], 60)

    def test_sets_nas_list_value(self):
        table = [{"Address": "192.168.2.8", "Port": 21}]
        cgi_config.set_table_value(table, "NAS", "NAS[0].Port", "2121")
        self.assertEqual(table[0]["Port"], 2121)

    def test_missing_path_is_rejected(self):
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.set_table_value(
                {"eth0": {}}, "Network", "Network.eth2.IPAddress", "192.168.2.20"
            )
        with self.assertRaises(cgi_config.ConfigError):
            cgi_config.set_table_value(
                [{"Port": 21}], "NAS", "NAS[2].Port", "21"
            )


if __name__ == "__main__":
    unittest.main()
