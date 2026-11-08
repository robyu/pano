#!/usr/bin/env python3
"""Allowlisted configuration sections and field metadata.

The camera exposes flat ``key=value`` configuration with section prefixes such
as ``Network.eth0.IPAddress`` and ``NAS[0].Address``. This module decides which
sections and fields the console may edit. Unknown firmware fields stay visible
in the raw viewer but are never writable.

Everything here is stdlib only and has no camera/network side effects.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any, Dict, Iterable, List, Optional

SECTIONS = (
    "General",
    "Network",
    "NAS",
    "NTP",
    "Encode",
    "AutoMaintain",
    "MotionDetect",
)

SECTION_TITLES = {
    "General": "General",
    "Network": "Network",
    "NAS": "NAS / FTP",
    "NTP": "NTP",
    "Encode": "Encode",
    "AutoMaintain": "Auto maintain",
    "MotionDetect": "Motion detect",
}

DANGEROUS_SECTIONS = {"Network", "NAS"}
CONFIRM_PHRASES = {
    "Network": "APPLY NETWORK",
    "NAS": "APPLY NAS",
}
SECTION_WARNINGS = {
    "Network": (
        "Changing the interface, DHCP, IP address, subnet, or gateway can make "
        "the camera unreachable. A backup is written before the write. If the "
        "camera disappears, restart the console with the new --ip."
    ),
    "NAS": (
        "The camera may stop uploading clips if the NAS/FTP target is wrong. "
        "A backup is written before the write."
    ),
    "MotionDetect": (
        "The mask grid stays in the Legacy mask tab. This form changes only "
        "the camera-wide motion Enable and Level values."
    ),
}

MAX_TEXT = 255
RESOLUTION_RE = re.compile(r"^\d{2,5}x\d{2,5}$")
HOSTNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
DANGEROUS_NETWORK_FIELDS = {
    "DefaultInterface",
    "DhcpEnable",
    "Enable",
    "EnableDhcpReservedIP",
    "DnsAutoGet",
    "IPAddress",
    "SubnetMask",
    "DefaultGateway",
}
AUTO_MAINTAIN_GROUPS = {
    "Open": "Auto open",
    "Reboot": "Auto reboot",
    "Shut": "Auto shut",
    "Shutdown": "Auto shutdown",
    "StartUp": "Auto start up",
}
ENCODE_FORMATS = {
    "MainFormat": "Main format",
    "ExtraFormat": "Extra format",
    "SnapFormat": "Snapshot format",
}


class SchemaError(ValueError):
    """Raised when a section, field, or value is not allowed."""


def _spec(
    kind: str,
    label: str,
    writable: bool = True,
    secret: bool = False,
    choices: Optional[Iterable[str]] = None,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
    pattern: Optional[re.Pattern] = None,
    group: str = "",
    dangerous: bool = False,
    help_text: str = "",
    max_length: int = MAX_TEXT,
) -> Dict[str, Any]:
    return {
        "type": kind,
        "label": label,
        "writable": bool(writable),
        "secret": bool(secret),
        "choices": list(choices or []),
        "min": minimum,
        "max": maximum,
        "pattern": pattern,
        "group": group,
        "dangerous": bool(dangerous),
        "help": help_text,
        "max_length": max_length,
    }


def _readonly(label: str, group: str = "") -> Dict[str, Any]:
    return _spec("text", label, writable=False, group=group)


def _network_spec(key: str) -> Dict[str, Any]:
    if key == "Network.DefaultInterface":
        return _spec(
            "text",
            "Default interface",
            group="Network",
            dangerous=True,
            help_text="Changing this may disconnect the camera.",
        )
    if key == "Network.Domain":
        return _spec("text", "Domain", group="Network")
    if key == "Network.Hostname":
        return _spec(
            "text",
            "Hostname",
            group="Network",
            pattern=HOSTNAME_RE,
            dangerous=True,
        )

    match = re.match(r"^Network\.([A-Za-z0-9_]+)\.DnsServers\[(\d+)\]$", key)
    if match:
        interface, index = match.group(1), match.group(2)
        return _spec(
            "ip",
            "DNS server {}".format(int(index) + 1),
            group=interface,
            dangerous=True,
        )

    match = re.match(r"^Network\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)$", key)
    if not match:
        return _readonly("Unknown network field")
    interface, field = match.group(1), match.group(2)
    dangerous = field in DANGEROUS_NETWORK_FIELDS
    if field in ("DhcpEnable", "Enable", "EnableDhcpReservedIP", "DnsAutoGet", "Bonding"):
        if field == "Bonding":
            return _spec(
                "boolean", "Bonding", writable=False, group=interface
            )
        return _spec(
            "boolean",
            field.replace("Dhcp", "DHCP ").replace("Dns", "DNS "),
            group=interface,
            dangerous=dangerous,
        )
    if field in ("IPAddress", "SubnetMask", "DefaultGateway"):
        labels = {
            "IPAddress": "IP address",
            "SubnetMask": "Subnet mask",
            "DefaultGateway": "Default gateway",
        }
        return _spec("ip", labels[field], group=interface, dangerous=dangerous)
    if field == "MTU":
        return _spec(
            "number", "MTU", group=interface, minimum=576, maximum=9000
        )
    if field in ("PhysicalAddress", "Type"):
        return _spec(
            "text", field.replace("PhysicalAddress", "MAC address"),
            writable=False,
            group=interface,
        )
    if field == "NetMode":
        return _spec("text", "Network mode", group=interface)
    return _spec("text", field, group=interface)


def _nas_spec(key: str) -> Dict[str, Any]:
    match = re.match(r"^NAS\[(\d+)\]\.([A-Za-z0-9_]+)$", key)
    if not match:
        return _readonly("Unknown NAS field")
    index, field = int(match.group(1)), match.group(2)
    group = "NAS[{}]".format(index)
    if field == "Enable":
        return _spec("boolean", "Enable", group=group, dangerous=True)
    if field == "Protocol":
        return _spec(
            "select",
            "Protocol",
            choices=("FTP", "NFS", "ISCSI", "SMB"),
            group=group,
            dangerous=True,
        )
    if field == "Port":
        return _spec(
            "number", "Port", minimum=1, maximum=65535, group=group
        )
    if field == "Password":
        return _spec(
            "password",
            "Password",
            secret=True,
            group=group,
            dangerous=True,
            help_text="Leave blank to keep the current password.",
        )
    if field == "TimeOut":
        return _spec(
            "number", "Timeout", minimum=0, maximum=3600, group=group
        )
    labels = {
        "Address": "Address",
        "Directory": "Directory",
        "UserName": "Username",
        "CharacterEncoding": "Character encoding",
        "Name": "Name",
    }
    return _spec(
        "text",
        labels.get(field, field),
        group=group,
        dangerous=field in ("Address", "Directory", "UserName"),
    )


def _ntp_spec(key: str) -> Dict[str, Any]:
    if key == "NTP.Enable":
        return _spec("boolean", "Enable", group="NTP")
    if key == "NTP.Address":
        return _spec("text", "Server", group="NTP")
    if key == "NTP.Port":
        return _spec("number", "Port", minimum=1, maximum=65535, group="NTP")
    if key == "NTP.TimeZone":
        return _spec("number", "Time zone", minimum=0, maximum=32, group="NTP")
    if key == "NTP.UpdatePeriod":
        return _spec(
            "number", "Update period", minimum=0, maximum=1440, group="NTP"
        )
    return _readonly("Unknown NTP field", "NTP")


def _auto_maintain_spec(key: str) -> Dict[str, Any]:
    match = re.match(
        r"^AutoMaintain\.Auto(Open|Reboot|Shut|Shutdown|StartUp)"
        r"(Day|Hour|Minute|Enable)$",
        key,
    )
    if not match:
        return _readonly("Unknown auto-maintain field")
    action, field = match.group(1), match.group(2)
    group = AUTO_MAINTAIN_GROUPS[action]
    if field == "Enable":
        return _spec("boolean", "Enable", group=group)
    if field == "Day":
        return _spec("number", "Day", minimum=-1, maximum=7, group=group)
    if field == "Hour":
        return _spec("number", "Hour", minimum=0, maximum=23, group=group)
    return _spec("number", "Minute", minimum=0, maximum=59, group=group)


def _encode_spec(key: str) -> Dict[str, Any]:
    match = re.match(
        r"^Encode\[(\d+)\]\.(MainFormat|ExtraFormat|SnapFormat)"
        r"\[(\d+)\]\.(.+)$",
        key,
    )
    if not match:
        return _readonly("Unknown encode field")
    channel, fmt, index, field = (
        int(match.group(1)),
        match.group(2),
        int(match.group(3)),
        match.group(4),
    )
    group = "{} {}".format(ENCODE_FORMATS[fmt], index)
    if channel:
        group = "Channel {} {}".format(channel, group)
    writable = {
        "VideoEnable",
        "Video.resolution",
        "Video.FPS",
        "Video.BitRate",
        "Video.BitRateControl",
        "Video.Compression",
        "Video.Profile",
        "Video.GOP",
        "Video.Quality",
        "Video.MaxBitrate",
        "Video.Priority",
        "AudioEnable",
        "Audio.Bitrate",
        "Audio.Compression",
        "Audio.Frequency",
        "Audio.Depth",
        "Audio.Pack",
        "Audio.Mode",
    }
    if field not in writable:
        return _readonly(field, group)
    if field in ("VideoEnable", "AudioEnable"):
        return _spec("boolean", field.replace("Enable", " enable"), group=group)
    if field == "Video.resolution":
        return _spec(
            "text",
            "Resolution",
            group=group,
            pattern=RESOLUTION_RE,
            help_text="Widthxheight, for example 1920x1080.",
        )
    if field in ("Video.FPS", "Video.GOP", "Video.Quality"):
        limits = {
            "Video.FPS": (1, 60),
            "Video.GOP": (1, 600),
            "Video.Quality": (1, 6),
        }
        low, high = limits[field]
        return _spec(
            "number", field.split(".", 1)[1], minimum=low, maximum=high,
            group=group,
        )
    if field in ("Video.BitRate", "Video.MaxBitrate", "Audio.Bitrate"):
        return _spec(
            "number",
            field.split(".", 1)[1],
            minimum=8,
            maximum=65536,
            group=group,
        )
    if field == "Video.BitRateControl":
        return _spec("text", "Bit rate control", group=group)
    if field == "Video.Compression":
        return _spec("text", "Compression", group=group)
    if field == "Video.Profile":
        return _spec("text", "Profile", group=group)
    if field in ("Video.Priority", "Audio.Frequency", "Audio.Depth"):
        return _spec(
            "number", field.split(".", 1)[1], minimum=0, maximum=100000,
            group=group,
        )
    return _spec("text", field.split(".", 1)[1], group=group)


def _motion_spec(key: str) -> Dict[str, Any]:
    if key == "MotionDetect[0].Enable":
        return _spec("boolean", "Enable", group="Motion")
    if key == "MotionDetect[0].Level":
        return _spec(
            "number", "Level (1-6 sensitivity)", minimum=1, maximum=6,
            group="Motion",
        )
    return _readonly("Read-only motion field", "Motion")


def field_spec(name: str, key: str) -> Optional[Dict[str, Any]]:
    if name not in SECTIONS:
        raise SchemaError("unknown configuration section: {}".format(name))
    if name == "General":
        return _readonly("Read-only general field", "General")
    if name == "Network":
        return _network_spec(key)
    if name == "NAS":
        return _nas_spec(key)
    if name == "NTP":
        return _ntp_spec(key)
    if name == "AutoMaintain":
        return _auto_maintain_spec(key)
    if name == "Encode":
        return _encode_spec(key)
    if name == "MotionDetect":
        return _motion_spec(key)
    return None


def _natural_key(value: str) -> List[Any]:
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", value)
    ]


def fields_for(name: str, values: Dict[str, str]) -> List[Dict[str, Any]]:
    if name not in SECTIONS:
        raise SchemaError("unknown configuration section: {}".format(name))
    fields: List[Dict[str, Any]] = []
    for key in sorted(values, key=_natural_key):
        spec = field_spec(name, key)
        if not spec or not spec["writable"]:
            continue
        value = values.get(key)
        secret = bool(spec["secret"])
        item = {
            "key": key,
            "label": spec["label"],
            "type": spec["type"],
            "group": spec["group"],
            "choices": spec["choices"],
            "min": spec["min"],
            "max": spec["max"],
            "dangerous": spec["dangerous"],
            "help": spec["help"],
            "secret": secret,
            "has_value": bool(value),
            "value": None if secret else value,
        }
        fields.append(item)
    return fields


def redacted_keys(name: str, values: Dict[str, str]) -> List[str]:
    keys: List[str] = []
    for key in sorted(values, key=_natural_key):
        spec = field_spec(name, key)
        if spec and spec["secret"] and values.get(key):
            keys.append(key)
    return keys


def section_info(name: str) -> Dict[str, Any]:
    if name not in SECTIONS:
        raise SchemaError("unknown configuration section: {}".format(name))
    return {
        "name": name,
        "title": SECTION_TITLES.get(name, name),
        "writable": name != "General",
        "dangerous": name in DANGEROUS_SECTIONS,
        "confirm_text": CONFIRM_PHRASES.get(name),
        "warning": SECTION_WARNINGS.get(name),
    }


def all_sections() -> List[Dict[str, Any]]:
    return [section_info(name) for name in SECTIONS]


def _normalize_bool(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return "true"
    if text in ("0", "false", "no", "off"):
        return "false"
    raise SchemaError("expected true or false, got {!r}".format(value))


def normalize_value(spec: Dict[str, Any], value: Any) -> Optional[str]:
    kind = spec["type"]
    secret = bool(spec["secret"])
    if secret and (value is None or value == "" or value == "<redacted>"):
        return None
    if value is None:
        raise SchemaError("value is required")
    if kind == "boolean":
        return _normalize_bool(value)
    if kind == "number":
        try:
            number = int(str(value).strip(), 10)
        except (TypeError, ValueError):
            raise SchemaError("expected an integer, got {!r}".format(value))
        if spec["min"] is not None and number < spec["min"]:
            raise SchemaError(
                "value must be at least {}".format(spec["min"])
            )
        if spec["max"] is not None and number > spec["max"]:
            raise SchemaError(
                "value must be at most {}".format(spec["max"])
            )
        return str(number)
    if kind == "ip":
        try:
            return str(ipaddress.ip_address(str(value).strip()))
        except ValueError:
            raise SchemaError("expected an IP address, got {!r}".format(value))
    text = str(value)
    if not secret:
        text = text.strip()
    if "\r" in text or "\n" in text or "\x00" in text:
        raise SchemaError("value must not contain line breaks")
    if len(text) > int(spec.get("max_length") or MAX_TEXT):
        raise SchemaError("value is too long")
    if not secret and not text:
        raise SchemaError("value must not be empty")
    if kind == "select" and text not in spec["choices"]:
        raise SchemaError(
            "expected one of: {}".format(", ".join(spec["choices"]))
        )
    pattern = spec.get("pattern")
    if pattern is not None and not pattern.match(text):
        raise SchemaError("value has an invalid format")
    return text
