import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configfile
import schemas
import state
from camera import CameraError

REGION_ROWS = ["4194303"] * 18


def base_sections() -> dict:
    """Section values shaped like a real camera (see tests/test_server.py)."""
    motion = {
        "MotionDetect[0].Enable": "true",
        "MotionDetect[0].Level": "3",
    }
    for row, value in enumerate(REGION_ROWS):
        motion["MotionDetect[0].Region[{}]".format(row)] = value
    return {
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
        },
        "NAS": {
            "NAS[0].Address": "192.168.2.8",
            "NAS[0].Port": "21",
            "NAS[0].Protocol": "FTP",
            "NAS[0].Enable": "true",
            "NAS[0].Directory": "cam-test",
            "NAS[0].UserName": "upload",
            "NAS[0].Password": "ftppass",
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
        },
        "AutoMaintain": {
            "AutoMaintain.AutoRebootEnable": "true",
            "AutoMaintain.AutoRebootDay": "7",
            "AutoMaintain.AutoRebootHour": "7",
            "AutoMaintain.AutoRebootMinute": "20",
        },
        "MotionDetect": motion,
    }


class FakeClient:
    """Duck-typed stand-in for camera.CameraClient (no HTTP, no sockets)."""

    def __init__(self, sections=None):
        self.sections = copy.deepcopy(sections or base_sections())
        self.writes = []
        self.motion_writes = []
        self.failing_reads = set()
        self.reject_writes = set()
        self.ignore_writes = False
        self.disconnect_after_network_write = False

    def get_section(self, name):
        if name in self.failing_reads:
            raise CameraError("camera refused {}".format(name))
        values = dict(self.sections.get(name, {}))
        return {
            "name": name,
            "values": values,
            "duplicates": [],
            "raw": "",
            "revision": "rev",
        }

    def set_section_changes(self, name, changes):
        self.writes.append((name, dict(changes)))
        if name in self.reject_writes:
            return "Error: ErrorID=5, Invalid Request!"
        if self.ignore_writes:
            return "OK"
        if name == "Network" and self.disconnect_after_network_write:
            self.disconnect_after_network_write = False
            self.failing_reads.add("Network")
            self.sections["Network"].update(changes)
            return "OK"
        self.sections[name].update(changes)
        return "OK"

    def write_motion_settings(self, changes):
        self.motion_writes.append(dict(changes))
        self.sections["MotionDetect"].update(changes)
        return "OK"

    # helpers used by console.run_batch
    def verify_credentials(self):
        return {"MachineName": "cam-test"}

    def detect_model(self):
        return None

    def identity(self):
        return {"magic": {}, "errors": []}

    def rpc_product_version(self):
        return {
            "software": "2.212.0000.2.R",
            "build": "2016-08-11",
            "web": "3.2.1.273284",
            "serial": "AMC002A34HATK2G7HH",
            "definitions": {},
        }


def document(sections=None, **overrides):
    doc = state.new_backup(
        {"name": "cam-test", "host": "192.168.2.10", "port": 80},
        {
            name: configfile.section_payload(name, values)
            for name, values in (sections or base_sections()).items()
        },
    )
    doc.update(overrides)
    return doc


class SectionPayloadTests(unittest.TestCase):
    def test_redacts_secrets_by_default(self):
        payload = configfile.section_payload(
            "NAS", {"NAS[0].Password": "ftppass", "NAS[0].Address": "1.2.3.4"}
        )
        self.assertEqual(payload["values"]["NAS[0].Password"], "<redacted>")
        self.assertEqual(payload["values"]["NAS[0].Address"], "1.2.3.4")
        self.assertEqual(payload["redacted"], ["NAS[0].Password"])

    def test_include_secrets_keeps_values(self):
        payload = configfile.section_payload(
            "NAS",
            {"NAS[0].Password": "ftppass"},
            include_secrets=True,
        )
        self.assertEqual(payload["values"]["NAS[0].Password"], "ftppass")
        self.assertEqual(payload["redacted"], [])

    def test_configuration_key_for_motion(self):
        self.assertEqual(configfile.configuration_key("MotionDetect"), "MotionDetectConfig")
        self.assertEqual(configfile.configuration_key("Network"), "Network")


class ReadTests(unittest.TestCase):
    def test_read_sections_covers_every_allowlisted_section(self):
        client = FakeClient()
        sections, errors = configfile.read_sections(client)
        self.assertEqual(errors, [])
        self.assertEqual(sorted(sections), sorted(schemas.SECTIONS))

    def test_read_sections_records_errors(self):
        client = FakeClient()
        client.failing_reads.add("Encode")
        sections, errors = configfile.read_sections(client)
        self.assertNotIn("Encode", sections)
        self.assertEqual([item["section"] for item in errors], ["Encode"])

    def test_read_document_fills_from_mirror_but_reports_error(self):
        client = FakeClient()
        client.failing_reads.add("NTP")
        mirror = {
            "configuration": {
                "NTP": configfile.section_payload(
                    "NTP", {"NTP.Address": "old.example"}
                )
            }
        }
        doc, errors = configfile.read_document(
            client, {"name": "cam-test"}, mirror=mirror
        )
        self.assertFalse(doc["complete"])
        self.assertTrue(doc["stale"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            doc["sections"]["NTP"]["values"], {"NTP.Address": "old.example"}
        )

    def test_include_secrets_flows_into_the_document(self):
        client = FakeClient()
        doc, _errors = configfile.read_document(
            client, {"name": "cam-test"}, include_secrets=True
        )
        self.assertEqual(
            doc["sections"]["NAS"]["values"]["NAS[0].Password"], "ftppass"
        )


class BackupTests(unittest.TestCase):
    def test_write_backup_writes_a_complete_document(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp:
            path, doc = configfile.write_backup(
                client,
                {"name": "cam-test", "host": "192.168.2.10", "port": 80},
                Path(tmp),
                "cam-test",
                "192.168.2.10",
            )
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(doc["complete"])

    def test_write_backup_fails_when_a_section_cannot_be_read(self):
        client = FakeClient()
        client.failing_reads.add("NTP")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CameraError):
                configfile.write_backup(
                    client, {"name": "cam-test"}, Path(tmp), "cam-test", "1.2.3.4"
                )


class LoadDocumentTests(unittest.TestCase):
    def write(self, body, name="config.json"):
        directory = tempfile.mkdtemp()
        path = Path(directory) / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_missing_file(self):
        with self.assertRaises(configfile.ConfigFileError):
            configfile.load_document(Path("/nonexistent/config-x.json"))

    def test_invalid_json(self):
        with self.assertRaises(configfile.ConfigFileError):
            configfile.load_document(self.write("{not json"))

    def test_wrong_kind(self):
        path = self.write(json.dumps({"kind": "other", "schema_version": 1}))
        with self.assertRaises(configfile.ConfigFileError):
            configfile.load_document(path)

    def test_unsupported_schema(self):
        path = self.write(
            json.dumps({"kind": state.BACKUP_KIND, "schema_version": 99})
        )
        with self.assertRaises(configfile.ConfigFileError):
            configfile.load_document(path)

    def test_missing_sections(self):
        path = self.write(
            json.dumps({"kind": state.BACKUP_KIND, "schema_version": 1})
        )
        with self.assertRaises(configfile.ConfigFileError):
            configfile.load_document(path)

    def test_valid_document(self):
        doc = document()
        path = self.write(json.dumps(doc))
        self.assertEqual(
            configfile.load_document(path)["sections"].keys(),
            doc["sections"].keys(),
        )


class NetworkGuardTests(unittest.TestCase):
    def setUp(self):
        self.live = dict(base_sections()["Network"])

    def test_identical_networks_have_no_mismatches(self):
        self.assertEqual(
            configfile.network_mismatches(self.live, dict(self.live)), {}
        )

    def test_changed_address_is_reported(self):
        target = dict(self.live)
        target["Network.eth0.IPAddress"] = "192.168.2.99"
        mismatches = configfile.network_mismatches(self.live, target)
        self.assertEqual(list(mismatches), ["Network.eth0.IPAddress"])
        self.assertEqual(
            mismatches["Network.eth0.IPAddress"],
            {"camera": "192.168.2.10", "file": "192.168.2.99"},
        )

    def test_key_present_on_one_side_only(self):
        target = dict(self.live)
        del target["Network.eth0.DefaultGateway"]
        target["Network.eth1.IPAddress"] = "10.0.0.5"
        mismatches = configfile.network_mismatches(self.live, target)
        self.assertEqual(
            sorted(mismatches),
            ["Network.eth0.DefaultGateway", "Network.eth1.IPAddress"],
        )
        self.assertIsNone(mismatches["Network.eth0.DefaultGateway"]["file"])
        self.assertIsNone(mismatches["Network.eth1.IPAddress"]["camera"])

    def test_secret_typed_network_keys_are_redacted(self):
        # No current Network field is secret-typed; force one to cover the branch.
        live = dict(self.live)
        live["Network.Password"] = "one"
        target = dict(live)
        target["Network.Password"] = "two"
        with mock.patch(
            "configfile.schemas.field_spec", return_value={"secret": True}
        ):
            mismatches = configfile.network_mismatches(live, target)
        self.assertEqual(
            mismatches["Network.Password"],
            {"camera": "<redacted>", "file": "<redacted>"},
        )

    def test_format_mismatches_lists_keys(self):
        target = dict(self.live)
        target["Network.Hostname"] = "other"
        text = configfile.format_mismatches(
            configfile.network_mismatches(self.live, target)
        )
        self.assertIn("Network.Hostname", text)
        self.assertIn("other", text)


class PlanTests(unittest.TestCase):
    def test_skips_general_and_network(self):
        client = FakeClient()
        plans, errors = configfile.plan_writes(client, document())
        self.assertEqual(errors, [])
        self.assertEqual([plan["name"] for plan in plans], ["NAS", "NTP", "Encode", "AutoMaintain", "MotionDetect"])

    def test_no_changes_when_file_matches_camera(self):
        client = FakeClient()
        plans, _errors = configfile.plan_writes(client, document())
        self.assertTrue(all(not plan["changes"] for plan in plans))

    def test_changes_are_normalized_and_non_writable_keys_dropped(self):
        client = FakeClient()
        sections = base_sections()
        sections["NTP"]["NTP.Address"] = "time.example"
        sections["NTP"]["NTP.Enable"] = False
        sections["MotionDetect"]["MotionDetect[0].Level"] = "5"
        sections["MotionDetect"]["MotionDetect[0].Region[0]"] = "0"
        doc = document(sections)
        # section_payload sanitizes; build the doc from raw values instead
        doc["sections"]["NTP"]["values"] = sections["NTP"]
        doc["sections"]["MotionDetect"]["values"] = sections["MotionDetect"]
        plans, errors = configfile.plan_writes(client, doc)
        self.assertEqual(errors, [])
        by_name = {plan["name"]: plan["changes"] for plan in plans}
        self.assertEqual(by_name["NTP"]["NTP.Address"], "time.example")
        self.assertEqual(by_name["NTP"]["NTP.Enable"], "false")
        self.assertEqual(by_name["MotionDetect"], {"MotionDetect[0].Level": "5"})

    def test_duplicate_keys_are_refused(self):
        client = FakeClient()

        def duplicate(name):
            section = FakeClient.get_section(client, name)
            section["duplicates"] = ["NTP.Address"]
            return section

        client.get_section = duplicate
        _plans, errors = configfile.plan_writes(client, document())
        self.assertTrue(
            all("duplicate" in item["error"] for item in errors)
        )

    def test_unknown_key_in_file_is_ignored(self):
        client = FakeClient()
        sections = base_sections()
        sections["NTP"]["NTP.Nonsense"] = "x"
        doc = document()
        doc["sections"]["NTP"]["values"] = sections["NTP"]
        _plans, errors = configfile.plan_writes(client, doc)
        self.assertEqual(errors, [])


class WriteAndVerifyTests(unittest.TestCase):
    def test_successful_write_is_verified(self):
        client = FakeClient()
        result = configfile.write_and_verify(
            client, "NTP", {"NTP.Address": "time.example"}, client.sections["NTP"]
        )
        self.assertTrue(result["verified"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["mismatches"], {})
        self.assertEqual(client.writes, [("NTP", {"NTP.Address": "time.example"})])

    def test_camera_rejection_raises(self):
        client = FakeClient()
        client.reject_writes.add("NTP")
        with self.assertRaises(CameraError):
            configfile.write_and_verify(
                client, "NTP", {"NTP.Address": "x"}, client.sections["NTP"]
            )

    def test_verification_failure_reports_mismatches(self):
        client = FakeClient()
        result = configfile.write_and_verify(
            client,
            "NTP",
            {"NTP.Address": "time.example"},
            client.sections["NTP"],
        )
        client.sections["NTP"]["NTP.Address"] = "something.else"
        client.writes.clear()
        result = configfile.write_and_verify(
            client,
            "NTP",
            {"NTP.Port": "1230"},
            {"NTP.Address": "time.example", "NTP.Port": "123"},
        )
        self.assertFalse(result["verified"])
        self.assertIn("NTP.Address", result["mismatches"])
        self.assertEqual(
            result["mismatches"]["NTP.Address"]["expected"], "time.example"
        )

    def test_motion_detect_uses_the_mask_safe_writer(self):
        client = FakeClient()
        configfile.write_and_verify(
            client,
            "MotionDetect",
            {"MotionDetect[0].Level": "5"},
            client.sections["MotionDetect"],
        )
        self.assertEqual(client.writes, [])
        self.assertEqual(client.motion_writes, [{"MotionDetect[0].Level": "5"}])

    def test_dangerous_network_write_reports_disconnect(self):
        client = FakeClient()
        client.disconnect_after_network_write = True
        result = configfile.write_and_verify(
            client,
            "Network",
            {"Network.eth0.IPAddress": "192.168.2.99"},
            client.sections["Network"],
        )
        self.assertTrue(result["disconnected"])
        self.assertFalse(result["verified"])
        self.assertEqual(
            result["values"]["Network.eth0.IPAddress"], "192.168.2.99"
        )

    def test_non_dangerous_read_failure_raises(self):
        client = FakeClient()
        client.failing_reads.add("NTP")
        with self.assertRaises(CameraError):
            configfile.write_and_verify(
                client, "NTP", {"NTP.Address": "x"}, client.sections["NTP"]
            )

    def test_secret_mismatch_is_redacted(self):
        client = FakeClient()
        client.ignore_writes = True
        result = configfile.write_and_verify(
            client,
            "NAS",
            {"NAS[0].Password": "newpass"},
            dict(client.sections["NAS"]),
        )
        self.assertFalse(result["verified"])
        self.assertEqual(
            result["mismatches"]["NAS[0].Password"],
            {"expected": "<redacted>", "actual": "<redacted>"},
        )

    def test_no_mismatch_when_the_camera_accepts_a_secret(self):
        client = FakeClient()
        result = configfile.write_and_verify(
            client,
            "NAS",
            {"NAS[0].Password": "newpass"},
            dict(client.sections["NAS"]),
        )
        self.assertTrue(result["verified"])
        self.assertEqual(client.sections["NAS"]["NAS[0].Password"], "newpass")


class ApplyDocumentTests(unittest.TestCase):
    def test_matching_file_writes_nothing(self):
        client = FakeClient()
        report = configfile.apply_document(client, document())
        self.assertEqual(client.writes, [])
        self.assertEqual(client.motion_writes, [])
        self.assertFalse(report["changed"])
        self.assertEqual(report["errors"], [])

    def test_applies_only_changed_sections(self):
        client = FakeClient()
        sections = base_sections()
        sections["NTP"]["NTP.Address"] = "time.example"
        doc = document()
        doc["sections"]["NTP"]["values"] = sections["NTP"]
        report = configfile.apply_document(client, doc)
        self.assertTrue(report["changed"])
        self.assertTrue(report["verified"])
        self.assertEqual(client.writes, [("NTP", {"NTP.Address": "time.example"})])
        self.assertEqual(
            [item["name"] for item in configfile.changed_results(report["results"])],
            ["NTP"],
        )
        self.assertEqual(report["results"][1]["keys"], ["NTP.Address"])

    def test_aborts_after_the_first_camera_error(self):
        client = FakeClient()
        sections = base_sections()
        sections["NTP"]["NTP.Address"] = "time.example"
        sections["Encode"]["Encode[0].MainFormat[0].Video.FPS"] = "25"
        doc = document()
        doc["sections"]["NTP"]["values"] = sections["NTP"]
        doc["sections"]["Encode"]["values"] = sections["Encode"]
        client.reject_writes.add("NTP")
        report = configfile.apply_document(client, doc)
        self.assertTrue(report["aborted"])
        self.assertFalse(report["verified"])
        self.assertEqual(client.writes, [("NTP", {"NTP.Address": "time.example"})])
        self.assertEqual([item["section"] for item in report["errors"]], ["NTP"])


class DocumentPathTests(unittest.TestCase):
    def test_default_config_file_path(self):
        path = configfile.document_path(Path("/tmp/state"), "Cam 01!", "10.0.0.1")
        self.assertEqual(path, Path("/tmp/state/config-cam-01.json"))

    def test_falls_back_to_host(self):
        path = configfile.document_path(Path("/tmp/state"), None, "192.168.2.129")
        self.assertEqual(path.name, "config-192.168.2.129.json")


class OrderedSectionsTests(unittest.TestCase):
    def test_schema_order_then_leftovers(self):
        sections = {"Zebra": 1, "NTP": 2, "General": 3}
        self.assertEqual(
            configfile.ordered_sections(sections),
            ["General", "NTP", "Zebra"],
        )


if __name__ == "__main__":
    unittest.main()
