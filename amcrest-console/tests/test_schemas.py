import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import camera
import schemas


class SectionTests(unittest.TestCase):
    def test_sections_match_camera_allowlist(self):
        self.assertEqual(tuple(schemas.SECTIONS), tuple(camera.SECTIONS))

    def test_unknown_section_is_rejected(self):
        with self.assertRaises(schemas.SchemaError):
            schemas.section_info("FTP")

    def test_general_is_read_only(self):
        info = schemas.section_info("General")
        self.assertFalse(info["writable"])
        self.assertEqual(schemas.fields_for("General", {"General.LocalNo": "8"}), [])

    def test_dangerous_sections_need_confirmation(self):
        self.assertTrue(schemas.section_info("Network")["dangerous"])
        self.assertTrue(schemas.section_info("NAS")["dangerous"])
        self.assertEqual(
            schemas.section_info("Network")["confirm_text"], "APPLY NETWORK"
        )


class FieldMetadataTests(unittest.TestCase):
    def test_network_field_types_and_danger(self):
        ip = schemas.field_spec("Network", "Network.eth0.IPAddress")
        self.assertEqual(ip["type"], "ip")
        self.assertTrue(ip["dangerous"])
        dhcp = schemas.field_spec("Network", "Network.eth0.DhcpEnable")
        self.assertEqual(dhcp["type"], "boolean")
        mac = schemas.field_spec("Network", "Network.eth0.PhysicalAddress")
        self.assertFalse(mac["writable"])
        dns = schemas.field_spec("Network", "Network.eth0.DnsServers[1]")
        self.assertEqual(dns["label"], "DNS server 2")

    def test_nas_password_is_secret(self):
        spec = schemas.field_spec("NAS", "NAS[0].Password")
        self.assertEqual(spec["type"], "password")
        self.assertTrue(spec["secret"])
        values = {"NAS[0].Password": "secret", "NAS[0].UserName": "upload"}
        fields = {field["key"]: field for field in schemas.fields_for("NAS", values)}
        self.assertTrue(fields["NAS[0].Password"]["secret"])
        self.assertIsNone(fields["NAS[0].Password"]["value"])
        self.assertTrue(fields["NAS[0].Password"]["has_value"])
        self.assertEqual(schemas.redacted_keys("NAS", values), ["NAS[0].Password"])

    def test_auto_maintain_keys(self):
        spec = schemas.field_spec("AutoMaintain", "AutoMaintain.AutoRebootHour")
        self.assertEqual(spec["type"], "number")
        self.assertEqual(spec["group"], "Auto reboot")
        self.assertEqual(spec["max"], 23)

    def test_encode_curated_fields(self):
        fps = schemas.field_spec(
            "Encode", "Encode[0].MainFormat[0].Video.FPS"
        )
        self.assertEqual(fps["type"], "number")
        self.assertEqual(fps["group"], "Main format 0")
        width = schemas.field_spec(
            "Encode", "Encode[0].MainFormat[0].Video.Width"
        )
        self.assertFalse(width["writable"])
        resolution = schemas.field_spec(
            "Encode", "Encode[0].MainFormat[0].Video.resolution"
        )
        self.assertTrue(resolution["pattern"].match("1920x1080"))

    def test_motion_form_is_enable_and_level_only(self):
        values = {
            "MotionDetect[0].Enable": "true",
            "MotionDetect[0].Level": "3",
            "MotionDetect[0].Region[0]": "4194303",
            "MotionDetect[0].MotionDetectWindow[0].Sensitive": "60",
        }
        fields = schemas.fields_for("MotionDetect", values)
        self.assertEqual(
            [field["key"] for field in fields],
            ["MotionDetect[0].Enable", "MotionDetect[0].Level"],
        )


class NormalizeTests(unittest.TestCase):
    def spec(self, name, key):
        return schemas.field_spec(name, key)

    def test_boolean_values(self):
        spec = self.spec("NTP", "NTP.Enable")
        self.assertEqual(schemas.normalize_value(spec, True), "true")
        self.assertEqual(schemas.normalize_value(spec, "off"), "false")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(spec, "maybe")

    def test_number_bounds(self):
        spec = self.spec("MotionDetect", "MotionDetect[0].Level")
        self.assertEqual(schemas.normalize_value(spec, "6"), "6")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(spec, "7")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(spec, "3.5")

    def test_ip_and_format(self):
        spec = self.spec("Network", "Network.eth0.IPAddress")
        self.assertEqual(schemas.normalize_value(spec, "192.168.2.10"), "192.168.2.10")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(spec, "not-an-ip")
        hostname = self.spec("Network", "Network.Hostname")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(hostname, "bad host")
        resolution = self.spec("Encode", "Encode[0].MainFormat[0].Video.resolution")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(resolution, "1920-1080")

    def test_secret_blank_means_unchanged(self):
        spec = self.spec("NAS", "NAS[0].Password")
        self.assertIsNone(schemas.normalize_value(spec, ""))
        self.assertIsNone(schemas.normalize_value(spec, "<redacted>"))
        self.assertEqual(schemas.normalize_value(spec, "new secret"), "new secret")

    def test_text_rejects_line_breaks(self):
        spec = self.spec("NTP", "NTP.Address")
        with self.assertRaises(schemas.SchemaError):
            schemas.normalize_value(spec, "a\nb")


if __name__ == "__main__":
    unittest.main()
