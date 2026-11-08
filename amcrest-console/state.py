#!/usr/bin/env python3
"""Per-camera JSON configuration mirror.

The camera is always the source of truth. This module maintains one local JSON
file per camera that reflects the last configuration read from (or verified on)
the camera. Phase 2 stores ``MotionDetect``; later phases can add other sections
under ``configuration`` without changing the file layout.

Writes are atomic (temp file + ``os.replace``), mode 0600, and serialized with
an advisory lock. Secret-looking keys are redacted by ``camera.sanitize`` before
anything reaches disk.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from camera import sanitize

try:  # POSIX only; macOS and Linux both have it.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore

SCHEMA_VERSION = 1
DEFAULT_STATE_DIR = Path(__file__).resolve().parent / "cameras"
DEFAULT_BACKUP_DIR = Path(__file__).resolve().parent / "backups"
SLUG_RE = re.compile(r"[^a-z0-9._-]+")
MAX_SLUG = 80
BACKUP_KIND = "amcrest-console-backup"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-._")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        slug = "camera"
    return slug[:MAX_SLUG]


def mirror_path(state_dir: Path, name: Optional[str], host: str) -> Path:
    """Return the per-camera mirror path (one file per camera)."""
    label = name or host
    return Path(state_dir) / "{}.json".format(slugify(label))


def backup_path(
    backup_dir: Path,
    name: Optional[str],
    host: str,
    stamp: Optional[str] = None,
) -> Path:
    label = name or host
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(backup_dir) / "{}-{}.json".format(slugify(label), stamp)


def new_backup(
    camera: Dict[str, Any],
    sections: Dict[str, Any],
    complete: bool = True,
    stale: bool = False,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": BACKUP_KIND,
        "created": now_iso(),
        "camera": {
            "name": camera.get("name"),
            "host": camera.get("host"),
            "port": camera.get("port", 80),
            "model": camera.get("model"),
            "firmware": camera.get("firmware"),
        },
        "complete": bool(complete),
        "stale": bool(stale),
        "sections": sections,
    }


def _quarantine(path: Path) -> Optional[Path]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name("{}.bad-{}".format(path.name, stamp))
    try:
        os.replace(str(path), str(target))
    except OSError:
        return None
    return target


def load(path: Path, quarantine: bool = True) -> Optional[Dict[str, Any]]:
    """Load a mirror; return None when missing, corrupt, or unsupported."""
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        if quarantine:
            _quarantine(path)
        return None
    if not isinstance(data, dict):
        if quarantine:
            _quarantine(path)
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        if quarantine:
            _quarantine(path)
        return None
    return data


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Serialize writers for one mirror file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    handle = open(str(lock_path), "a+")
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def save(path: Path, data: Dict[str, Any]) -> None:
    """Atomically write a sanitized mirror file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = sanitize(data)
    with locked(path):
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        )
        tmp_name = handle.name
        try:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        try:
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, str(path))
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def new_mirror(
    camera: Dict[str, Any],
    configuration: Dict[str, Any],
    stale: bool = False,
    verified: bool = True,
    last_apply: Optional[str] = None,
    updated: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "camera": {
            "name": camera.get("name"),
            "host": camera.get("host"),
            "port": camera.get("port", 80),
            "model": camera.get("model"),
            "firmware": camera.get("firmware"),
        },
        "configuration": configuration,
        "mirror": {
            "updated": updated or now_iso(),
            "last_apply": last_apply,
            "verified": bool(verified),
            "stale": bool(stale),
        },
    }
