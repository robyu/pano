#!/usr/bin/env python3
"""Non-interactive configuration file read/write for the console (``--noui``).

``--config read`` dumps every allowlisted section to one JSON file for offline
editing; ``--config write`` pushes that file back to the camera. The file format
is the existing backup document (:func:`state.new_backup`), so it is the same
shape produced by ``GET /api/backup``.

Two rules govern the write path:

* **Network is never written non-interactively.** The camera's current
  ``Network`` section is compared against the file's and any difference aborts
  the whole run before a single write is issued. Changing an address, mask,
  gateway, or DHCP flag can make the camera unreachable, so that stays in the
  browser console.
* **MotionDetect goes through :meth:`camera.CameraClient.write_motion_settings`.**
  A bare ``setConfig`` on that section resets the 18-row legacy mask, so the
  mask rows are filtered out as non-writable and only ``Enable``/``Level`` are
  ever sent.

The section write/verify core (:func:`write_and_verify`) is shared with the
browser console's ``POST /api/config`` so both paths behave identically.

Everything here is stdlib only.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cgi_config
import schemas
import state
from camera import CameraClient, CameraError, redact_text, sanitize

LOG = logging.getLogger("amcrest.configfile")

NETWORK_SECTION = "Network"
#: Sections the write path never touches: read-only, or interactive-only.
SKIP_SECTIONS = ("General", NETWORK_SECTION)


class ConfigFileError(RuntimeError):
    """Raised when a configuration file is missing, unusable, or unsupported."""


def configuration_key(name: str) -> str:
    """Mirror key for a section (MotionDetect's flat view has its own name)."""
    if name == "MotionDetect":
        return "MotionDetectConfig"
    return name


def section_payload(
    name: str,
    values: Dict[str, str],
    duplicates: Optional[List[str]] = None,
    stale: bool = False,
    include_secrets: bool = False,
) -> Dict[str, Any]:
    """Build one section entry for a mirror, backup, or config file."""
    payload: Dict[str, Any] = {
        "name": name,
        "title": schemas.SECTION_TITLES.get(name, name),
        "writable": name != "General",
        "dangerous": name in schemas.DANGEROUS_SECTIONS,
        "confirm_text": schemas.CONFIRM_PHRASES.get(name),
        "values": dict(values) if include_secrets else sanitize(values),
        "fields": schemas.fields_for(name, values),
        "redacted": []
        if include_secrets
        else schemas.redacted_keys(name, values),
        "revision": cgi_config.revision(values),
        "duplicates": list(duplicates or []),
        "warning": schemas.SECTION_WARNINGS.get(name),
    }
    if stale:
        payload["stale"] = True
    return payload


def read_sections(
    client: CameraClient, include_secrets: bool = False
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Read every allowlisted section; return ``(sections, errors)``."""
    sections: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = []
    for name in schemas.SECTIONS:
        try:
            section = client.get_section(name)
        except CameraError as error:
            LOG.warning("configuration read failed name=%s: %s", name, error)
            errors.append({"section": name, "error": str(error)})
            continue
        sections[name] = section_payload(
            name,
            section["values"],
            duplicates=section["duplicates"],
            include_secrets=include_secrets,
        )
    return sections, errors


def read_document(
    client: CameraClient,
    camera_meta: Dict[str, Any],
    mirror: Optional[Dict[str, Any]] = None,
    include_secrets: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Read the camera and return a backup document plus per-section errors.

    When ``mirror`` is supplied, a section that failed to read is filled in from
    the mirror so the document stays complete; the error is still reported.
    """
    sections, errors = read_sections(client, include_secrets=include_secrets)
    if mirror:
        configuration = mirror.get("configuration") or {}
        for item in errors:
            stored = configuration.get(configuration_key(item["section"]))
            if stored:
                sections[item["section"]] = stored
    doc = state.new_backup(
        camera_meta, sections, complete=not errors, stale=bool(errors)
    )
    if errors:
        doc["errors"] = errors
    return doc, errors


def write_backup(
    client: CameraClient,
    camera_meta: Dict[str, Any],
    backup_dir: Path,
    name: str,
    host: str,
) -> Tuple[Path, Dict[str, Any]]:
    """Write a complete pre-write backup; fail if any section cannot be read."""
    doc, errors = read_document(client, camera_meta, mirror=None)
    if errors:
        detail = "; ".join(
            "{}: {}".format(item["section"], item["error"]) for item in errors
        )
        raise CameraError(
            "cannot create a complete pre-write backup: {}".format(detail)
        )
    path = state.backup_path(backup_dir, name, host)
    try:
        state.save(path, doc)
    except OSError as error:
        raise CameraError(
            "cannot write pre-write backup {}: {}".format(path, error)
        )
    LOG.info("pre-write backup written path=%s", path)
    return path, doc


def document_path(state_dir: Path, name: Optional[str], host: str) -> Path:
    """Default ``--config-file`` path, ``<state-dir>/config-<slug>.json``."""
    return Path(state_dir) / "config-{}.json".format(state.slugify(name or host))


def load_document(path: Path) -> Dict[str, Any]:
    """Load and validate a configuration file written by ``--config read``."""
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigFileError("configuration file not found: {}".format(path))
    except OSError as error:
        raise ConfigFileError(
            "cannot read configuration file {}: {}".format(path, error)
        )
    try:
        doc = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise ConfigFileError(
            "configuration file is not valid JSON: {}".format(path)
        )
    if not isinstance(doc, dict):
        raise ConfigFileError(
            "configuration file is not a JSON object: {}".format(path)
        )
    if doc.get("kind") != state.BACKUP_KIND:
        raise ConfigFileError(
            "not an amcrest console configuration file (kind={!r}): {}".format(
                doc.get("kind"), path
            )
        )
    if doc.get("schema_version") != state.SCHEMA_VERSION:
        raise ConfigFileError(
            "configuration file schema_version {} is not supported "
            "({} expected): {}".format(
                doc.get("schema_version"), state.SCHEMA_VERSION, path
            )
        )
    sections = doc.get("sections")
    if not isinstance(sections, dict):
        raise ConfigFileError(
            "configuration file has no sections object: {}".format(path)
        )
    return doc


def ordered_sections(sections: Dict[str, Any]) -> List[str]:
    """Section names in schema order, then any unknown leftovers sorted."""
    known = [name for name in schemas.SECTIONS if name in sections]
    extra = sorted(name for name in sections if name not in schemas.SECTIONS)
    return known + extra


def network_mismatches(
    live: Dict[str, str], target: Dict[str, str]
) -> Dict[str, Dict[str, Optional[str]]]:
    """Compare the camera's Network section against the file's.

    Compares the union of keys so a key present on only one side counts as a
    difference. Secret-typed values are reported as ``<redacted>``.
    """
    mismatches: Dict[str, Dict[str, Optional[str]]] = {}
    for key in sorted(set(live) | set(target)):
        current = live.get(key)
        wanted = target.get(key)
        if current == wanted:
            continue
        spec = schemas.field_spec(NETWORK_SECTION, key)
        if spec and spec.get("secret"):
            current = "<redacted>"
            wanted = "<redacted>"
        mismatches[key] = {"camera": current, "file": wanted}
    return mismatches


def writable_values(name: str, values: Dict[str, str]) -> Dict[str, str]:
    """Keep only the keys the schema marks writable for ``name``."""
    allowed: Dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            continue
        spec = schemas.field_spec(name, key)
        if spec and spec["writable"]:
            allowed[key] = value
    return allowed


def _dangerous_field(name: str, key: str) -> bool:
    spec = schemas.field_spec(name, key)
    return bool(spec and spec.get("dangerous"))


def write_and_verify(
    client: CameraClient,
    name: str,
    changes: Dict[str, str],
    live_values: Dict[str, str],
    backup_path: Optional[Path] = None,
    log: logging.Logger = LOG,
) -> Dict[str, Any]:
    """Apply ``changes`` to one section, re-read, and verify every key.

    Returns a result dict with ``changed``/``verified``/``values`` and, on
    failure, ``mismatches`` or ``disconnected`` plus ``error``. Raises
    :class:`camera.CameraError` when the camera rejects the write outright or
    when a re-read fails for a non-network reason.
    """
    result: Dict[str, Any] = {
        "name": name,
        "changed": True,
        "verified": False,
        "disconnected": False,
        "error": None,
        "mismatches": {},
        "backup": str(backup_path) if backup_path else None,
    }
    network_danger = name == NETWORK_SECTION and any(
        _dangerous_field(name, key) for key in changes
    )
    log.info(
        "config apply requested name=%s keys=%d changed=%s backup=%s",
        name,
        len(changes),
        sorted(changes),
        backup_path,
    )
    if name == "MotionDetect":
        response = client.write_motion_settings(changes)
    else:
        response = client.set_section_changes(name, changes)
    log.info(
        "config write response name=%s response=%r",
        name,
        redact_text(response)[:200],
    )
    if "ErrorID" in response or "error" in response.lower():
        raise CameraError(
            "camera rejected config write: {}".format(
                redact_text(response)[:300]
            )
        )

    expected = cgi_config.apply_changes(name, live_values, changes)
    try:
        after = client.get_section(name)
    except CameraError as error:
        if network_danger:
            log.warning(
                "network write may have disconnected the camera name=%s: %s",
                name,
                error,
            )
            result["disconnected"] = True
            result["error"] = str(error)
            result["values"] = expected
            return result
        raise

    actual = after["values"]
    mismatches: Dict[str, Dict[str, Optional[str]]] = {}
    for key in sorted(set(expected) | set(actual)):
        if expected.get(key) != actual.get(key):
            spec = schemas.field_spec(name, key)
            if spec and spec.get("secret"):
                mismatches[key] = {
                    "expected": "<redacted>",
                    "actual": "<redacted>",
                }
            else:
                mismatches[key] = {
                    "expected": expected.get(key),
                    "actual": actual.get(key),
                }
    if mismatches:
        log.error(
            "config write verification failed name=%s fields=%s",
            name,
            sorted(mismatches),
        )
        result["mismatches"] = mismatches
        result["values"] = actual
        return result

    result["verified"] = True
    result["values"] = actual
    result["duplicates"] = list(after["duplicates"])
    return result


def plan_writes(
    client: CameraClient, doc: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Read each writable section and compute the changes the file implies.

    Returns ``(plans, errors)``. A plan holds the live section and the
    normalized changes (empty when the file already matches the camera).
    """
    plans: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    sections = doc.get("sections") or {}
    for name in ordered_sections(sections):
        if name in SKIP_SECTIONS:
            continue
        try:
            live = client.get_section(name)
            if live["duplicates"]:
                errors.append(
                    {
                        "section": name,
                        "error": "camera returned duplicate config keys; "
                        "refusing write",
                        "duplicates": list(live["duplicates"]),
                    }
                )
                continue
            target = writable_values(name, sections[name].get("values") or {})
            changes = cgi_config.diff_changes(name, live["values"], target)
        except (
            cgi_config.ConfigError,
            schemas.SchemaError,
            CameraError,
        ) as error:
            errors.append({"section": name, "error": str(error)})
            continue
        plans.append({"name": name, "live": live, "changes": changes})
    return plans, errors


def apply_document(
    client: CameraClient,
    doc: Dict[str, Any],
    backup_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Apply a configuration document to the camera, section by section.

    Returns a report with ``results`` (one entry per writable section),
    ``errors``, ``changed``, ``verified``, and ``aborted``. The first camera
    error stops the run so a half-applied batch cannot cascade.
    """
    plans, errors = plan_writes(client, doc)
    results: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {
        "results": results,
        "errors": errors,
        "changed": False,
        "verified": True,
        "aborted": False,
    }
    for plan in plans:
        name = plan["name"]
        live = plan["live"]
        if not plan["changes"]:
            LOG.info("config apply no-op name=%s", name)
            results.append(
                {
                    "name": name,
                    "changed": False,
                    "verified": True,
                    "disconnected": False,
                    "error": None,
                    "keys": [],
                    "mismatches": {},
                    "backup": str(backup_path) if backup_path else None,
                    "values": live["values"],
                    "duplicates": list(live["duplicates"]),
                }
            )
            continue
        try:
            result = write_and_verify(
                client,
                name,
                plan["changes"],
                live["values"],
                backup_path=backup_path,
            )
        except CameraError as error:
            LOG.error("config apply failed name=%s: %s", name, error)
            errors.append({"section": name, "error": str(error)})
            results.append(
                {
                    "name": name,
                    "changed": False,
                    "verified": False,
                    "disconnected": False,
                    "error": str(error),
                    "keys": sorted(plan["changes"]),
                    "mismatches": {},
                    "backup": str(backup_path) if backup_path else None,
                    "values": live["values"],
                    "duplicates": list(live["duplicates"]),
                }
            )
            report["aborted"] = True
            report["verified"] = False
            break
        result["keys"] = sorted(plan["changes"])
        results.append(result)
        if result["changed"]:
            report["changed"] = True
        if not result["verified"]:
            report["verified"] = False
    return report


def changed_results(results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in results if item.get("changed")]


def format_mismatches(mismatches: Dict[str, Dict[str, Optional[str]]]) -> str:
    """Render a mismatch table for the network guard and verification errors."""
    lines = []
    width = max((len(key) for key in mismatches), default=0)
    for key in sorted(mismatches):
        entry = mismatches[key]
        lines.append(
            "  {:<{w}}  camera={!r}  file={!r}".format(
                key,
                entry.get("camera", entry.get("expected")),
                entry.get("file", entry.get("actual")),
                w=width,
            )
        )
    return "\n".join(lines)
